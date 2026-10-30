"""Relatório de validação da importação (RF12; docs/importacao.md, seção 5).

Compara o que a planilha publica com o que o sistema calcula: taxas pela população do IBGE,
variação da taxa, participação (proporções da T09 e da T21) e as tabelas de conferência (T01,
T09). Também registra informações (regiões calculadas, somas parciais, contagem por situação) e
avisos (células vazias, registros órfãos). O resultado vai para dados/relatorios/ em CSV (uma
linha por apontamento) e em Markdown (resumo).

Todas as comparações são feitas em precisão total, sem arredondar nenhum lado, com tolerância
absoluta de 1e-6 (ADR 0004). As taxas do FBSP batem com o cálculo pela população do IBGE até
~1e-14, e o arredondamento de taxa_publicada a 12 casas acrescenta no máximo 5e-13.
"""

import csv
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from apps.importacao.leitores.fbsp import TabelaLida, ValorPublicado
from apps.importacao.leitores.ibge import PopulacaoLida
from apps.importacao.linhas import Chave, Linha, Localidade, Metodo, Nivel
from apps.registros.escolhas import Situacao
from apps.registros.queries import variacao_percentual

TOLERANCIA = Decimal("1e-6")
BASE_HABITANTES = "100 mil habitantes"
CEM_MIL = Decimal(100_000)

COLUNAS = (
    "tabela",
    "origem",
    "indicador",
    "localidade",
    "recorte",
    "unidade",
    "ano",
    "verificacao",
    "esperado",
    "obtido",
    "diferenca",
    "severidade",
)


class Severidade(StrEnum):
    DIVERGENCIA = "divergencia"
    AVISO = "aviso"
    INFORMACAO = "informacao"


def taxa_por_100_mil(valor: Decimal, populacao: int | Decimal) -> Decimal:
    """Taxa por 100 mil habitantes, em precisão total (sem arredondar)."""
    return valor / Decimal(populacao) * CEM_MIL


def diverge(calculada: Decimal, publicada: Decimal, tolerancia: Decimal = TOLERANCIA) -> bool:
    """Indica se a diferença entre os dois valores passa da tolerância."""
    return abs(calculada - publicada) > tolerancia


@dataclass(frozen=True)
class Apontamento:
    verificacao: str
    severidade: Severidade
    tabela: str = ""
    origem: str = ""
    chave: Chave | None = None
    esperado: Decimal | str | None = None
    obtido: Decimal | str | None = None

    @property
    def diferenca(self) -> Decimal | None:
        if isinstance(self.esperado, Decimal) and isinstance(self.obtido, Decimal):
            return self.obtido - self.esperado
        return None

    def como_linha(self) -> dict[str, str]:
        chave = self.chave
        recorte = ";".join(f"{d}={v}" for d, v in chave.recorte) if chave else ""
        return {
            "tabela": self.tabela,
            "origem": self.origem,
            "indicador": chave.indicador if chave else "",
            "localidade": chave.localidade.sigla if chave else "",
            "recorte": recorte,
            "unidade": chave.unidade if chave else "",
            "ano": str(chave.ano) if chave else "",
            "verificacao": self.verificacao,
            "esperado": "" if self.esperado is None else str(self.esperado),
            "obtido": "" if self.obtido is None else str(self.obtido),
            "diferenca": "" if self.diferenca is None else str(self.diferenca),
            "severidade": self.severidade,
        }


@dataclass
class Relatorio:
    apontamentos: list[Apontamento] = field(default_factory=list)
    conferidos: Counter = field(default_factory=Counter)  # comparações feitas por verificação

    def adicionar(self, apontamento: Apontamento) -> None:
        self.apontamentos.append(apontamento)

    def incorporar(self, outro: Relatorio, rotulo: str) -> None:
        """Junta o relatório de uma edição anterior, com o arquivo na verificação e na tabela."""
        for item in outro.apontamentos:
            if item.verificacao == "ibge_marca_de_nota":  # já está no relatório da edição atual
                continue
            self.adicionar(
                replace(
                    item,
                    verificacao=f"{rotulo}:{item.verificacao}",
                    tabela=f"{rotulo}:{item.tabela}",
                )
            )
        for verificacao, total in outro.conferidos.items():
            self.conferidos[f"{rotulo}:{verificacao}"] += total

    def de(self, severidade: Severidade) -> list[Apontamento]:
        return [a for a in self.apontamentos if a.severidade is severidade]

    @property
    def tem_divergencias(self) -> bool:
        return bool(self.de(Severidade.DIVERGENCIA))

    def salvar(self, diretorio: Path, versao: str) -> tuple[Path, Path]:
        diretorio.mkdir(parents=True, exist_ok=True)
        caminho_csv = diretorio / f"validacao-{versao}.csv"
        with caminho_csv.open("w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS, lineterminator="\r\n")
            escritor.writeheader()
            escritor.writerows(a.como_linha() for a in self.apontamentos)
        caminho_md = diretorio / f"validacao-{versao}.md"
        caminho_md.write_text(self.resumo(versao), encoding="utf-8")
        return caminho_csv, caminho_md

    def resumo(self, versao: str) -> str:
        linhas = [
            f"# Relatório de validação — carga {versao}",
            "",
            f"Tolerância: {TOLERANCIA} (precisão total, sem arredondar).",
            "",
            "## Comparações feitas",
            "",
            "| Verificação | Comparações | Divergências |",
            "| :--- | ---: | ---: |",
        ]
        divergencias = Counter(a.verificacao for a in self.de(Severidade.DIVERGENCIA))
        for verificacao, total in sorted(self.conferidos.items()):
            linhas.append(f"| {verificacao} | {total} | {divergencias[verificacao]} |")
        linhas += ["", "## Apontamentos por severidade", ""]
        for severidade in Severidade:
            linhas.append(f"- {severidade}: {len(self.de(severidade))}")
        for severidade in (Severidade.DIVERGENCIA, Severidade.AVISO, Severidade.INFORMACAO):
            itens = self.de(severidade)
            if not itens:
                continue
            linhas += ["", f"## {severidade.capitalize()}", ""]
            for item in itens:
                dados = item.como_linha()
                descricao = " ".join(
                    dados[c]
                    for c in ("tabela", "origem", "indicador", "localidade", "recorte")
                    if dados[c]
                )
                ano = f" {dados['unidade']} {dados['ano']}" if dados["ano"] else ""
                detalhe = f": esperado {dados['esperado']}" if dados["esperado"] else ""
                detalhe += f", obtido {dados['obtido']}" if dados["obtido"] else ""
                linhas.append(f"- {item.verificacao} — {descricao}{ano}{detalhe}")
        return "\n".join(linhas) + "\n"


def _tabela(origem: str) -> str:
    return origem.split("!", 1)[0]


class Calculos:
    """Taxa, variação e participação calculadas como a API calcula (contrato, seção 3)."""

    def __init__(
        self,
        linhas: Iterable[Linha],
        populacao: Mapping[tuple[Localidade, int], Decimal],
        base_taxa: Mapping[str, str | None],
    ):
        self.linhas = {linha.chave: linha for linha in linhas}
        self.populacao = populacao
        self.base_taxa = base_taxa

    def taxa(self, chave: Chave) -> Decimal | None:
        linha = self.linhas.get(chave)
        if linha is None or linha.valor is None:
            return None
        populacao = self.populacao.get((chave.localidade, chave.ano))
        if self.base_taxa.get(chave.indicador) == BASE_HABITANTES and populacao:
            return taxa_por_100_mil(linha.valor, populacao)
        return linha.taxa_publicada

    def variacao_da_taxa(self, chave: Chave) -> Decimal | None:
        anterior = Chave(
            chave.localidade, chave.indicador, chave.recorte, chave.unidade, chave.ano - 1
        )
        return variacao_percentual(self.taxa(chave), self.taxa(anterior))

    def participacao(self, chave: Chave, pai: str) -> Decimal | None:
        filho = self.linhas.get(chave)
        referencia = self.linhas.get(Chave(chave.localidade, pai, (), chave.unidade, chave.ano))
        if filho is None or referencia is None or filho.valor is None or not referencia.valor:
            return None
        return filho.valor / referencia.valor * 100


def gerar(
    linhas: list[Linha],
    tabelas: Iterable[TabelaLida],
    populacoes: Iterable[PopulacaoLida],
    base_taxa: Mapping[str, str | None],
    indicador_pai: Mapping[str, str | None],
    *,
    denominador_proprio: bool = False,
) -> Relatorio:
    """Monta o relatório; não grava nada. Os órfãos entram depois, com `adicionar_orfaos`.

    `denominador_proprio`: as taxas da edição usam outra população (edição de 2024: Censo 2022). A
    diferença para POPULACAO vira informação, e a variação publicada é conferida com as próprias
    taxas publicadas.
    """
    tabelas = list(tabelas)
    populacoes = list(populacoes)
    populacao = {
        (loc, lida.ano): valor for lida in populacoes for loc, valor in lida.valores.items()
    }
    calculos = Calculos(linhas, populacao, base_taxa)
    relatorio = Relatorio()

    if denominador_proprio:
        _taxas(relatorio, linhas, calculos, Severidade.INFORMACAO)
        calculos = Calculos(linhas, {}, base_taxa)
    else:
        _taxas(relatorio, linhas, calculos)
    for tabela in tabelas:
        for publicado in tabela.publicados:
            _conferir_publicado(relatorio, publicado, tabela, calculos, indicador_pai)
        for origem in tabela.vazias:
            relatorio.adicionar(
                Apontamento("celula_vazia", Severidade.AVISO, _tabela(origem), origem)
            )
    _recortes_t08(relatorio, linhas)
    _informacoes(relatorio, linhas, populacoes)
    return relatorio


def _taxas(
    relatorio: Relatorio,
    linhas: list[Linha],
    calculos: Calculos,
    severidade: Severidade | None = None,
) -> None:
    """Taxa calculada pela população do IBGE × taxa publicada (vítimas e ocorrências)."""
    for linha in linhas:
        chave = linha.chave
        populacao = calculos.populacao.get((chave.localidade, chave.ano))
        if (
            calculos.base_taxa.get(chave.indicador) != BASE_HABITANTES
            or not populacao
            or linha.valor is None
            or linha.taxa_publicada is None
        ):
            continue
        calculada = taxa_por_100_mil(linha.valor, populacao)
        relatorio.conferidos["taxa_calculada_x_publicada"] += 1
        if diverge(calculada, linha.taxa_publicada):
            relatorio.adicionar(
                Apontamento(
                    "taxa_calculada_x_publicada",
                    severidade or Severidade.DIVERGENCIA,
                    _tabela(linha.origem),
                    linha.origem_taxa or linha.origem,
                    chave,
                    linha.taxa_publicada,
                    calculada,
                )
            )


def _conferir_publicado(
    relatorio: Relatorio,
    publicado: ValorPublicado,
    tabela: TabelaLida,
    calculos: Calculos,
    indicador_pai: Mapping[str, str | None],
) -> None:
    chave = publicado.chave
    if publicado.grupo == "variacao":
        verificacao, calculado = "variacao_da_taxa", calculos.variacao_da_taxa(chave)
    elif publicado.grupo == "proporcao":
        pai = indicador_pai[chave.indicador]
        verificacao, calculado = "participacao_x_proporcao", calculos.participacao(chave, pai)
    else:  # tabela de conferência: o mesmo valor publicado pela tabela dona
        dona = calculos.linhas.get(chave)
        verificacao = f"conferencia_{publicado.tabela.lower()}_{publicado.grupo}"
        if dona is None:
            calculado = None
        else:
            calculado = dona.valor if publicado.grupo == "valor" else dona.taxa_publicada

    relatorio.conferidos[verificacao] += 1
    marcador = publicado.situacao is not Situacao.INFORMADO
    if publicado.grupo in ("variacao", "proporcao") and marcador:
        # "-" ou "..." no lugar de um percentual: não há número a comparar. Só é apontado (como
        # informação) quando o sistema calcula um número onde a planilha não publicou nenhum.
        if calculado is not None:
            relatorio.adicionar(
                Apontamento(
                    f"{verificacao}_sem_numero_publicado",
                    Severidade.INFORMACAO,
                    tabela.tabela.aba,
                    publicado.origem,
                    chave,
                    publicado.situacao.value,
                    calculado,
                )
            )
        return
    if calculado is None and publicado.valor is None:
        return
    if calculado is None or publicado.valor is None or diverge(calculado, publicado.valor):
        relatorio.adicionar(
            Apontamento(
                verificacao,
                Severidade.DIVERGENCIA,
                tabela.tabela.aba,
                publicado.origem,
                chave,
                publicado.valor,
                calculado,
            )
        )


def _recortes_t08(relatorio: Relatorio, linhas: list[Linha]) -> None:
    """Soma dos recortes de corporação e situação × total de MDIP (informativo)."""
    totais: dict[tuple, Linha] = {}
    soma: dict[tuple, Decimal] = defaultdict(Decimal)
    for linha in linhas:
        chave = linha.chave
        if chave.indicador != "morte-intervencao-policial" or linha.metodo is not Metodo.PUBLICADO:
            continue
        grupo = (chave.localidade, chave.unidade, chave.ano)
        if chave.recorte:
            soma[grupo] += linha.valor or 0
        else:
            totais[grupo] = linha
    for grupo, total in sorted(totais.items()):
        if total.valor is not None and soma[grupo] != total.valor:
            relatorio.adicionar(
                Apontamento(
                    "soma_dos_recortes_x_total",
                    Severidade.INFORMACAO,
                    _tabela(total.origem),
                    total.origem,
                    total.chave,
                    total.valor,
                    soma[grupo],
                )
            )


def _informacoes(
    relatorio: Relatorio, linhas: list[Linha], populacoes: list[PopulacaoLida]
) -> None:
    for linha in linhas:
        if linha.chave.localidade.nivel is Nivel.PAIS and "soma apenas" in linha.observacao:
            relatorio.adicionar(
                Apontamento(
                    "brasil_soma_parcial",
                    Severidade.INFORMACAO,
                    _tabela(linha.origem),
                    linha.origem,
                    linha.chave,
                    obtido=linha.observacao,
                )
            )

    regionais: Counter = Counter()
    regionais_nulas: Counter = Counter()
    situacoes: Counter = Counter()
    for linha in linhas:
        tabela = _tabela(linha.origem)
        situacoes[(tabela, linha.situacao)] += 1
        if linha.metodo is Metodo.SOMA_UFS:
            regionais[(tabela, linha.chave.unidade)] += 1
            if linha.situacao is Situacao.NAO_DISPONIVEL:
                regionais_nulas[(tabela, linha.chave.unidade)] += 1
    for (tabela, unidade), total in sorted(regionais.items()):
        relatorio.adicionar(
            Apontamento(
                f"regioes_calculadas_{unidade}",
                Severidade.INFORMACAO,
                tabela,
                esperado=f"{total} calculadas",
                obtido=f"{regionais_nulas[(tabela, unidade)]} nao_disponivel",
            )
        )
    for (tabela, situacao), total in sorted(situacoes.items()):
        relatorio.adicionar(
            Apontamento(f"contagem_{situacao}", Severidade.INFORMACAO, tabela, obtido=str(total))
        )

    for lida in populacoes:
        for localidade, marca in lida.marcas.items():
            relatorio.adicionar(
                Apontamento(
                    "ibge_marca_de_nota",
                    Severidade.INFORMACAO,
                    lida.arquivo,
                    obtido=f"{localidade.sigla} {lida.ano}: {marca} {' '.join(lida.notas)}",
                )
            )


def adicionar_orfaos(relatorio: Relatorio, orfaos: Iterable[str]) -> None:
    """Registros da carga anterior ausentes na atual: não são apagados, só apontados."""
    for orfao in orfaos:
        relatorio.adicionar(Apontamento("registro_orfao", Severidade.AVISO, obtido=orfao))

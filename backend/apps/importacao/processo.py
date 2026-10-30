"""Fluxo completo da importação (docs/importacao.md, seção 4.1).

O comando importar_anuario só trata as opções e as mensagens; o fluxo fica aqui para ser testado
com planilhas reduzidas (`tabelas` com só parte do mapeamento). Qualquer erro desfaz a transação
inteira, e a carga anterior continua valendo; a carga que falhou fica com status "falhou".
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.catalogo import referencia as ref_catalogo
from apps.importacao import edicoes, gravacao, validacao
from apps.importacao.agregacao import ErroAgregacao, agregar
from apps.importacao.erros import ErroImportacao
from apps.importacao.leitores import fbsp, ibge
from apps.importacao.linhas import Linha, Metodo
from apps.importacao.mapeamento import EDICOES_ANTERIORES, TABELAS, Tabela, contagem_esperada
from apps.importacao.models import Carga
from apps.localidades.referencia import REGIAO_DA_UF

PREFIXO_DAS_PROJECOES = "projecoes"
LINHA_DO_MANIFESTO = re.compile(r"^\|\s*`([^`]+)`\s*\|.*\|\s*`([0-9a-f]{64})`\s*\|\s*$")


@dataclass(frozen=True)
class Arquivo:
    nome: str
    caminho: Path
    sha256: str


@dataclass
class Resultado:
    versao: str
    carga: Carga | None
    registros: int
    calculados: int
    populacao: int
    relatorio: validacao.Relatorio
    arquivos_relatorio: tuple[Path, Path]


def ler_manifesto(caminho: Path) -> dict[str, str]:
    """{arquivo: sha256} da tabela de dados/README.md."""
    if not caminho.is_file():
        raise ErroImportacao(f"Manifesto com os hashes não encontrado: {caminho}")
    hashes = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        casou = LINHA_DO_MANIFESTO.match(linha.strip())
        if casou:
            hashes[casou.group(1)] = casou.group(2)
    if not hashes:
        raise ErroImportacao(f"Nenhum hash de arquivo encontrado em {caminho}")
    return hashes


def sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def _e_projecao(arquivo: Arquivo) -> bool:
    return arquivo.nome.startswith(PREFIXO_DAS_PROJECOES)


def _planilhas_do_anuario(arquivos: list[Arquivo]) -> list[Arquivo]:
    return [a for a in arquivos if a.nome.endswith(".xlsx") and not _e_projecao(a)]


def _edicao_atual(arquivos: list[Arquivo]) -> list[Arquivo]:
    anteriores = {edicao.arquivo for edicao in EDICOES_ANTERIORES}
    return [a for a in _planilhas_do_anuario(arquivos) if a.nome not in anteriores]


def _ler_edicao(
    caminho: Path,
    tabelas: tuple[Tabela, ...],
    unidade_padrao,
    base_taxa,
) -> tuple[list, list[Linha], list[Linha]]:
    """Lê as tabelas de uma planilha e agrega as regiões; confere chaves e contagem da edição."""
    wb = fbsp.abrir(caminho)
    lidas = [fbsp.ler_tabela(wb, t, unidade_padrao, base_taxa) for t in tabelas]
    linhas = [linha for lida in lidas for linha in lida.linhas]
    calculadas = agregar(linhas, REGIAO_DA_UF)
    verificar_chaves_unicas(linhas + calculadas)
    esperados = contagem_esperada(tabelas)
    if (len(linhas), len(calculadas)) != esperados:
        raise ErroImportacao(
            f"{caminho.name}: {len(linhas)} registros lidos e {len(calculadas)} calculados; "
            f"esperados {esperados[0]} e {esperados[1]}."
        )
    return lidas, linhas + calculadas, calculadas


def verificar_arquivos(dados: Path, manifesto: Path) -> list[Arquivo]:
    """Todo arquivo do manifesto precisa existir em `dados` com o mesmo SHA-256 (regra 1)."""
    arquivos = []
    for nome, esperado in sorted(ler_manifesto(manifesto).items()):
        caminho = dados / nome
        if not caminho.is_file():
            raise ErroImportacao(f"Arquivo do manifesto não encontrado: {caminho}")
        obtido = sha256(caminho)
        if obtido != esperado:
            raise ErroImportacao(
                f"SHA-256 de {nome} diverge do manifesto ({obtido} ≠ {esperado}). Nova versão de "
                "planilha exige novo arquivo e novo hash em dados/README.md."
            )
        arquivos.append(Arquivo(nome, caminho, obtido))
    if len(_edicao_atual(arquivos)) != 1 or not any(a.nome.endswith(".ods") for a in arquivos):
        raise ErroImportacao("O manifesto precisa listar uma planilha .xlsx e as .ods do IBGE.")
    return arquivos


def versao_da_carga(arquivos: list[Arquivo]) -> str:
    """sha256 dos hashes concatenados, em ordem de nome; 12 primeiros caracteres."""
    return hashlib.sha256("".join(a.sha256 for a in arquivos).encode()).hexdigest()[:12]


def verificar_chaves_unicas(linhas: list[Linha]) -> None:
    """Mesma chave vinda de duas tabelas donas é erro do mapeamento (regra 8)."""
    vistas: dict = {}
    for linha in linhas:
        if linha.chave in vistas:
            raise ErroImportacao(
                f"Chave repetida em {vistas[linha.chave]} e {linha.origem}: {linha.chave}"
            )
        vistas[linha.chave] = linha.origem


def importar(
    dados: Path,
    relatorio: Path,
    manifesto: Path,
    *,
    tabelas: tuple[Tabela, ...] = TABELAS,
    somente_validar: bool = False,
) -> Resultado:
    """Importa as planilhas e gera o relatório; erro → ErroImportacao, nada gravado."""
    arquivos = verificar_arquivos(dados, manifesto)
    versao = versao_da_carga(arquivos)
    carga = None
    if not somente_validar:
        carga = Carga.objects.create(
            versao=versao, arquivos=[{"nome": a.nome, "sha256": a.sha256} for a in arquivos]
        )

    unidade_padrao = {i.slug: i.unidade_padrao for i in ref_catalogo.INDICADORES}
    base_taxa = {
        i.slug: i.base_taxa.value if i.base_taxa else None for i in ref_catalogo.INDICADORES
    }
    indicador_pai = {i.slug: i.pai for i in ref_catalogo.INDICADORES}

    try:
        with transaction.atomic():
            refs = gravacao.carregar_referencias()

            populacoes = [ibge.ler(a.caminho) for a in arquivos if a.nome.endswith(".ods")]
            for arquivo in filter(_e_projecao, arquivos):
                populacoes += ibge.ler_projecoes(arquivo.caminho)
            anos = [lida.ano for lida in populacoes]
            if len(set(anos)) != len(anos):
                raise ErroImportacao(f"População do IBGE repetida para o mesmo ano: {anos}")
            total_populacao = gravacao.gravar_populacao(populacoes, refs)

            planilha = _edicao_atual(arquivos)[0]
            lidas, linhas, calculadas = _ler_edicao(
                planilha.caminho, tabelas, unidade_padrao, base_taxa
            )
            relatorio_gerado = validacao.gerar(linhas, lidas, populacoes, base_taxa, indicador_pai)

            caminhos = {a.nome: a.caminho for a in arquivos}
            for edicao in EDICOES_ANTERIORES:
                if edicao.arquivo not in caminhos:
                    continue
                lidas_edicao, linhas_edicao, _ = _ler_edicao(
                    caminhos[edicao.arquivo], edicao.tabelas, unidade_padrao, base_taxa
                )
                relatorio_gerado.incorporar(
                    validacao.gerar(
                        linhas_edicao + edicoes.mvi_da_conferencia(lidas_edicao),
                        lidas_edicao,
                        populacoes,
                        base_taxa,
                        indicador_pai,
                        denominador_proprio=edicao.denominador_proprio,
                    ),
                    edicao.arquivo,
                )
                linhas, revisoes = edicoes.incorporar(
                    linhas, linhas_edicao, edicao.ano, edicao.arquivo
                )
                for revisao in revisoes:
                    relatorio_gerado.adicionar(revisao)
            verificar_chaves_unicas(linhas)
            calculadas = [linha for linha in linhas if linha.metodo is Metodo.SOMA_UFS]

            if somente_validar:
                transaction.set_rollback(True)
            else:
                ordem_recortes = [b.recorte for t in tabelas for b in t.blocos if b.recorte]
                orfaos = gravacao.upsert(linhas, refs, ordem_recortes)
                validacao.adicionar_orfaos(relatorio_gerado, orfaos)
                carga.status = Carga.Status.CONCLUIDA
                carga.concluida_em = timezone.now()
                carga.total_registros = len(linhas)
                carga.save(update_fields=["status", "concluida_em", "total_registros"])
    except ErroAgregacao as erro:
        _falhou(carga)
        raise ErroImportacao(str(erro)) from erro
    except Exception:
        _falhou(carga)
        raise

    arquivos_relatorio = relatorio_gerado.salvar(relatorio, versao)
    return Resultado(
        versao,
        carga,
        len(linhas),
        len(calculadas),
        total_populacao,
        relatorio_gerado,
        arquivos_relatorio,
    )


def _falhou(carga: Carga | None) -> None:
    if carga is not None:
        carga.status = Carga.Status.FALHOU
        carga.save(update_fields=["status"])

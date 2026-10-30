"""Gravação idempotente no banco (docs/importacao.md, seções 4.1, 4.6 e 4.9).

Só o comando importar_anuario chama estas funções (RNF06), dentro da transação da carga. Rodar a
importação duas vezes não muda contagem nem id de nenhum registro (regra 3): referências usam
update_or_create pela chave natural, e população e registros usam upsert (bulk_create com
update_conflicts) sobre as constraints NULLS NOT DISTINCT. Nada é apagado: registros da carga
anterior ausentes na atual são devolvidos como órfãos para o relatório.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from apps.catalogo import referencia as ref_catalogo
from apps.catalogo.models import Fonte, Indicador, Recorte, RecorteItem
from apps.importacao.leitores.ibge import PopulacaoLida
from apps.importacao.linhas import Linha, Localidade, Nivel
from apps.importacao.linhas import Recorte as ItensRecorte
from apps.localidades import referencia as ref_localidades
from apps.localidades.models import Estado, Populacao, Regiao
from apps.registros.models import RegistroAnual

LOTE = 2000


@dataclass
class Referencias:
    """Objetos gravados, por chave natural, para montar populações e registros."""

    fontes: dict[str, Fonte]
    regioes: dict[str, Regiao]
    estados: dict[str, Estado]
    indicadores: dict[str, Indicador]

    def localidade(self, localidade: Localidade) -> dict:
        """Campos estado/regiao de uma localidade (exatamente um preenchido)."""
        if localidade.nivel is Nivel.UF:
            return {"estado": self.estados[localidade.sigla], "regiao": None}
        return {"estado": None, "regiao": self.regioes[localidade.sigla]}


def carregar_referencias() -> Referencias:
    """Fontes primeiro e na ordem fixa (ids estáveis), depois localidades e indicadores."""
    fontes = {}
    for fonte in ref_catalogo.FONTES:
        fontes[fonte.slug], _ = Fonte.objects.update_or_create(
            slug=fonte.slug,
            defaults={"nome": fonte.nome, "descricao": fonte.descricao, "url": fonte.url},
        )

    regioes = {}
    for regiao in ref_localidades.REGIOES:
        regioes[regiao.sigla], _ = Regiao.objects.update_or_create(
            sigla=regiao.sigla,
            defaults={"nome": regiao.nome, "tipo": regiao.tipo, "codigo_ibge": regiao.codigo_ibge},
        )
    estados = {}
    for estado in ref_localidades.ESTADOS:
        estados[estado.sigla], _ = Estado.objects.update_or_create(
            sigla=estado.sigla,
            defaults={
                "nome": estado.nome,
                "codigo_ibge": estado.codigo_ibge,
                "regiao": regioes[estado.regiao],
            },
        )

    indicadores = {}
    for ordem, indicador in enumerate(ref_catalogo.INDICADORES, start=1):
        base = indicador.base_taxa
        indicadores[indicador.slug], _ = Indicador.objects.update_or_create(
            slug=indicador.slug,
            defaults={
                "nome": indicador.nome,
                "descricao": indicador.descricao,
                "unidade_padrao": indicador.unidade_padrao,
                "base_taxa": base,
                "fonte_taxa": fontes[ref_catalogo.FONTE_DA_BASE[base]] if base else None,
                "indicador_pai": indicadores[indicador.pai] if indicador.pai else None,
                "ordem": ordem,
            },
        )
    return Referencias(fontes, regioes, estados, indicadores)


def chave_do_recorte(itens: ItensRecorte) -> str:
    """ "corporacao=Polícia Civil;situacao_policial=Em serviço" (pares em ordem)."""
    return ";".join(f"{dimensao}={valor}" for dimensao, valor in sorted(itens))


def rotulo_do_recorte(itens: ItensRecorte) -> str:
    """Valores na ordem da chave, só o primeiro com maiúscula: "Polícia Civil, em serviço"."""
    valores = [valor for _, valor in sorted(itens)]
    return ", ".join([valores[0], *(valor[0].lower() + valor[1:] for valor in valores[1:])])


def obter_recortes(em_ordem: Iterable[ItensRecorte]) -> dict[ItensRecorte, Recorte]:
    """Recortes criados na ordem recebida (a dos blocos de mapeamento.py): banco limpo, mesmos ids.

    Contrato, seção 4.4; docs/importacao.md, seção 4.6.
    """
    recortes: dict[ItensRecorte, Recorte] = {}
    for itens in em_ordem:
        if not itens or itens in recortes:
            continue
        recorte, criado = Recorte.objects.get_or_create(
            chave=chave_do_recorte(itens), defaults={"rotulo": rotulo_do_recorte(itens)}
        )
        if criado:
            RecorteItem.objects.bulk_create(
                RecorteItem(recorte=recorte, dimensao=dimensao, valor=valor)
                for dimensao, valor in sorted(itens)
            )
        recortes[itens] = recorte
    return recortes


def gravar_populacao(populacoes: Iterable[PopulacaoLida], refs: Referencias) -> int:
    objetos = [
        Populacao(
            fonte=refs.fontes[lida.fonte],
            ano=lida.ano,
            valor=valor,
            **refs.localidade(localidade),
        )
        for lida in populacoes
        for localidade, valor in lida.valores.items()
    ]
    Populacao.objects.bulk_create(
        objetos,
        batch_size=LOTE,
        update_conflicts=True,
        unique_fields=["estado", "regiao", "ano"],
        update_fields=["valor", "fonte"],
    )
    return len(objetos)


CAMPOS_DA_CHAVE = ("estado_id", "regiao_id", "indicador_id", "recorte_id", "unidade", "ano")


def _orfaos(objetos: list[RegistroAnual]) -> list[str]:
    """Registros já gravados cuja chave não está na carga atual, descritos para o relatório."""
    atuais = {tuple(getattr(objeto, campo) for campo in CAMPOS_DA_CHAVE) for objeto in objetos}
    gravados = RegistroAnual.objects.values_list(
        *CAMPOS_DA_CHAVE, "estado__sigla", "regiao__sigla", "indicador__slug", "recorte__chave"
    )
    return [
        f"{uf or regiao} {indicador} [{recorte or 'total'}] {unidade} {ano}"
        for *chave, uf, regiao, indicador, recorte in gravados.iterator()
        if tuple(chave) not in atuais
        for unidade, ano in [chave[4:6]]
    ]


def upsert(
    linhas: list[Linha], refs: Referencias, ordem_recortes: Iterable[ItensRecorte] = ()
) -> list[str]:
    """Grava as linhas sem apagar nem duplicar. Devolve os registros órfãos da carga anterior.

    `ordem_recortes` dá a ordem de criação dos recortes; os que faltarem nela vêm depois, na
    ordem das linhas.
    """
    recortes = obter_recortes([*ordem_recortes, *(linha.chave.recorte for linha in linhas)])
    fonte = refs.fontes[ref_catalogo.FONTE_DOS_REGISTROS]
    objetos = [
        RegistroAnual(
            **refs.localidade(linha.chave.localidade),
            indicador=refs.indicadores[linha.chave.indicador],
            recorte=recortes.get(linha.chave.recorte),
            fonte=fonte,
            ano=linha.chave.ano,
            unidade=linha.chave.unidade,
            valor=linha.valor,
            taxa_publicada=linha.taxa_publicada,
            situacao=linha.situacao,
            metodo=linha.metodo,
            origem=linha.origem,
            observacao=linha.observacao or None,
        )
        for linha in linhas
    ]
    orfaos = _orfaos(objetos)
    RegistroAnual.objects.bulk_create(
        objetos,
        batch_size=LOTE,
        update_conflicts=True,
        unique_fields=["estado", "regiao", "indicador", "recorte", "unidade", "ano"],
        update_fields=[
            "valor",
            "taxa_publicada",
            "situacao",
            "observacao",
            "fonte",
            "origem",
            "metodo",
        ],
    )
    return orfaos

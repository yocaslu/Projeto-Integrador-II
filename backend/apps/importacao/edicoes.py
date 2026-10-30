"""Junção das edições do Anuário: qual edição é a dona de cada ano (ADR 0012).

A dona de um (indicador, recorte, unidade, ano) é a edição mais recente cuja tabela traz esse ano,
em todas as localidades: "..." e "-" contam como publicados, e o Brasil e as UFs saem sempre da
mesma edição, para o Brasil continuar igual à soma das UFs que informaram (regra 4). O mesmo dado em
edição anterior nunca substitui o da dona: se difere, vira nota na observação e informação no
relatório.
"""

from collections.abc import Iterable
from dataclasses import replace

from apps.importacao.agregacao import _juntar, _sem_localidade
from apps.importacao.leitores.fbsp import TabelaLida
from apps.importacao.linhas import Linha, Metodo
from apps.importacao.validacao import Apontamento, Severidade
from apps.registros.escolhas import Situacao


def _publicado(linha: Linha) -> str:
    if linha.valor is None:
        return "o dado como não disponível"
    return f"{linha.valor:f}"


def incorporar(
    donas: list[Linha], anteriores: Iterable[Linha], ano_da_edicao: int, arquivo: str
) -> tuple[list[Linha], list[Apontamento]]:
    """As linhas `donas` mais os anos que só a edição anterior traz, e as revisões encontradas.

    As linhas novas levam o nome do arquivo na `origem`; as `donas` ganham a nota da revisão.
    """
    por_chave = {linha.chave: linha for linha in donas}
    grupos_com_dona = {_sem_localidade(chave) for chave in por_chave}
    novas: list[Linha] = []
    revisoes: list[Apontamento] = []
    for linha in anteriores:
        if _sem_localidade(linha.chave) not in grupos_com_dona:
            linha.origem = f"{arquivo}:{linha.origem}"
            novas.append(linha)
            continue
        dona = por_chave.get(linha.chave)
        if (
            dona is None
            or dona.metodo is not Metodo.PUBLICADO
            or linha.metodo is not Metodo.PUBLICADO
            or dona.valor == linha.valor
        ):
            continue
        dona.observacao = _juntar(
            dona.observacao,
            f"Revisão do FBSP: a edição de {ano_da_edicao} do Anuário publicou "
            f"{_publicado(linha)}.",
        )
        revisoes.append(
            Apontamento(
                "revisao_entre_edicoes",
                Severidade.INFORMACAO,
                arquivo,
                linha.origem,
                linha.chave,
                linha.valor,
                dona.valor,
            )
        )
    return donas + novas, revisoes


def mvi_da_conferencia(lidas: Iterable[TabelaLida]) -> list[Linha]:
    """A MVI das tabelas de conferência da edição: base das proporções de MDIP publicadas nela.

    As séries de MVI das edições anteriores não são lidas; estas linhas só entram na validação.
    """
    return [
        replace(
            Linha(chave=publicado.chave),
            valor=publicado.valor,
            situacao=publicado.situacao or Situacao.INFORMADO,
            origem=publicado.origem,
        )
        for tabela in lidas
        for publicado in tabela.publicados
        if publicado.chave.indicador == "mvi" and publicado.grupo == "valor"
    ]

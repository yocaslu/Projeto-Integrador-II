"""Agregados regionais calculados como soma das UFs (docs/importacao.md, seção 4.8).

O Anuário publica o total do Brasil em todas as tabelas, mas os totais das regiões só na série
histórica de MVI (T02). Para os demais indicadores, a região é calculada aqui somando as UFs, que é
o mesmo método do FBSP: em todas as colunas absolutas da planilha, o total do Brasil é exatamente a
soma das UFs, e os totais regionais da T02 são exatamente a soma das UFs de cada região.

Regras (CLAUDE.md, regra invariável 4):

- só a soma geográfica (UF → região) é feita; um indicador-pai nunca é a soma dos subtipos;
- dentro do mesmo indicador, recorte, unidade e ano: vítimas e ocorrências nunca se misturam, e
  o que é somável decide-se pela unidade da chave (ADR 0004);
- se alguma UF da região está como "..." (não disponível), a região fica nula e não disponível,
  em vez de virar uma soma parcial;
- a taxa da região não é somada: fica nula aqui e é calculada na consulta a partir da população
  da região, quando a base é 100 mil habitantes (regra 11);
- agregados publicados (Brasil e regiões da T02) continuam sendo importados e servem de
  conferência: se a soma das UFs que informaram divergir do valor publicado, a importação aborta.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from decimal import Decimal

from apps.importacao.linhas import Chave, Linha, Localidade, Metodo, Nivel, Unidade
from apps.importacao.normalizacao import Situacao

UNIDADES_SOMAVEIS = frozenset(Unidade)

NOTA_SOMA = "Valor calculado pelo projeto como soma das UFs da região."


class ErroAgregacao(Exception):
    """Dado incompatível com a agregação; a importação inteira deve ser desfeita."""


@dataclass(frozen=True)
class Divergencia:
    chave: Chave
    publicado: Decimal
    soma_das_ufs: Decimal

    def __str__(self) -> str:
        loc = self.chave.localidade
        recorte = ";".join(f"{d}={v}" for d, v in self.chave.recorte) or "total"
        return (
            f"{loc.nivel}={loc.sigla} {self.chave.indicador} [{recorte}] {self.chave.unidade} "
            f"{self.chave.ano}: "
            f"publicado {self.publicado}, soma das UFs {self.soma_das_ufs}"
        )


def agregar(linhas: Iterable[Linha], regiao_da_uf: Mapping[str, str]) -> list[Linha]:
    """Confere os agregados publicados e devolve as linhas regionais que faltam.

    `regiao_da_uf` mapeia a sigla de cada uma das 27 UFs para a sigla da sua região (vem das
    referências de localidades). A unidade de cada linha está na própria chave.

    Anota, nas linhas do Brasil, quando o total publicado soma só as UFs que informaram.
    Levanta `ErroAgregacao` se algum agregado publicado divergir da soma das UFs, se faltar UF em
    algum grupo, se aparecer UF fora das referências ou unidade que não seja somável.
    """
    linhas = list(linhas)
    ufs_da_regiao: dict[str, set[str]] = defaultdict(set)
    for uf, regiao in regiao_da_uf.items():
        ufs_da_regiao[regiao].add(uf)
    todas_as_ufs = set(regiao_da_uf)

    publicadas = {linha.chave: linha for linha in linhas}
    brasil = {
        _sem_localidade(linha.chave): linha
        for linha in linhas
        if linha.chave.localidade.nivel is Nivel.PAIS
    }

    por_regiao: dict[Chave, list[Linha]] = defaultdict(list)
    por_pais: dict[tuple, list[Linha]] = defaultdict(list)
    for linha in linhas:
        localidade = linha.chave.localidade
        if localidade.nivel is not Nivel.UF:
            continue
        _exigir_somavel(linha.chave)
        if localidade.sigla not in regiao_da_uf:
            raise ErroAgregacao(f"UF sem região nas referências: {localidade.sigla}")
        regiao = Localidade(Nivel.REGIAO, regiao_da_uf[localidade.sigla])
        por_regiao[replace(linha.chave, localidade=regiao)].append(linha)
        por_pais[_sem_localidade(linha.chave)].append(linha)

    divergencias: list[Divergencia] = []

    for chave_sem_local, ufs in sorted(por_pais.items()):
        _exigir_ufs(ufs, todas_as_ufs, chave_sem_local)
        linha_brasil = brasil.get(chave_sem_local)
        if linha_brasil is None or linha_brasil.valor is None:
            continue
        divergencia = _conferir(linha_brasil, ufs)
        if divergencia:
            divergencias.append(divergencia)
        sem_dado = _ufs_sem_dado(ufs)
        if sem_dado:
            linha_brasil.observacao = _juntar(
                linha_brasil.observacao,
                f"O total publicado pelo FBSP soma apenas as UFs que informaram o dado "
                f"({len(ufs) - len(sem_dado)} de {len(ufs)}; sem informação: "
                f"{', '.join(sem_dado)}).",
            )

    novas: list[Linha] = []
    for chave, ufs in sorted(por_regiao.items()):
        _exigir_ufs(ufs, ufs_da_regiao[chave.localidade.sigla], chave)
        publicada = publicadas.get(chave)
        if publicada is None:
            novas.append(_somar(chave, ufs))
        elif publicada.valor is not None:
            divergencia = _conferir(publicada, ufs)
            if divergencia:
                divergencias.append(divergencia)

    if divergencias:
        detalhes = "\n".join(f"- {d}" for d in divergencias)
        raise ErroAgregacao(
            f"{len(divergencias)} agregado(s) publicado(s) divergem da soma das UFs:\n{detalhes}"
        )
    return novas


def _sem_localidade(chave: Chave) -> tuple:
    return (chave.indicador, chave.recorte, chave.unidade, chave.ano)


def _exigir_somavel(chave: Chave) -> None:
    """Toda linha de UF tem unidade absoluta; outra unidade é erro do leitor, não dado a pular."""
    if chave.unidade not in UNIDADES_SOMAVEIS:
        raise ErroAgregacao(f"Unidade não somável em {chave}: {chave.unidade!r}")


def _exigir_ufs(ufs: list[Linha], esperadas: set[str], grupo) -> None:
    presentes = {linha.chave.localidade.sigla for linha in ufs}
    faltam = esperadas - presentes
    if faltam:
        raise ErroAgregacao(f"Faltam UFs para agregar {grupo}: {', '.join(sorted(faltam))}")


def _ufs_sem_dado(ufs: list[Linha]) -> list[str]:
    return sorted(linha.chave.localidade.sigla for linha in ufs if linha.valor is None)


def _conferir(publicada: Linha, ufs: list[Linha]) -> Divergencia | None:
    """Compara com a soma das UFs que informaram, que é como o FBSP monta os totais."""
    soma = sum((linha.valor for linha in ufs if linha.valor is not None), Decimal(0))
    if soma != publicada.valor:
        return Divergencia(publicada.chave, publicada.valor, soma)
    return None


def _somar(chave: Chave, ufs: list[Linha]) -> Linha:
    ufs = sorted(ufs, key=lambda linha: linha.chave.localidade.sigla)
    sem_dado = _ufs_sem_dado(ufs)

    if sem_dado:
        valor, situacao = None, Situacao.NAO_DISPONIVEL
    elif all(linha.situacao is Situacao.INEXISTENTE for linha in ufs):
        valor, situacao = Decimal(0), Situacao.INEXISTENTE
    else:
        valor, situacao = sum((linha.valor for linha in ufs), Decimal(0)), Situacao.INFORMADO

    observacao = NOTA_SOMA
    if sem_dado:
        observacao = _juntar(observacao, f"UFs sem informação: {', '.join(sem_dado)}.")
    observacao = _juntar(observacao, _notas_das_ufs(ufs))

    return Linha(
        chave=chave,
        valor=valor,
        situacao=situacao,
        taxa_publicada=None,
        origem=_origem(ufs),
        observacao=observacao,
        marcas=set().union(*(linha.marcas for linha in ufs)),
        metodo=Metodo.SOMA_UFS,
    )


def _notas_das_ufs(ufs: list[Linha]) -> str:
    """Repete uma vez a nota comum a todas as UFs e identifica a UF das demais.

    Ex.: o homicídio doloso de MG inclui as mortes por intervenção policial; a nota precisa
    acompanhar o total do Sudeste.
    """
    textos: dict[str, list[str]] = defaultdict(list)
    for linha in ufs:
        if linha.observacao:
            textos[linha.observacao].append(linha.chave.localidade.sigla)
    partes = []
    for texto, siglas in textos.items():
        if len(siglas) == len(ufs):
            partes.append(texto)
        else:
            partes.append(f"{', '.join(siglas)}: {texto}")
    return " ".join(partes)


def _origem(ufs: list[Linha]) -> str:
    """Células somadas, ex.: "T03!C10+C13+C21"; a aba aparece uma vez quando é a mesma."""
    origens = [linha.origem for linha in ufs if linha.origem]
    abas = {origem.split("!", 1)[0] for origem in origens if "!" in origem}
    if len(abas) == 1 and all("!" in origem for origem in origens):
        aba = abas.pop()
        return f"{aba}!" + "+".join(origem.split("!", 1)[1] for origem in origens)
    return "+".join(origens)


def _juntar(*partes: str) -> str:
    return " ".join(parte for parte in partes if parte)

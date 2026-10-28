"""Especificação declarativa das tabelas lidas da planilha do FBSP (docs/importacao.md, 4.2).

Nenhuma posição fixa de linha ou coluna: cada tabela é localizada pela âncora (rótulo da coluna A
que abre o cabeçalho) e cada coluna pelo seu caminho de cabeçalho, a lista de textos das linhas
de cabeçalho acima dela, com as células mescladas expandidas. Ex.: coluna D da T03:

    ("Homicídios dolosos", "Nº de Vítimas", "Taxas (2)", "2024 (3)")

Toda coluna com cabeçalho precisa casar com exatamente um bloco ou com um padrão de `ignorar`;
uma coluna órfã aborta a importação. Cada (indicador, localidade, recorte, unidade, ano) tem uma
única tabela dona; T01 e T09 só alimentam o relatório (conferencia=True).
"""

from dataclasses import dataclass

from apps.registros.escolhas import Unidade

ANCORA_UFS = r"^\s*Brasil e Unidades da Federa[çc][ãa]o\s*$"
ANCORA_REGIOES = r"^\s*Brasil, Regi[õo]es e Unidades da Federa[çc][ãa]o\s*$"
# Fechadas com \s*$: a linha 3 (abrangência) começa com o mesmo texto e vem antes da âncora.

GRUPOS = {
    r"^ns\.? absolutos|^n[úu]mero absoluto": "valor",
    r"^taxas?\b": "taxa",
    r"^varia[çc][ãa]o": "variacao",
    r"^em percentual|^propor[çc][ãa]o": "proporcao",  # só conferência (T09, T21)
}
"""Grupo de cada coluna, pelo penúltimo nível do caminho (sem diferença de caixa)."""

GRUPOS_GRAVADOS = frozenset({"valor", "taxa"})
"""Os demais grupos (variação, proporção) vão só para o relatório de validação."""

PADRAO = frozenset({"valor", "taxa", "variacao"})
SO_VALOR = frozenset({"valor"})

Recorte = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Bloco:
    indicador: str  # slug
    caminho: tuple[str, ...]  # regexes que precisam casar, em ordem, com níveis do caminho
    recorte: Recorte = ()  # pares (dimensao, valor) em ordem; vazio = total do indicador
    unidade: Unidade | None = None  # None = unidade_padrao do indicador
    grupos: frozenset[str] = PADRAO


@dataclass(frozen=True)
class Tabela:
    aba: str
    ancora: str  # regex do rótulo da coluna A que abre o cabeçalho
    linhas_cabecalho: int  # níveis a partir da âncora, inclusive
    blocos: tuple[Bloco, ...]
    anos: tuple[int, ...]
    localidades_esperadas: int  # 28 (Brasil e UFs) ou 33 (com as regiões)
    ignorar: tuple[str, ...] = ()  # colunas com cabeçalho que não são lidas
    conferencia: bool = False  # True = só alimenta o relatório

    def blocos_gravados(self) -> tuple[Bloco, ...]:
        """Blocos que geram registros: os que têm coluna de valor."""
        return tuple(bloco for bloco in self.blocos if "valor" in bloco.grupos)


ANOS_2024_2025 = (2024, 2025)
VITIMAS, OCORRENCIAS = Unidade.VITIMAS, Unidade.OCORRENCIAS


def _vitimas_e_ocorrencias(indicador: str, rotulo: str) -> tuple[Bloco, ...]:
    """T03, T04 e T05: o mesmo crime em vítimas e em ocorrências (ADR 0004)."""
    return (
        Bloco(indicador, (rotulo, r"V[íi]timas$"), unidade=VITIMAS),
        Bloco(indicador, (rotulo, r"Ocorr[êe]ncias$"), unidade=OCORRENCIAS),
    )


def _mdip(corporacao: str, situacao: str, regex: str) -> Bloco:
    return Bloco(
        "morte-intervencao-policial",
        (regex,),
        recorte=(("corporacao", corporacao), ("situacao_policial", situacao)),
        grupos=SO_VALOR,
    )


TABELAS: tuple[Tabela, ...] = (
    Tabela(
        aba="T02",
        ancora=ANCORA_REGIOES,
        linhas_cabecalho=3,
        blocos=(Bloco("mvi", (r"^Mortes Violentas Intencionais",)),),
        anos=tuple(range(2012, 2026)),
        localidades_esperadas=33,
    ),
    Tabela(
        aba="T03",
        ancora=ANCORA_UFS,
        linhas_cabecalho=4,
        blocos=_vitimas_e_ocorrencias("homicidio-doloso", r"^Homic[íi]dios dolosos$"),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
    ),
    Tabela(
        aba="T04",
        ancora=ANCORA_UFS,
        linhas_cabecalho=4,
        blocos=_vitimas_e_ocorrencias("latrocinio", r"^Latroc[íi]nio$"),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
    ),
    Tabela(
        aba="T05",
        ancora=ANCORA_UFS,
        linhas_cabecalho=4,
        blocos=_vitimas_e_ocorrencias(
            "lesao-corporal-seguida-de-morte", r"^Les[ãa]o corporal seguida de morte$"
        ),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
    ),
    Tabela(
        aba="T08",
        ancora=ANCORA_UFS,
        linhas_cabecalho=3,
        blocos=(
            _mdip("Polícia Civil", "Em serviço", r"Policiais Civis em servi[çc]o$"),
            _mdip("Polícia Militar", "Em serviço", r"Policiais Militares em servi[çc]o$"),
            _mdip("Polícia Civil", "Fora de serviço", r"Policiais Civis fora de servi[çc]o$"),
            _mdip("Polícia Militar", "Fora de serviço", r"Policiais Militares fora de servi[çc]o$"),
            Bloco("morte-intervencao-policial", (r"^Total$",)),
        ),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
    ),
    Tabela(
        aba="T11",
        ancora=ANCORA_UFS,
        linhas_cabecalho=3,
        blocos=(
            Bloco("roubo-veiculo", (r"^Roubo de ve[íi]culo$",)),
            Bloco("furto-veiculo", (r"^Furto de ve[íi]culo$",)),
        ),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
        ignorar=(r"^Roubo e Furto",),  # regra 5: não existe total de furtos
    ),
    Tabela(
        aba="T12",
        ancora=ANCORA_UFS,
        linhas_cabecalho=3,
        blocos=(
            Bloco("roubo-celular", (r"^Roubo de celulares$",)),
            Bloco("furto-celular", (r"^Furto de celulares$",)),
        ),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
        ignorar=(r"^Roubo e Furto",),
    ),
    Tabela(
        aba="T14",
        ancora=ANCORA_UFS,
        linhas_cabecalho=3,
        blocos=(
            Bloco("roubo-estabelecimento-comercial", (r"^Roubo a estabelecimento comercial$",)),
            Bloco("roubo-residencia", (r"^Roubo a resid[êe]ncia$",)),
            Bloco("roubo-transeunte", (r"^Roubo a transeunte$",)),
        ),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
    ),
    Tabela(
        aba="T15",
        ancora=ANCORA_UFS,
        linhas_cabecalho=3,
        blocos=(
            Bloco("roubo-instituicao-financeira", (r"^Roubo a institui[çc][ãa]o financeira",)),
            Bloco("roubo-carga", (r"^Roubo de carga$",)),
            Bloco("roubo", (r"^Roubo \(total\)$",)),
        ),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
    ),
    Tabela(
        aba="T21",
        ancora=ANCORA_UFS,
        linhas_cabecalho=4,
        blocos=(
            Bloco("homicidio-mulheres", (r"^Homic[íi]dios \(incluindo feminic[íi]dios\)$",)),
            Bloco("feminicidio", (r"^Feminic[íi]dios$",)),
            # Proporção feminicídio ÷ homicídio de mulheres: conferida contra a participação.
            Bloco(
                "feminicidio",
                (r"^Propor[çc][ãa]o de feminic[íi]dios",),
                grupos=frozenset({"proporcao"}),
            ),
        ),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
    ),
    # Só conferência
    Tabela(
        aba="T01",
        ancora=ANCORA_UFS,
        linhas_cabecalho=5,
        blocos=(Bloco("mvi", (r"^Mortes Violentas Intencionais",)),),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
        ignorar=(
            r"^Crimes Violentos Letais Intencionais",
            r"^Policiais Civis e Militares V[íi]timas",
            r"^Morte Decorrente de Interven[çc][ãa]o Policial",
        ),
        conferencia=True,
    ),
    Tabela(
        aba="T09",
        ancora=ANCORA_UFS,
        linhas_cabecalho=5,
        blocos=(
            Bloco("mvi", (r"^Mortes Violentas Intencionais",), grupos=SO_VALOR),
            Bloco(
                "morte-intervencao-policial",
                (r"^Mortes Decorrentes de Interven[çc][õo]es Policiais",),
                grupos=SO_VALOR,
            ),
            # Proporção MDIP ÷ MVI: conferida contra a participação.
            Bloco(
                "morte-intervencao-policial",
                (r"^Propor[çc][ãa]o de MDIP",),
                grupos=frozenset({"proporcao"}),
            ),
        ),
        anos=ANOS_2024_2025,
        localidades_esperadas=28,
        conferencia=True,
    ),
)

REGIOES_CALCULADAS = 5
"""Regiões somadas por (indicador, recorte, unidade, ano) nas tabelas sem totais regionais."""


def contagem_esperada(tabelas: tuple[Tabela, ...] = TABELAS) -> tuple[int, int]:
    """(registros lidos, registros regionais calculados) que a importação precisa produzir.

    Com as tabelas completas: 1.750 lidos + 230 calculados = 1.980 (docs/importacao.md, 3).
    """
    lidos = calculados = 0
    for tabela in tabelas:
        if tabela.conferencia:
            continue
        combinacoes = len(tabela.anos) * len(tabela.blocos_gravados())
        lidos += tabela.localidades_esperadas * combinacoes
        if tabela.localidades_esperadas == 28:  # sem regiões publicadas
            calculados += REGIOES_CALCULADAS * combinacoes
    return lidos, calculados

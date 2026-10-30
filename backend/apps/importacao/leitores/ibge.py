"""Leitura da população do IBGE: estimativas de 2024 e 2025 e projeções de 2012 a 2023.

Estimativas (dados/brutos/POP2024_*.ods e POP2025_*.ods):

Segue docs/importacao.md, seção 4.7: aba BRASIL_E_UFs, âncora "BRASIL E UNIDADES DA FEDERAÇÃO",
leitura até "Fonte:". O ano vem do título e é conferido com o nome do arquivo. Cada arquivo traz
as 33 localidades (Brasil, 5 regiões e 27 UFs) com os totais regionais já publicados; não há soma.
A coluna de marcas (ex.: "(1)" em PR e SC em 2025) não entra no valor: vai para o relatório.

Projeções (dados/brutos/projecoes_2024_*.xlsx, CLAUDE.md, pendência 12): uma aba, com os anos de
2000 a 2070 nas colunas. Não há linha de total: a população é a soma dos 19 grupos etários com sexo
"Ambos". As regiões têm siglas próprias do IBGE.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import openpyxl
import pandas as pd

from apps.catalogo import referencia as ref_catalogo
from apps.importacao.erros import ErroImportacao
from apps.importacao.linhas import Localidade, Nivel
from apps.importacao.normalizacao import chave_de_nome, resolver_localidade
from apps.localidades.referencia import REGIAO_DA_UF

ABA = "BRASIL_E_UFs"
ANCORA = "brasil e unidades da federacao"
LOCALIDADES_ESPERADAS = 33
ANO_DO_TITULO = re.compile(r"DE (\d{4})\s*$")
ANO_DO_ARQUIVO = re.compile(r"^POP(\d{4})_")

ANOS_DAS_PROJECOES = tuple(range(2012, 2024))
"""Anos lidos das projeções; 2024 e 2025 ficam com as estimativas, usadas pelo FBSP nesses anos."""
ROTULO_DO_CABECALHO = "grupo etario"
SEXO_TOTAL = "Ambos"
GRUPOS_ETARIOS = 19
COLUNA_DO_GRUPO, COLUNA_DO_SEXO, COLUNA_DA_SIGLA, PRIMEIRA_COLUNA_DE_ANO = 0, 1, 3, 5
PRIMEIRO_ANO, ULTIMO_ANO = 2000, 2070
REGIOES_NAS_PROJECOES = {"NO": "N", "ND": "NE", "SD": "SE", "SU": "S", "CO": "CO"}


@dataclass
class PopulacaoLida:
    arquivo: str
    ano: int
    valores: dict[Localidade, Decimal] = field(default_factory=dict)
    marcas: dict[Localidade, str] = field(default_factory=dict)  # marca de nota por localidade
    notas: list[str] = field(default_factory=list)  # texto após "Fonte:", ex.: "(1) diferença…"
    fonte: str = ref_catalogo.FONTE_DAS_ESTIMATIVAS


def _texto(valor: object) -> str:
    if valor is None or (isinstance(valor, float) and valor != valor):
        return ""
    return re.sub(r"\s+", " ", str(valor)).strip()


def ler(caminho: Path) -> PopulacaoLida:
    """Lê um arquivo do IBGE; qualquer inconsistência levanta ErroImportacao."""
    nome = caminho.name
    try:
        df = pd.read_excel(caminho, sheet_name=ABA, engine="odf", header=None, dtype=object)
    except ValueError as erro:
        raise ErroImportacao(f"{nome}: aba {ABA} não encontrada ({erro}).") from None
    celulas = df.to_numpy().tolist()

    titulo = _texto(celulas[0][0]) if celulas else ""
    ano_titulo = ANO_DO_TITULO.search(titulo)
    ano_arquivo = ANO_DO_ARQUIVO.match(nome)
    if not ano_titulo:
        raise ErroImportacao(f"{nome}: ano não encontrado no título ({titulo!r}).")
    ano = int(ano_titulo.group(1))
    if ano_arquivo and int(ano_arquivo.group(1)) != ano:
        raise ErroImportacao(f"{nome}: o título é de {ano}, mas o nome do arquivo não.")

    linha_ancora = next(
        (i for i, linha in enumerate(celulas) if chave_de_nome(_texto(linha[0])) == ANCORA), None
    )
    if linha_ancora is None:
        raise ErroImportacao(f"{nome}: âncora {ANCORA!r} não encontrada.")

    lida = PopulacaoLida(nome, ano)
    em_notas = False
    for i in range(linha_ancora + 1, len(celulas)):
        linha = celulas[i]
        rotulo = _texto(linha[0])
        if em_notas:
            if rotulo:
                lida.notas.append(rotulo)
            continue
        if not rotulo:
            continue
        if rotulo.startswith("Fonte:"):
            em_notas = True
            continue
        try:
            localidade = resolver_localidade(rotulo)
        except KeyError as erro:
            raise ErroImportacao(f"{nome}, linha {i + 1}: {erro.args[0]}") from None
        if localidade in lida.valores:
            raise ErroImportacao(f"{nome}, linha {i + 1}: localidade repetida ({rotulo}).")
        bruto = linha[1] if len(linha) > 1 else None
        if isinstance(bruto, bool) or not isinstance(bruto, int | float | str):
            raise ErroImportacao(f"{nome}, linha {i + 1}: população inválida ({bruto!r}).")
        try:
            valor = Decimal(str(bruto).strip())
        except ArithmeticError:
            raise ErroImportacao(
                f"{nome}, linha {i + 1}: população inválida ({bruto!r})."
            ) from None
        if valor <= 0 or valor != valor.to_integral_value():
            raise ErroImportacao(f"{nome}, linha {i + 1}: população inválida ({bruto!r}).")
        lida.valores[localidade] = valor
        marca = _texto(linha[2]) if len(linha) > 2 else ""
        if marca:
            lida.marcas[localidade] = marca

    if len(lida.valores) != LOCALIDADES_ESPERADAS:
        raise ErroImportacao(
            f"{nome}: {len(lida.valores)} localidades lidas; esperadas {LOCALIDADES_ESPERADAS}."
        )
    return lida


def _localidade_das_projecoes(sigla: str) -> Localidade | None:
    if sigla == "BR":
        return Localidade(Nivel.PAIS, "BR")
    if sigla in REGIOES_NAS_PROJECOES:
        return Localidade(Nivel.REGIAO, REGIOES_NAS_PROJECOES[sigla])
    return Localidade(Nivel.UF, sigla) if sigla in REGIAO_DA_UF else None


def ler_projecoes(caminho: Path) -> list[PopulacaoLida]:
    """Lê as projeções, uma PopulacaoLida por ano; inconsistência levanta ErroImportacao."""
    nome = caminho.name
    planilha = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    try:
        linhas = planilha.worksheets[0].iter_rows(values_only=True)
        for linha in linhas:
            if chave_de_nome(_texto(linha[COLUNA_DO_GRUPO])) == ROTULO_DO_CABECALHO:
                break
        else:
            raise ErroImportacao(f"{nome}: cabeçalho {ROTULO_DO_CABECALHO!r} não encontrado.")
        esperados = list(range(PRIMEIRO_ANO, ULTIMO_ANO + 1))
        if (
            list(linha[PRIMEIRA_COLUNA_DE_ANO : PRIMEIRA_COLUNA_DE_ANO + len(esperados)])
            != esperados
        ):
            raise ErroImportacao(
                f"{nome}: os anos do cabeçalho não são {esperados[0]} a {esperados[-1]}."
            )

        lidas = {
            ano: PopulacaoLida(nome, ano, fonte=ref_catalogo.FONTE_DAS_PROJECOES)
            for ano in ANOS_DAS_PROJECOES
        }
        grupos: dict[Localidade, int] = {}
        for linha in linhas:
            sigla = _texto(linha[COLUNA_DA_SIGLA])
            if not sigla or _texto(linha[COLUNA_DO_SEXO]) != SEXO_TOTAL:
                continue
            localidade = _localidade_das_projecoes(sigla)
            if localidade is None:
                raise ErroImportacao(f"{nome}: sigla de localidade não reconhecida ({sigla}).")
            grupos[localidade] = grupos.get(localidade, 0) + 1
            for ano, lida in lidas.items():
                bruto = linha[PRIMEIRA_COLUNA_DE_ANO + ano - PRIMEIRO_ANO]
                if isinstance(bruto, bool) or not isinstance(bruto, int | float):
                    raise ErroImportacao(
                        f"{nome}: população inválida em {sigla}, {ano} ({bruto!r})."
                    )
                lida.valores[localidade] = lida.valores.get(localidade, Decimal(0)) + Decimal(
                    str(bruto)
                )
    finally:
        planilha.close()

    if len(grupos) != LOCALIDADES_ESPERADAS:
        raise ErroImportacao(
            f"{nome}: {len(grupos)} localidades lidas; esperadas {LOCALIDADES_ESPERADAS}."
        )
    incompletas = sorted(loc.sigla for loc, total in grupos.items() if total != GRUPOS_ETARIOS)
    if incompletas:
        raise ErroImportacao(
            f"{nome}: localidades sem os {GRUPOS_ETARIOS} grupos etários: {', '.join(incompletas)}."
        )
    return list(lidas.values())

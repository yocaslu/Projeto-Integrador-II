"""Leitura das estimativas populacionais do IBGE (dados/brutos/POP2024_*.ods e POP2025_*.ods).

Segue docs/importacao.md, seção 4.7: aba BRASIL_E_UFs, âncora "BRASIL E UNIDADES DA FEDERAÇÃO",
leitura até "Fonte:". O ano vem do título e é conferido com o nome do arquivo. Cada arquivo traz
as 33 localidades (Brasil, 5 regiões e 27 UFs) com os totais regionais já publicados; não há soma.
A coluna de marcas (ex.: "(1)" em PR e SC em 2025) não entra no valor: vai para o relatório.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pandas as pd

from apps.importacao.erros import ErroImportacao
from apps.importacao.linhas import Localidade
from apps.importacao.normalizacao import chave_de_nome, resolver_localidade

ABA = "BRASIL_E_UFs"
ANCORA = "brasil e unidades da federacao"
LOCALIDADES_ESPERADAS = 33
ANO_DO_TITULO = re.compile(r"DE (\d{4})\s*$")
ANO_DO_ARQUIVO = re.compile(r"^POP(\d{4})_")


@dataclass
class PopulacaoLida:
    arquivo: str
    ano: int
    valores: dict[Localidade, Decimal] = field(default_factory=dict)
    marcas: dict[Localidade, str] = field(default_factory=dict)  # marca de nota por localidade
    notas: list[str] = field(default_factory=list)  # texto após "Fonte:", ex.: "(1) diferença…"


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

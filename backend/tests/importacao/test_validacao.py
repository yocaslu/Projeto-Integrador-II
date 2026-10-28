from decimal import Decimal

from apps.importacao.leitores.fbsp import TabelaLida, ValorPublicado
from apps.importacao.leitores.ibge import PopulacaoLida
from apps.importacao.linhas import Chave, Linha, Localidade, Nivel
from apps.importacao.mapeamento import TABELAS
from apps.importacao.normalizacao import Situacao
from apps.importacao.validacao import (
    COLUNAS,
    TOLERANCIA,
    Apontamento,
    Severidade,
    diverge,
    gerar,
    taxa_por_100_mil,
)
from apps.registros.escolhas import Unidade

BA = Localidade(Nivel.UF, "BA")
BASE = {"homicidio-doloso": "100 mil habitantes", "roubo-carga": "100 mil habitantes"}
PAI = {"homicidio-doloso": "mvi", "roubo-carga": "roubo"}


def test_taxa_por_100_mil_em_precisao_total():
    taxa = taxa_por_100_mil(Decimal(5800), 14_180_000)

    assert taxa == Decimal(5800) / Decimal(14_180_000) * 100_000
    assert taxa != taxa.quantize(Decimal("0.1"))


def test_tolerancia_e_1e_6():
    assert Decimal("1e-6") == TOLERANCIA


def test_diverge_respeita_a_tolerancia_sem_arredondar():
    publicada = Decimal("40.941582612345")
    assert not diverge(publicada + Decimal("1e-6"), publicada)
    assert diverge(publicada + Decimal("1.1e-6"), publicada)
    assert diverge(Decimal("40.94"), Decimal("40.95"))


def test_diferenca_do_apontamento():
    item = Apontamento(
        "x", Severidade.DIVERGENCIA, esperado=Decimal("40.9"), obtido=Decimal("41.2")
    )
    assert item.diferenca == Decimal("0.3")
    assert Apontamento("x", Severidade.AVISO, obtido="texto").diferenca is None


def chave(ano, indicador="homicidio-doloso", unidade=Unidade.VITIMAS):
    return Chave(BA, indicador, (), unidade, ano)


def linha(ano, valor, taxa, indicador="homicidio-doloso"):
    return Linha(
        chave=chave(ano, indicador),
        valor=Decimal(valor),
        situacao=Situacao.INFORMADO,
        taxa_publicada=Decimal(taxa),
        origem=f"T03!B{ano - 2000}",
    )


def relatorio_com(linhas, publicados=(), populacao=None):
    lida = TabelaLida(TABELAS[1], publicados=list(publicados))
    pop = PopulacaoLida("POP2025.ods", 2025, populacao or {BA: Decimal(1_000_000)})
    return gerar(linhas, [lida], [pop], BASE, PAI)


def test_taxa_divergente_e_apontada():
    relatorio = relatorio_com([linha(2025, 100, "10.5")])

    [divergencia] = relatorio.de(Severidade.DIVERGENCIA)
    assert divergencia.verificacao == "taxa_calculada_x_publicada"
    assert divergencia.esperado == Decimal("10.5")
    assert divergencia.obtido == Decimal(10)
    assert relatorio.tem_divergencias


def test_taxa_igual_dentro_da_tolerancia_nao_e_apontada():
    relatorio = relatorio_com([linha(2025, 100, "10.0000000001")])
    assert not relatorio.tem_divergencias
    assert relatorio.conferidos["taxa_calculada_x_publicada"] == 1


def test_variacao_da_taxa_e_comparada_com_a_publicada():
    linhas = [linha(2024, 100, "8"), linha(2025, 100, "10")]  # 2025 calculada: 10; 2024: 8
    certa = ValorPublicado("T03", "T03!F21", "variacao", chave(2025), Decimal(25))
    errada = ValorPublicado("T03", "T03!F21", "variacao", chave(2025), Decimal(30))

    assert not relatorio_com(linhas, [certa]).tem_divergencias
    assert relatorio_com(linhas, [errada]).tem_divergencias


def test_variacao_publicada_como_marcador_vira_informacao():
    linhas = [linha(2024, 100, "8"), linha(2025, 100, "10")]
    marcador = ValorPublicado(
        "T03", "T03!F21", "variacao", chave(2025), None, Situacao.NAO_DISPONIVEL
    )

    relatorio = relatorio_com(linhas, [marcador])

    assert not relatorio.tem_divergencias
    [info] = [a for a in relatorio.de(Severidade.INFORMACAO) if "sem_numero" in a.verificacao]
    assert info.obtido == Decimal(25)


def test_salva_csv_e_resumo(tmp_path):
    relatorio = relatorio_com([linha(2025, 100, "10.5")])

    caminho_csv, caminho_md = relatorio.salvar(tmp_path, "abc123")

    conteudo = caminho_csv.read_bytes().decode()
    assert conteudo.startswith(",".join(COLUNAS) + "\r\n")
    assert "T03,T03!B25,homicidio-doloso,BA,,vitimas,2025,taxa_calculada_x_publicada" in conteudo
    resumo = caminho_md.read_text()
    assert "carga abc123" in resumo
    assert "| taxa_calculada_x_publicada | 1 | 1 |" in resumo

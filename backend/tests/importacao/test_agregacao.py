from decimal import Decimal

import pytest

from apps.importacao.agregacao import NOTA_SOMA, ErroAgregacao, agregar
from apps.importacao.linhas import Chave, Linha, Localidade, Metodo, Nivel, Unidade
from apps.importacao.normalizacao import Situacao, normalizar_celula

# Referência reduzida: duas UFs por região. "SE" é Sergipe (Nordeste) e também a sigla do Sudeste.
REGIAO_DA_UF = {"AC": "N", "PA": "N", "BA": "NE", "SE": "NE", "MG": "SE", "SP": "SE"}
# Unidade padrão de cada indicador usado nos testes, só para não repeti-la em cada linha.
UNIDADE_PADRAO = {
    "mvi": Unidade.VITIMAS,
    "homicidio-doloso": Unidade.VITIMAS,
    "morte-intervencao-policial": Unidade.VITIMAS,
    "roubo": Unidade.OCORRENCIAS,
    "roubo-celular": Unidade.OCORRENCIAS,
}
PM_EM_SERVICO = (("corporacao", "Polícia Militar"), ("situacao_policial", "Em serviço"))
PC_EM_SERVICO = (("corporacao", "Polícia Civil"), ("situacao_policial", "Em serviço"))


def linha(nivel, sigla, bruto, indicador="mvi", ano=2025, recorte=(), unidade=None, **extra):
    celula = normalizar_celula(bruto)
    unidade = unidade or UNIDADE_PADRAO[indicador]
    return Linha(
        chave=Chave(Localidade(Nivel(nivel), sigla), indicador, recorte, unidade, ano),
        valor=celula.valor,
        situacao=celula.situacao,
        **extra,
    )


def ufs(valores, **kwargs):
    """Linhas das seis UFs da referência, na ordem AC, PA, BA, SE, MG, SP."""
    return [linha("uf", uf, v, **kwargs) for uf, v in zip(REGIAO_DA_UF, valores, strict=True)]


def por_regiao(novas):
    return {n.chave.localidade.sigla: n for n in novas}


def executar(linhas):
    return agregar(linhas, REGIAO_DA_UF)


def test_soma_as_ufs_de_cada_regiao():
    novas = por_regiao(executar(ufs([10, 20, 30, 40, 50, 60], indicador="homicidio-doloso")))

    assert set(novas) == {"N", "NE", "SE"}
    assert novas["N"].valor == Decimal(30)
    assert novas["NE"].valor == Decimal(70)
    assert novas["SE"].valor == Decimal(110)
    norte = novas["N"]
    assert norte.chave == Chave(
        Localidade(Nivel.REGIAO, "N"), "homicidio-doloso", (), Unidade.VITIMAS, 2025
    )
    assert norte.situacao is Situacao.INFORMADO
    assert norte.metodo is Metodo.SOMA_UFS
    assert norte.taxa_publicada is None
    assert norte.observacao.startswith(NOTA_SOMA)


def test_sergipe_entra_no_nordeste_e_nao_no_sudeste():
    novas = por_regiao(executar(ufs([0, 0, 0, 7, 0, 0], indicador="roubo")))

    assert novas["NE"].valor == Decimal(7)
    assert novas["SE"].valor == Decimal(0)
    assert novas["SE"].chave.localidade == Localidade(Nivel.REGIAO, "SE")


def test_uf_nao_disponivel_deixa_a_regiao_nula():
    novas = por_regiao(
        executar(ufs([1, "...", 3, 4, 5, 6], indicador="morte-intervencao-policial"))
    )

    norte = novas["N"]
    assert norte.valor is None
    assert norte.situacao is Situacao.NAO_DISPONIVEL
    assert "UFs sem informação: PA." in norte.observacao
    assert novas["NE"].valor == Decimal(7)


def test_regiao_so_com_fenomeno_inexistente_fica_zero_inexistente():
    novas = por_regiao(executar(ufs(["-", "-", "-", 2, 5, "-"], indicador="roubo")))

    assert novas["N"].valor == Decimal(0)
    assert novas["N"].situacao is Situacao.INEXISTENTE
    assert novas["NE"].valor == Decimal(2)
    assert novas["NE"].situacao is Situacao.INFORMADO


def test_recortes_sao_somados_separadamente_e_nunca_juntos():
    linhas = ufs([1, 1, 1, 1, 1, 1], indicador="morte-intervencao-policial", recorte=PM_EM_SERVICO)
    linhas += ufs([2, 2, 2, 2, 2, 2], indicador="morte-intervencao-policial", recorte=PC_EM_SERVICO)

    novas = executar(linhas)

    assert len(novas) == 6
    norte = {n.chave.recorte: n.valor for n in novas if n.chave.localidade.sigla == "N"}
    assert norte == {PM_EM_SERVICO: Decimal(2), PC_EM_SERVICO: Decimal(4)}


def test_subtipos_nunca_viram_total_do_indicador_pai():
    novas = executar(ufs([1, 2, 3, 4, 5, 6], indicador="roubo-celular"))

    assert {n.chave.indicador for n in novas} == {"roubo-celular"}


def test_vitimas_e_ocorrencias_sao_somadas_separadamente():
    linhas = ufs([1, 1, 1, 1, 1, 1], indicador="homicidio-doloso", unidade=Unidade.VITIMAS)
    linhas += ufs([2, 2, 2, 2, 2, 2], indicador="homicidio-doloso", unidade=Unidade.OCORRENCIAS)

    novas = executar(linhas)

    assert len(novas) == 6
    norte = {n.chave.unidade: n.valor for n in novas if n.chave.localidade.sigla == "N"}
    assert norte == {Unidade.VITIMAS: Decimal(2), Unidade.OCORRENCIAS: Decimal(4)}


def test_brasil_e_conferido_dentro_da_mesma_unidade():
    linhas = ufs([1, 1, 1, 1, 1, 1], indicador="homicidio-doloso", unidade=Unidade.VITIMAS)
    linhas += ufs([2, 2, 2, 2, 2, 2], indicador="homicidio-doloso", unidade=Unidade.OCORRENCIAS)
    linhas.append(linha("pais", "BR", 6, indicador="homicidio-doloso", unidade=Unidade.VITIMAS))
    linhas.append(
        linha("pais", "BR", 12, indicador="homicidio-doloso", unidade=Unidade.OCORRENCIAS)
    )

    assert len(executar(linhas)) == 6


def test_unidade_nao_somavel_aborta():
    linhas = ufs([10, 20, 30, 40, 50, 60], unidade="percentual")

    with pytest.raises(ErroAgregacao, match="Unidade não somável"):
        executar(linhas)


def test_regiao_publicada_nao_e_recalculada_e_confere_com_a_soma():
    linhas = ufs([10, 20, 30, 40, 50, 60])
    linhas.append(linha("regiao", "N", 30, origem="T02!B10"))

    novas = executar(linhas)

    assert "N" not in por_regiao(novas)
    assert set(por_regiao(novas)) == {"NE", "SE"}


def test_regiao_publicada_divergente_aborta():
    linhas = ufs([10, 20, 30, 40, 50, 60])
    linhas.append(linha("regiao", "N", 31))

    with pytest.raises(ErroAgregacao, match=r"regiao=N mvi \[total\] vitimas 2025: publicado 31"):
        executar(linhas)


def test_brasil_divergente_aborta():
    linhas = ufs([10, 20, 30, 40, 50, 60], indicador="roubo")
    linhas.append(linha("pais", "BR", 200, indicador="roubo"))

    with pytest.raises(ErroAgregacao, match="soma das UFs 210"):
        executar(linhas)


def test_brasil_igual_a_soma_das_ufs_passa_sem_anotacao():
    linhas = ufs([10, 20, 30, 40, 50, 60], indicador="roubo")
    brasil = linha("pais", "BR", 210, indicador="roubo")
    linhas.append(brasil)

    executar(linhas)

    assert brasil.observacao == ""


def test_brasil_com_soma_parcial_recebe_nota():
    linhas = ufs([1, "...", 3, "...", 5, 6], indicador="morte-intervencao-policial")
    brasil = linha("pais", "BR", 15, indicador="morte-intervencao-policial", observacao="Nota.")
    linhas.append(brasil)

    executar(linhas)

    assert brasil.observacao == (
        "Nota. O total publicado pelo FBSP soma apenas as UFs que informaram o dado "
        "(4 de 6; sem informação: PA, SE)."
    )


def test_brasil_nao_disponivel_nao_e_conferido():
    linhas = ufs([1, 2, 3, 4, 5, 6], indicador="roubo")
    linhas.append(linha("pais", "BR", "...", indicador="roubo"))

    assert len(executar(linhas)) == 3


def test_uf_ausente_aborta_em_vez_de_somar_parcialmente():
    linhas = [item for item in ufs([1, 2, 3, 4, 5, 6]) if item.chave.localidade.sigla != "PA"]

    with pytest.raises(ErroAgregacao, match="Faltam UFs .*: PA"):
        executar(linhas)


def test_uf_fora_das_referencias_aborta():
    linhas = ufs([1, 2, 3, 4, 5, 6]) + [linha("uf", "XX", 1)]

    with pytest.raises(ErroAgregacao, match="UF sem região nas referências: XX"):
        executar(linhas)


def test_origem_lista_as_celulas_somadas():
    linhas = [linha("uf", uf, 1, origem=f"T03!C{n}") for n, uf in enumerate(REGIAO_DA_UF, start=10)]

    norte = por_regiao(executar(linhas))["N"]

    assert norte.origem == "T03!C10+C11"


def test_notas_das_ufs_acompanham_a_regiao():
    revisado = "Atualização das informações publicadas no Anuário."
    linhas = ufs([1, 2, 3, 4, 5, 6], indicador="homicidio-doloso", ano=2024, observacao=revisado)
    mg = next(item for item in linhas if item.chave.localidade.sigla == "MG")
    mg.observacao = f"{revisado} Inclui as mortes decorrentes de intervenções policiais."
    mg.marcas = {"4"}

    sudeste = por_regiao(executar(linhas))["SE"]

    assert sudeste.observacao == (
        f"{NOTA_SOMA} MG: {revisado} Inclui as mortes decorrentes de intervenções policiais. "
        f"SP: {revisado}"
    )
    assert sudeste.marcas == {"4"}
    nordeste = por_regiao(executar(linhas))["NE"]
    assert nordeste.observacao == f"{NOTA_SOMA} {revisado}"


def test_resultado_e_deterministico():
    linhas = ufs([1, 2, 3, 4, 5, 6], ano=2024) + ufs([6, 5, 4, 3, 2, 1], ano=2025)

    primeira = executar(linhas)
    segunda = executar(list(reversed(linhas)))

    assert primeira == segunda
    assert [n.chave for n in primeira] == sorted(n.chave for n in primeira)

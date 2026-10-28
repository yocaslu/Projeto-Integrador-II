"""Exportação em CSV (contrato, seção 5; testes da seção 8)."""

import csv
import io

import pytest

from apps.api import renderizadores
from apps.registros.models import RegistroAnual

# Copiados da seção 5.3 do contrato: a lista e a ordem das colunas são contrato.
CABECALHOS = {
    "registros": "id,ano,localidade_nivel,localidade_codigo,localidade_codigo_ibge,localidade_nome,indicador_slug,indicador_nome,recorte_id,recorte_rotulo,unidade,valor,situacao,metodo,taxa_valor,taxa_base,taxa_origem,taxa_fonte,taxa_publicada,variacao_ano_referencia,variacao_valor_pct,variacao_taxa_pct,participacao_tipo,participacao_indicador,participacao_valor_pct,fonte,observacao",  # noqa: E501 cabeçalho literal do contrato
    "populacao": "id,ano,localidade_nivel,localidade_codigo,localidade_codigo_ibge,localidade_nome,valor,fonte",  # noqa: E501 cabeçalho literal do contrato
    "ranking": "ano,indicador_slug,indicador_nome,unidade,criterio,recorte_id,recorte_rotulo,posicao,localidade_nivel,localidade_codigo,localidade_codigo_ibge,localidade_nome,valor,situacao,metodo,taxa_valor,taxa_base,taxa_origem,taxa_fonte,variacao_ano_referencia,variacao_valor_pct,variacao_taxa_pct,participacao_tipo,participacao_indicador,participacao_valor_pct,fonte,observacao",  # noqa: E501 cabeçalho literal do contrato
    "comparacao": "indicador_slug,indicador_nome,unidade,recorte_id,recorte_rotulo,localidade_nivel,localidade_codigo,localidade_codigo_ibge,localidade_nome,ano,valor,situacao,metodo,taxa_valor,taxa_base,taxa_origem,taxa_fonte,variacao_ano_referencia,variacao_valor_pct,variacao_taxa_pct,participacao_tipo,participacao_indicador,participacao_valor_pct,fonte,observacao",  # noqa: E501 cabeçalho literal do contrato
}
CONSULTAS = {
    "registros": "indicador=mvi&ano=2025",
    "populacao": "",
    "ranking": "indicador=mvi",
    "comparacao": "uf=BA&indicador=mvi&ano_min=2025",
}


def baixar(client, recurso, consulta="", **cabecalhos):
    resposta = client.get(f"/api/v1/{recurso}/?{consulta}", **cabecalhos)
    assert resposta.status_code == 200, resposta.content
    return resposta, b"".join(resposta.streaming_content)


def tabela(conteudo: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(conteudo.decode("utf-8"), newline="")))


@pytest.mark.parametrize("recurso", list(CABECALHOS))
def test_cabecalho_exato_e_dialeto(client, serie, recurso):
    resposta, conteudo = baixar(client, recurso, f"{CONSULTAS[recurso]}&formato=csv")

    assert resposta.streaming
    assert resposta["Content-Type"] == "text/csv; charset=utf-8; header=present"
    assert resposta["Content-Disposition"] == f'attachment; filename="anuario-{recurso}.csv"'
    assert "Accept" in resposta["Vary"]
    assert not conteudo.startswith(b"\xef\xbb\xbf")  # sem BOM
    primeira, *resto = conteudo.split(b"\r\n")
    assert primeira.decode() == CABECALHOS[recurso]
    assert resto[-1] == b""  # toda linha termina em \r\n, inclusive a última
    assert not any(linha.startswith(b"#") for linha in resto)  # nenhuma linha de comentário
    assert b"\n" not in conteudo.replace(b"\r\n", b"")


@pytest.mark.parametrize("recurso", list(CABECALHOS))
def test_accept_text_csv(client, serie, recurso):
    resposta, conteudo = baixar(client, recurso, CONSULTAS[recurso], HTTP_ACCEPT="text/csv")
    assert conteudo.split(b"\r\n")[0].decode() == CABECALHOS[recurso]


def test_formato_json_prevalece_sobre_accept_csv(client, serie):
    resposta = client.get("/api/v1/registros/?formato=json", HTTP_ACCEPT="text/csv")
    assert resposta["Content-Type"] == "application/json"


def test_mesmos_valores_e_ordem_do_json(client, serie):
    consulta = "nivel=pais,regiao,uf&unidade=todas&recorte=todos&ordenar=-taxa"
    json = client.get(f"/api/v1/registros/?{consulta}&tamanho=1000").json()["results"]
    _, conteudo = baixar(client, "registros", f"{consulta}&formato=csv")
    linhas = tabela(conteudo)

    assert [int(linha["id"]) for linha in linhas] == [r["id"] for r in json]
    for linha, registro in zip(linhas, json, strict=True):
        esperado = renderizadores.achatar(registro)
        assert linha == {c: "" if esperado[c] is None else str(esperado[c]) for c in linha}


def test_nulo_vira_campo_vazio_e_fonte_so_com_o_nome(client, serie):
    _, conteudo = baixar(client, "registros", "indicador=mvi&uf=AC&formato=csv")
    [acre] = tabela(conteudo)

    assert (acre["valor"], acre["taxa_valor"], acre["taxa_origem"], acre["taxa_fonte"]) == (
        "",
        "",
        "",
        "",
    )
    assert acre["situacao"] == "nao_disponivel"
    assert acre["fonte"] == serie.fontes["secretarias-seguranca"].nome
    assert (acre["recorte_id"], acre["participacao_tipo"]) == ("", "")


def test_formatos_decimais_e_achatamento(client, serie):
    _, conteudo = baixar(client, "registros", "indicador=mvi&uf=BA&ano=2025&formato=csv")
    [bahia] = tabela(conteudo)

    assert bahia["valor"] == "120"
    assert bahia["taxa_valor"] == "8.00"
    assert bahia["taxa_publicada"] == "8.000000000123"
    assert (bahia["variacao_valor_pct"], bahia["variacao_taxa_pct"]) == ("20.00", "-20.00")
    assert bahia["taxa_fonte"] == serie.fontes["ibge-estimativas"].nome
    assert (bahia["localidade_nivel"], bahia["localidade_codigo"]) == ("uf", "BA")


def test_recorte_e_participacao_achatados(client, serie):
    consulta = "indicador=morte-intervencao-policial&recorte=todos&formato=csv"
    _, conteudo = baixar(client, "registros", consulta)
    linhas = tabela(conteudo)

    pm = next(linha for linha in linhas if linha["recorte_rotulo"].startswith("Polícia Militar"))
    assert pm["recorte_id"].isdigit()
    assert (
        pm["participacao_tipo"],
        pm["participacao_indicador"],
        pm["participacao_valor_pct"],
    ) == (
        "total_do_indicador",
        "morte-intervencao-policial",
        "40.00",
    )
    assert "recorte_itens" not in pm  # os itens do recorte não entram


def test_aspas_so_quando_necessario(client, serie):
    RegistroAnual.objects.filter(estado__sigla="BA", indicador__slug="mvi", ano=2025).update(
        observacao='Nota com vírgula, "aspas" e\nquebra de linha.'
    )
    _, conteudo = baixar(client, "registros", "indicador=mvi&uf=BA&ano=2025&formato=csv")

    assert b'"Nota com v\xc3\xadrgula, ""aspas"" e\nquebra de linha."\r\n' in conteudo
    antes_da_nota = conteudo.split(b"\r\n")[1].split(b',"Nota')[0]
    assert b'"' not in antes_da_nota  # os demais campos, sem vírgula nem aspas, vêm sem aspas
    assert tabela(conteudo)[0]["observacao"] == 'Nota com vírgula, "aspas" e\nquebra de linha.'


def test_sem_dados_so_o_cabecalho(client, serie):
    _, conteudo = baixar(client, "registros", "indicador=latrocinio&formato=csv")
    assert conteudo == CABECALHOS["registros"].encode() + b"\r\n"


def test_ranking_e_comparacao_repetem_o_contexto(client, serie):
    _, ranking = baixar(client, "ranking", "indicador=mvi&formato=csv")
    _, comparacao = baixar(client, "comparacao", "uf=BA&indicador=mvi&formato=csv")
    ranking, comparacao = tabela(ranking), tabela(comparacao)

    assert [(r["posicao"], r["localidade_codigo"]) for r in ranking] == [
        ("1", "BA"),
        ("2", "SE"),
        ("3", "SP"),
        ("", "AC"),
    ]
    assert {(r["ano"], r["indicador_slug"], r["criterio"], r["unidade"]) for r in ranking} == {
        ("2025", "mvi", "taxa", "vitimas")
    }
    assert [(r["localidade_codigo"], r["ano"]) for r in comparacao] == [
        ("BA", "2024"),
        ("BA", "2025"),
        ("NE", "2025"),
        ("BR", "2025"),
    ]
    assert {r["indicador_slug"] for r in comparacao} == {"mvi"}


@pytest.mark.parametrize(
    ("consulta", "parametro"),
    [
        ("formato=csv&pagina=1", "pagina"),
        ("formato=csv&tamanho=10", "tamanho"),
        ("formato=csv&uf=XX", "uf"),
        ("formato=csv&desconhecido=1", "desconhecido"),
    ],
)
def test_erro_sai_em_json_mesmo_pedindo_csv(client, serie, consulta, parametro):
    for cabecalhos in ({}, {"HTTP_ACCEPT": "text/csv"}):
        resposta = client.get(f"/api/v1/registros/?{consulta}", **cabecalhos)
        assert resposta.status_code == 400
        assert resposta["Content-Type"].startswith("application/problem+json")
        assert parametro in {e["parametro"] for e in resposta.json()["erros"]}


def test_pagina_e_tamanho_so_sao_recusados_com_csv_pelo_accept(client, serie):
    resposta = client.get("/api/v1/registros/?pagina=1", HTTP_ACCEPT="text/csv")
    assert resposta.status_code == 400


def test_limite_de_linhas(client, serie, monkeypatch):
    monkeypatch.setattr(renderizadores, "LIMITE_LINHAS_CSV", 3)
    # MVI em todos os níveis: Brasil, Nordeste, Sudeste, BA (2024 e 2025), SE, SP e AC.
    resposta = client.get("/api/v1/registros/?indicador=mvi&nivel=pais,regiao,uf&formato=csv")

    assert resposta.status_code == 400
    assert resposta.json()["erros"] == [
        {
            "parametro": "formato",
            "mensagem": "A exportação teria 8 linhas; o limite é 3. "
            "Restrinja com ano, uf ou indicador.",
        }
    ]
    _, conteudo = baixar(client, "registros", "nivel=pais&formato=csv")  # 1 linha passa
    assert len(tabela(conteudo)) == 1


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/registros/{id}/",
        "/api/v1/regioes/",
        "/api/v1/estados/",
        "/api/v1/indicadores/",
        "/api/v1/recortes/",
        "/api/v1/fontes/",
        "/api/v1/metadados/",
    ],
)
def test_recursos_sem_csv_406(client, serie, url):
    url = url.format(id=RegistroAnual.objects.values_list("id", flat=True)[0])
    assert client.get(f"{url}?formato=csv").status_code == 406
    assert client.get(url, HTTP_ACCEPT="text/csv").status_code == 406


def test_streaming_com_poucas_consultas(client, serie, django_assert_max_num_queries):
    with django_assert_max_num_queries(12):
        _, conteudo = baixar(
            client, "registros", "nivel=pais,regiao,uf&recorte=todos&unidade=todas&formato=csv"
        )
    assert len(tabela(conteudo)) == RegistroAnual.objects.count()


def test_exportacao_completa_da_planilha(client, importado):
    _, conteudo = baixar(
        client, "registros", "nivel=pais,regiao,uf&unidade=todas&recorte=todos&formato=csv"
    )
    linhas = tabela(conteudo)

    assert len(linhas) == RegistroAnual.objects.count() == 1254
    assert all(linha["fonte"] and linha["situacao"] for linha in linhas)  # RF11, RNF12

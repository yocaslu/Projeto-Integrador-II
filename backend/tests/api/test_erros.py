from rest_framework import exceptions
from rest_framework.test import APIRequestFactory

from apps.api.erros import manipulador_problem_details


def test_metodo_de_escrita_retorna_405_em_problem_details(client):
    resposta = client.post("/api/v1/schema/")

    assert resposta.status_code == 405
    assert resposta["Content-Type"].startswith("application/problem+json")
    assert "GET" in resposta["Allow"]
    corpo = resposta.json()
    assert corpo["status"] == 405
    assert corpo["title"] == "Método não permitido"
    assert corpo["instance"] == "/api/v1/schema/"


def test_erro_de_validacao_lista_os_parametros():
    request = APIRequestFactory().get("/api/v1/registros/?ano=20255")
    erro = exceptions.ValidationError({"ano": ["Ano fora do intervalo disponível."]})

    resposta = manipulador_problem_details(erro, {"request": request})

    assert resposta.status_code == 400
    assert resposta.data["type"].endswith("/api/v1/docs/erros#parametro-invalido")
    assert resposta.data["erros"] == [
        {"parametro": "ano", "mensagem": "Ano fora do intervalo disponível."}
    ]

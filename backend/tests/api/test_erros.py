import json

from rest_framework import exceptions
from rest_framework.renderers import BaseRenderer
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.api.erros import manipulador_problem_details


class RenderizadorCsvDeTeste(BaseRenderer):
    media_type = "text/csv"
    format = "csv"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return b"nao,deveria,aparecer\r\n"


class ViewCsvComErro(APIView):
    renderer_classes = [RenderizadorCsvDeTeste]
    versioning_class = None  # chamada sem passar pelas rotas, que fornecem a versão da URL

    def get(self, request, *args, **kwargs):
        raise exceptions.ValidationError({"uf": ["UF inexistente: XX."]})


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


def test_erro_sai_em_json_quando_a_view_negocia_csv():
    request = APIRequestFactory().get("/api/v1/registros/?uf=XX", HTTP_ACCEPT="text/csv")

    resposta = ViewCsvComErro.as_view()(request)
    resposta.render()

    assert resposta.status_code == 400
    assert resposta["Content-Type"].startswith("application/problem+json")
    corpo = json.loads(resposta.content)
    assert corpo["erros"] == [{"parametro": "uf", "mensagem": "UF inexistente: XX."}]

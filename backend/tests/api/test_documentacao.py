def test_esquema_openapi_disponivel(client):
    resposta = client.get("/api/v1/schema/")
    assert resposta.status_code == 200


def test_swagger_disponivel(client):
    resposta = client.get("/api/v1/docs/")
    assert resposta.status_code == 200

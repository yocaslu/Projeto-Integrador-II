def test_esquema_openapi_disponivel(client):
    resposta = client.get("/api/v1/schema/")
    assert resposta.status_code == 200


def test_swagger_disponivel(client):
    resposta = client.get("/api/v1/docs/")
    assert resposta.status_code == 200


def test_esquema_lista_as_rotas_versionadas(client):
    """Com URLPathVersioning, sem DEFAULT_VERSION o esquema sairia com `paths: {}`."""
    esquema = client.get("/api/v1/schema/", HTTP_ACCEPT="application/json")
    assert "/api/v1/regioes/" in esquema.content.decode()


def test_comando_spectacular_gera_as_rotas(tmp_path):
    from django.core.management import call_command

    destino = tmp_path / "openapi.yaml"
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(destino))
    assert "/api/v1/indicadores/{slug}/:" in destino.read_text()

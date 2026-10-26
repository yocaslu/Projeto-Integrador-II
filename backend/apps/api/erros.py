"""Respostas de erro no padrão Problem Details (RFC 9457).

Configurado em REST_FRAMEWORK["EXCEPTION_HANDLER"]. Erros 500 não passam por aqui: o Django
devolve uma resposta genérica, sem detalhes técnicos.
"""

from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

TIPO_CONTEUDO = "application/problem+json"

PROBLEMAS = {
    400: ("parametro-invalido", "Parâmetro inválido"),
    404: ("nao-encontrado", "Recurso não encontrado"),
    405: ("metodo-nao-permitido", "Método não permitido"),
    406: ("formato-nao-suportado", "Formato não suportado"),
    429: ("limite-excedido", "Limite de requisições excedido"),
}

CABECALHOS_PRESERVADOS = ("Allow", "Retry-After", "WWW-Authenticate")


def _lista_de_erros(dados) -> list[dict[str, str]]:
    """Converte os erros de validação do DRF em [{"parametro": ..., "mensagem": ...}]."""
    if isinstance(dados, dict):
        return [
            {"parametro": str(parametro), "mensagem": str(mensagem)}
            for parametro, mensagens in dados.items()
            for mensagem in (mensagens if isinstance(mensagens, list) else [mensagens])
        ]
    mensagens = dados if isinstance(dados, list) else [dados]
    return [{"parametro": "", "mensagem": str(mensagem)} for mensagem in mensagens]


def manipulador_problem_details(exc, context):
    resposta = exception_handler(exc, context)
    if resposta is None:
        return None

    request = context["request"]
    status = resposta.status_code
    slug, titulo = PROBLEMAS.get(status, ("erro", "Erro"))

    corpo = {
        "type": request.build_absolute_uri(f"/api/v1/docs/erros#{slug}"),
        "title": titulo,
        "status": status,
        "instance": request.get_full_path(),
    }
    if isinstance(exc, exceptions.ValidationError):
        corpo["detail"] = "Um ou mais parâmetros de consulta são inválidos."
        corpo["erros"] = _lista_de_erros(exc.detail)
    else:
        corpo["detail"] = str(getattr(exc, "detail", titulo))

    cabecalhos = {
        nome: resposta[nome] for nome in CABECALHOS_PRESERVADOS if resposta.has_header(nome)
    }
    return Response(corpo, status=status, headers=cabecalhos, content_type=TIPO_CONTEUDO)

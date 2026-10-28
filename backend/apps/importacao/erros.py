"""Erros da importação. Qualquer um deles desfaz a transação inteira (regra 7)."""


class ErroImportacao(Exception):
    """Dado da planilha incompatível com a especificação; a mensagem cita aba e célula."""

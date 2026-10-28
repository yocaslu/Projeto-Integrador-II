"""Negociação de conteúdo da API (contrato, seção 5.1).

- `formato` (`json` | `csv`) tem precedência sobre o cabeçalho `Accept`;
- sem os dois, ou com `Accept: */*`, JSON;
- formato desconhecido, ou CSV num recurso sem CSV, → 406 (o DRF devolveria 404 para o
  formato pela URL);
- `Accept` sem nenhum tipo suportado → 406 (comportamento padrão do DRF).
"""

from rest_framework.exceptions import NotAcceptable
from rest_framework.negotiation import DefaultContentNegotiation


class NegociacaoPorFormato(DefaultContentNegotiation):
    def select_renderer(self, request, renderers, format_suffix=None):
        formato = format_suffix or request.query_params.get(self.settings.URL_FORMAT_OVERRIDE)
        if formato:
            for renderer in renderers:
                if renderer.format == formato:
                    return renderer, renderer.media_type
            raise NotAcceptable(f"Formato não suportado neste recurso: {formato}.")
        return super().select_renderer(request, renderers, format_suffix)

"""Modelos de catálogo: FONTES, INDICADORES, RECORTES e RECORTE_ITENS.

- Fonte: origem dos dados (secretarias estaduais, IBGE, Senatran, Banco Central e FBSP).
- Indicador: indicadores e subtipos de crime, em hierarquia pela autorrelação indicador_pai,
  com slug (usado na API), unidade e base_taxa.
- Recorte e RecorteItem: grupos de vítimas ou de agentes, formados por pares de dimensão e
  valor, como corporacao = Polícia Militar.
"""

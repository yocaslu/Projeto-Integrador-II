"""Modelos de catálogo: FONTES, INDICADORES, RECORTES e RECORTE_ITENS.

- Fonte: origem dos dados (secretarias estaduais, IBGE, Senatran, Banco Central e FBSP).
- Indicador: indicadores e subtipos de crime, em hierarquia pela autorrelação indicador_pai
  ("contido em", nunca "soma de"), com slug (usado na API), ordem, unidade_padrao e base_taxa.
  A unidade de cada valor fica no registro (ADR 0004).
- Recorte e RecorteItem: grupos de agentes, formados por pares de dimensão e valor, como
  corporacao = Polícia Militar (dimensões: corporacao e situacao_policial).
"""

"""Modelo REGISTROS_ANUAIS, a tabela de fatos.

Cada registro guarda o valor de um indicador em um ano, para um estado ou uma região e,
opcionalmente, para um recorte. Restrições previstas:

- exatamente um entre estado e regiao preenchido (CheckConstraint);
- unicidade de localidade, indicador, recorte e ano com nulls_distinct=False
  (NULLS NOT DISTINCT, PostgreSQL 18);
- valor e taxa_publicada em DecimalField, que corresponde a NUMERIC (RNF10);
- situacao com as marcações originais: informado, inexistente ou nao_disponivel (RF11);
- metodo: publicado (lido da planilha) ou soma_ufs (total regional calculado na importação
  como soma das UFs, nos indicadores cuja tabela não publica regiões; ver ADR 0002). Em
  soma_ufs, origem e taxa_publicada são nulos.
"""

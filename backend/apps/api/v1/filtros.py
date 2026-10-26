"""FilterSets da versão 1.

Diferente do comportamento padrão do django-filter, um parâmetro desconhecido deve retornar 400,
para que um erro de digitação como uf_=SP não devolva os dados do Brasil inteiro.
"""

"""Serializers da versão 1.

Valores e taxas são serializados como texto ("41.2"), padrão do DRF para DecimalField, o que
preserva a precisão do tipo NUMERIC (RNF10).
"""

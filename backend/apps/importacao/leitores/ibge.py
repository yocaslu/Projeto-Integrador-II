"""Leitura das estimativas populacionais do IBGE (dados/brutos/POP2024_*.ods e POP2025_*.ods).

Responsabilidades previstas:

- abrir as planilhas .ods com pandas e odfpy;
- extrair a população de cada UF, de cada região e do Brasil;
- devolver linhas (localidade, ano, valor) para a entidade POPULACAO.
"""

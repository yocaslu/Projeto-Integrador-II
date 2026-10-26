"""Leitura da planilha do Anuário (dados/brutos/anuario-2026.xlsx).

Responsabilidades previstas:

- abrir cada tabela da planilha com pandas e openpyxl;
- localizar as linhas de UF, região e Brasil e as colunas de ano;
- devolver linhas brutas (localidade, indicador, recorte, ano, valor, taxa publicada, nota),
  sem gravar nada no banco; a gravação fica no comando importar_anuario.
"""

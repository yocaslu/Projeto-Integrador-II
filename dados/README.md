# Dados

## `brutos/`

Arquivos oficiais usados pelo comando `importar_anuario`. São versionados para que a importação
possa ser reproduzida mesmo se as fontes trocarem os arquivos publicados. Ao substituir um
arquivo, atualize a tabela abaixo (`sha256sum dados/brutos/*`).

| Arquivo | Fonte | Conteúdo | SHA-256 |
| --- | --- | --- | --- |
| `anuario-2026.xlsx` | Fórum Brasileiro de Segurança Pública (FBSP) | Planilha do 20º Anuário Brasileiro de Segurança Pública | `6b01f4edfa3922cdbcbe46789b1c436a862fee63f9b1f5a712362000dc784f21` |
| `POP2024_20241230.ods` | IBGE | Estimativas populacionais de 2024 | `a1a05b51982d8ac398f1069bf2f2756c13d7b785c92302146bd490c266e14664` |
| `POP2025_20260828.ods` | IBGE | Estimativas populacionais de 2025 | `748303510fb724f11a6e36b3d3ba19d1655397cacabe7dad5ba82ac11d781629` |

Pendente: registrar a URL de download e a data de acesso de cada arquivo.

## `relatorios/`

Relatórios de validação gerados a cada importação (RF12), com as divergências entre as taxas
calculadas e as publicadas pelo FBSP. Não são versionados.

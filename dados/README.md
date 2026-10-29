# Dados

## `brutos/`

Arquivos oficiais usados pelo comando `importar_anuario`. São versionados para que a importação
possa ser reproduzida mesmo se as fontes trocarem os arquivos publicados. Nunca edite um arquivo
daqui: nova versão de planilha é arquivo novo, com o novo hash na tabela abaixo, em commit próprio.

**Esta tabela é o manifesto que o `importar_anuario` lê** (`--manifesto`, padrão: este arquivo).
Todo arquivo listado precisa existir em `brutos/` com o mesmo SHA-256 (`sha256sum dados/brutos/*`),
senão a importação aborta antes de gravar. Mantenha o formato das linhas: nome e hash entre
crases, o hash na última coluna.

| Arquivo | Fonte | Conteúdo | SHA-256 |
| --- | --- | --- | --- |
| `anuario-2026.xlsx` | Fórum Brasileiro de Segurança Pública (FBSP) | Planilha do 20º Anuário Brasileiro de Segurança Pública | `6b01f4edfa3922cdbcbe46789b1c436a862fee63f9b1f5a712362000dc784f21` |
| `POP2024_20241230.ods` | IBGE | Estimativas populacionais de 2024 | `a1a05b51982d8ac398f1069bf2f2756c13d7b785c92302146bd490c266e14664` |
| `POP2025_20260828.ods` | IBGE | Estimativas populacionais de 2025 | `748303510fb724f11a6e36b3d3ba19d1655397cacabe7dad5ba82ac11d781629` |

Pendente: registrar a URL de download e a data de acesso de cada arquivo.

### Edições anteriores (ainda não importadas)

Planilhas de edições anteriores do Anuário, guardadas para estender as séries históricas. **Ficam
fora do manifesto de propósito**: hoje o `importar_anuario` aceita uma única planilha `.xlsx`, e
estas edições têm outra numeração de tabelas, que o `mapeamento.py` ainda não cobre. Os hashes
ficam nesta lista, e não na tabela, para que o importador não os leia. Ao incorporar uma edição à
importação, a linha dela passa para a tabela acima no mesmo commit da mudança do importador.

- `anuario-2025.xlsx`: planilha do 19º Anuário Brasileiro de Segurança Pública (FBSP, 2025), com dados de 2023 e 2024 e a série de MVI de 2012 a 2024. Origem: <https://forumseguranca.org.br/wp-content/uploads/2025/09/anuario-2025.xlsx>, acesso em 29/10/2026. SHA-256: `23f187480418d15071272e859e1cc3ebcffc515816353aee91906f8e86660f04`.
- `anuario-2024.xlsx`: planilha do 18º Anuário Brasileiro de Segurança Pública (FBSP, 2024), publicada no repositório do FBSP como "PLANILHA Anuário Brasileiro de Segurança Pública.xlsx", com dados de 2022 e 2023. Origem: <https://publicacoes.forumseguranca.org.br/handle/123456789/253>, acesso em 29/10/2026. SHA-256: `69121cc6954c2a6ef1c30e13bf3b73d19feb1914f97f5e5bf4dbc47a0d755ab6`.

## `relatorios/`

Relatórios de validação gerados a cada importação (RF12), em `validacao-<versao>.csv` (um
apontamento por linha) e `validacao-<versao>.md` (resumo). Comparam, sem arredondar e com
tolerância de 1e-6, as taxas calculadas pela população do IBGE com as publicadas, a variação da
taxa com a coluna "Variação (%)", a participação com as proporções da T09 e da T21 e as tabelas de
conferência (T01, T09); também trazem informações (regiões calculadas, somas parciais, contagem
por situação) e avisos (células vazias, registros órfãos). Não são versionados. Especificação em
`docs/importacao.md`, seção 5.

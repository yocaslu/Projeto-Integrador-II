# 0007. Implementação do modelo e da importação

- Data: 2026-10-28
- Situação: aceita

## Contexto

O CLAUDE.md lista 13 ajustes ao modelo do Roteiro, a registrar em ADR quando fossem
implementados. Os ADRs 0003 a 0005 explicam os ajustes 7 e 9 a 13; os ajustes 1 a 6 e 8 só
estavam descritos no CLAUDE.md e nos ADRs 0002 e 0003. A implementação dos modelos, das migrações
iniciais e do comando `importar_anuario` também exigiu algumas decisões que a especificação
(`docs/importacao.md`) deixava em aberto.

## Decisão

### 1. Ajustes ao modelo do Roteiro (todos na migração 0001 de cada app)

| # | Ajuste | Onde |
| ---: | :--- | :--- |
| 1 | `INDICADORES.slug` único | `catalogo.Indicador` |
| 2 | `codigo_ibge` em `ESTADOS` (único) e `REGIOES` (único por `tipo`), `CharField(2)` | `localidades` |
| 3 | `RECORTES.chave` única (`dimensao=valor;...`, pares em ordem) | `catalogo.Recorte` |
| 4 | `REGISTROS_ANUAIS.origem` (`T08!D15`; células somadas em `soma_ufs`), `max_length=200` | `registros.RegistroAnual` |
| 5 | Entidade `CARGAS` (`versao`, `arquivos` com nome e SHA-256, `iniciada_em`, `concluida_em`, `status`, `total_registros`) | `importacao.Carga` |
| 6 | `POPULACAO` com CHECK de localidade e unicidade (localidade, ano) `NULLS NOT DISTINCT` | `localidades.Populacao` |
| 7 | `taxa_publicada` `NUMERIC(24, 12)`, arredondada na importação (ADR 0003) | `normalizacao.normalizar_taxa` |
| 8 | `REGISTROS_ANUAIS.metodo` (`publicado` \| `soma_ufs`, ADR 0002) | `registros.RegistroAnual` |
| 9 | `INDICADORES.ordem` (pré-ordem, ADR 0003) | `catalogo.Indicador` |
| 10 | `REGISTROS_ANUAIS.unidade` na chave única (ADR 0004) | `registros.RegistroAnual` |
| 11 | `INDICADORES.unidade_padrao` (ADR 0004) | `catalogo.Indicador` |
| 12 | `INDICADORES.fonte_taxa`, com CHECK de coerência com `base_taxa` (ADR 0005) | `catalogo.Indicador` |
| 13 | `FONTES.slug` e ids fixos 1 a 5 (ADR 0005) | `catalogo.Fonte` |

### 2. Decisões da implementação

1. **Escolhas compartilhadas.** `Situacao`, `Metodo` e `Unidade` são `TextChoices` em
   `apps/registros/escolhas.py`, usadas pelos modelos e pela importação (`linhas`, `normalizacao`,
   `agregacao`), sem duas definições que possam divergir. Os rótulos são os de `/metadados/`
   (contrato, 4.10).
2. **Constraints a mais no banco (regra 14).** Além das previstas: `situacao` coerente com
   `valor` (`informado` → não nulo; `inexistente` → 0; `nao_disponivel` → nulo) e `soma_ufs` sem
   `taxa_publicada`.
3. **Nulo em `observacao` e `base_taxa`.** São campos de texto anuláveis: nulo é "sem nota" e
   "sem base de taxa", o `null` que a API expõe e o par de `fonte_taxa` no CHECK. A regra DJ001
   do Ruff é dispensada nessas duas linhas, com a justificativa no comentário.
4. **Manifesto de hashes.** O comando lê os hashes da tabela de `dados/README.md` (o
   `README.md` acima de `--dados`; outro arquivo com `--manifesto`). Todo arquivo listado precisa
   existir com o mesmo SHA-256; o manifesto precisa listar uma `.xlsx` e as `.ods`.
5. **Carga.** Criada antes da transação, com `status = em_andamento`; concluída dentro dela; marcada
   `falhou` se a importação abortar. `--somente-validar` não cria carga nem grava nada (a
   transação é desfeita). `--estrito` faz o comando terminar com erro depois de gravar, para o CI
   ou um script notarem a divergência.
6. **Ordem dos recortes.** Criados na ordem dos blocos de `mapeamento.py`, como diz o contrato
   (4.4): 1 PC em serviço, 2 PM em serviço, 3 PC fora de serviço, 4 PM fora de serviço. Os ids dos
   exemplos do contrato são ilustrativos.
7. **Notas de rodapé.** Vão para `observacao` as notas marcadas no rótulo da linha e no ano do
   cabeçalho, em ordem numérica. A nota marcada no grupo de taxa declara a base (é conferida, seção
   4.3) e não descreve o dado, por isso não entra.
8. **Variação e proporção com "-" ou "...".** São marcadores, não números: não entram na
   comparação com tolerância. O relatório registra uma informação quando o sistema calcula um
   número onde a planilha não publicou nenhum (na planilha versionada, 6 casos na T15). Sem isso,
   18 células da T15 apareciam como divergência, embora nenhuma fosse diferença numérica.
9. **Fluxo testável.** O fluxo está em `apps/importacao/processo.py` e recebe as tabelas do
   mapeamento por parâmetro; os testes usam planilhas reduzidas (`tests/fixtures/planilhas/`,
   geradas por script), com todas as linhas das abas mantidas, porque a agregação exige todas as
   UFs. A planilha real é importada num passo próprio do CI (`pytest -m planilha_real`).

## Consequências

- Um banco limpo, depois de `migrate` e `importar_anuario`, tem 1.980 registros (230 `soma_ufs`,
  24 deles `nao_disponivel`), 66 populações, 18 indicadores, 5 fontes, 4 recortes e 33
  localidades, com os ids de fontes e recortes reproduzíveis. A segunda execução não muda
  contagem, ids nem valores.
- O relatório da planilha versionada não tem divergência acima de 1e-6: 850 taxas, 560
  variações, 112 participações e 224 conferências de T01 e T09.
- O exemplo de `/recortes/` do contrato (id 3 = Polícia Militar, em serviço) não corresponde aos
  ids reais; por ser ilustrativo, o contrato não muda.
- O CI ganha dois passos no job do backend: `makemigrations --check --dry-run` e a importação da
  planilha real.

# 0005. Fonte do denominador da taxa, catálogo de fontes, API sem carga e método do RNF02

- Data: 2026-10-27
- Situação: aceita

## Contexto

A avaliação do contrato da API v1 (ADRs 0002–0004) apontou quatro lacunas que o contrato e o
modelo ainda não resolviam:

1. **Fonte da taxa.** O contrato exige `taxa.fonte` (a fonte do **denominador**: IBGE, Senatran ou
   Banco Central) em todo registro, mas nenhum atributo do modelo liga o indicador ou a
   `base_taxa` a uma `FONTE`. A decisão afeta todos os serializers de registro.
2. **Catálogo de `FONTES`.** Não estavam definidos nome, descrição, URL e ordem de criação de cada
   fonte. O contrato usa ids nos exemplos e ordena `/fontes/` por `id`, então os ids precisam ser
   estáveis, como já se exige dos recortes.
3. **Banco sem carga concluída.** O ETag (`W/"<versao>-json"`) e o campo `carga` de `/metadados/`
   dependem da última `Carga` concluída, e não estava definido o que a API faz quando não há
   nenhuma.
4. **Método do teste do RNF02.** O requisito (p95 < 500 ms em consultas filtradas por UF, ano e
   indicador) não dizia volume, número de requisições, consultas nem ambiente.

Conferido na planilha versionada (rodapés e notas de T01–T21): as taxas por 100 mil habitantes
usam as estimativas do IBGE ("Estimativas da população residente … 1º de julho"); a T21 (taxa por
100 mil mulheres) cita as **projeções** da população do IBGE, não as estimativas; a T11 usa a frota
da Senatran de dezembro de cada ano (nota 2); e a T15 usa a quantidade de instituições financeiras
do Banco Central de dezembro de cada ano (nota 3).

## Decisão

### 1. `INDICADORES.fonte_taxa` (ajuste 12 do modelo)

- `Indicador.fonte_taxa = ForeignKey(Fonte, null=True, on_delete=PROTECT, related_name="+")`,
  preenchida por `catalogo/referencia.py` junto com `base_taxa`.
- Nula **se e somente se** `base_taxa` é nula (hoje, só o agrupador `furto`), garantido por
  `CheckConstraint` no banco.
- Mapeamento:

  | `base_taxa` | `fonte_taxa` (slug) |
  | :--- | :--- |
  | 100 mil habitantes | `ibge-estimativas` |
  | 100 mil mulheres | `ibge-projecoes` |
  | 100 mil veículos | `senatran-frota` |
  | 100 instituições | `bcb-instituicoes` |

- Na API, `taxa.fonte` = `indicador.fonte_taxa` sempre que `taxa.valor` não é nulo, com
  `origem` `calculada` ou `publicada` (a taxa publicada pelo FBSP usa o mesmo denominador). Quando
  `taxa.valor` é nulo, `taxa.fonte` é nula. As consultas usam
  `select_related("indicador__fonte_taxa")`, sem consulta extra por registro.
- Coerência verificada por teste: nos indicadores com base 100 mil habitantes, `fonte_taxa` é a
  mesma fonte das linhas de `POPULACAO`, que é o denominador da taxa calculada.
- Alternativa descartada: mapa fixo `base_taxa → fonte` só no código. A ligação ficaria invisível
  no banco e para quem consulta o esquema, e `/indicadores/` e `/metadados/` não poderiam expô-la
  com um `select_related`.

### 2. `FONTES.slug` (ajuste 13 do modelo) e catálogo fixo

- `Fonte.slug = SlugField(max_length=50, unique=True)`. A importação cria as fontes com
  `update_or_create(slug=…)`, **antes** de qualquer outra referência e **nesta ordem**, de modo que
  um banco limpo reproduz os mesmos `id`s (há teste). Fonte nova entra **no fim** da lista; nenhuma
  é reordenada nem removida.

  | `id` | `slug` | `nome` | Usada em |
  | ---: | :--- | :--- | :--- |
  | 1 | `secretarias-seguranca` | Secretarias Estaduais de Segurança Pública e/ou Defesa Social (compilação FBSP) | `REGISTROS_ANUAIS.fonte` (todos, inclusive `soma_ufs`) |
  | 2 | `ibge-estimativas` | IBGE – Estimativas da população residente | `POPULACAO.fonte`; `fonte_taxa` da base 100 mil habitantes |
  | 3 | `ibge-projecoes` | IBGE – Projeções da população | `fonte_taxa` da base 100 mil mulheres |
  | 4 | `senatran-frota` | Senatran – Frota de veículos | `fonte_taxa` da base 100 mil veículos |
  | 5 | `bcb-instituicoes` | Banco Central do Brasil – Instituições financeiras | `fonte_taxa` da base 100 instituições |

- Descrições e URLs:

  | `slug` | `descricao` | `url` |
  | :--- | :--- | :--- |
  | `secretarias-seguranca` | Registros policiais das secretarias estaduais de segurança pública e defesa social, do ISP/RJ e de polícias civis e militares de alguns estados, compilados pelo Fórum Brasileiro de Segurança Pública no 20º Anuário Brasileiro de Segurança Pública (2026). A linha "Fonte:" completa de cada tabela está em `docs/importacao.md`. | `https://publicacoes.forumseguranca.org.br/items/bb542342-3cf8-47a5-a51d-a0eb911914b9` |
  | `ibge-estimativas` | Estimativas da população residente no Brasil e nas Unidades da Federação, com data de referência em 1º de julho de 2024 e de 2025. | `https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html` |
  | `ibge-projecoes` | Projeções da população do Brasil e das Unidades da Federação por sexo e idade, usadas pelo FBSP no denominador das taxas por 100 mil mulheres. | `https://www.ibge.gov.br/estatisticas/sociais/populacao/9109-projecao-da-populacao.html` |
  | `senatran-frota` | Frota de veículos registrada no RENAVAM e informada pela Secretaria Nacional de Trânsito (Ministério dos Transportes) em dezembro de 2024 e de 2025. | `https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/estatisticas-frota-de-veiculos-senatran` |
  | `bcb-instituicoes` | Quantidade de instituições financeiras (bancos, caixas eletrônicos e empresas de transporte de valores) informada pelo Banco Central do Brasil em dezembro de 2024 e de 2025. | `https://www.bcb.gov.br/estabilidadefinanceira/relacao_instituicoes_funcionamento` |

- `/fontes/` passa a trazer `slug`. O resumo `{"id", "nome"}` dentro dos registros não muda.

### 3. Sem carga concluída: 503

- A "carga atual" é a `Carga` com `status = concluida` e o maior `concluida_em`. Cargas
  `em_andamento` ou `falhou` são ignoradas: como a importação roda em uma transação, a carga
  anterior continua valendo até a nova ser concluída.
- Se não existe nenhuma carga concluída, **todo recurso de `/api/v1/`** (catálogos, consultas,
  detalhes e `/metadados/`) responde **503** em Problem Details, com `title` "Serviço
  indisponível" e `detail` "Nenhuma carga de dados foi concluída. Tente novamente mais tarde.",
  `Cache-Control: no-store` e **sem** `ETag`. A verificação vem depois da validação de método
  (405) e de formato (406), e antes da validação de parâmetros.
- Ficam fora da regra: `/api/v1/schema/`, `/api/v1/docs/` e `/api/v1/redoc/`, que não dependem dos
  dados.
- Motivo: devolver listas vazias com 200 seria cacheado por 24 h (`max-age=86400`) por clientes e
  intermediários, e o dashboard mostraria "sem dados" muito depois da primeira importação. Também
  não haveria intervalo de anos para validar `ano` (contrato, seção 2, regra 8).

### 4. Método do teste do RNF02

- **Onde:** `backend/tests/desempenho/test_p95.py`, com o marker `desempenho`, fora da execução
  padrão (`addopts` com `-m "not desempenho and not planilha_real"`) e em um passo próprio do job
  do backend no CI: `uv run pytest -m desempenho --no-cov`.
- **Ambiente:** o do CI (`ubuntu-latest`, PostgreSQL 18 como serviço) e, localmente, o
  `docker compose` com `db` e `backend`. `DEBUG = False` (`config.settings.test`).
- **Volume:** a carga real completa, importada uma vez por sessão a partir de `dados/brutos/` pelo
  próprio `importar_anuario`: 1.980 registros e 66 linhas de população. Não se infla o banco: o
  RNF02 trata das consultas que o sistema de fato serve.
- **Cliente:** `django.test.Client`, em processo. Mede roteamento, middlewares, validação,
  consultas ao PostgreSQL, serialização e, no CSV, o consumo completo do streaming
  (`b"".join(resposta.streaming_content)`). Não mede rede nem Traefik. Sem `If-None-Match`: toda
  requisição monta a resposta.
- **Consultas** (as filtradas por UF, ano e indicador, mais as que o dashboard faz com os mesmos
  filtros), com os indicadores `mvi`, `homicidio-doloso`, `feminicidio`,
  `morte-intervencao-policial` e `roubo`:

  | Recurso | Requisições medidas |
  | :--- | ---: |
  | `/registros/?uf=<UF>&ano=<ano>&indicador=<slug>` (27 UFs × 2024 e 2025 × 5 indicadores) | 270 |
  | O mesmo com `formato=csv` | 270 |
  | `/ranking/?indicador=<slug>&ano=<ano>` (5 × 2), repetido 3 vezes | 30 |
  | `/comparacao/?uf=<UF>&indicador=<slug>` (27 × 5) | 135 |

- **Aquecimento:** as 20 primeiras requisições de cada recurso são feitas e descartadas.
- **Medida:** `time.perf_counter()` em volta de cada requisição; toda resposta precisa ser 200.
- **Critério:** p95 de **cada recurso** < 500 ms, com
  `statistics.quantiles(tempos, n=20, method="inclusive")[18]`. Na falha, a mensagem traz p50,
  p95 e máximo do recurso.
- O mesmo teste aplica `django_assert_max_num_queries` a uma requisição de cada recurso, para que
  uma regressão N+1 apareça mesmo quando o tempo ainda passa.

## Consequências

- Modelo: `INDICADORES.fonte_taxa` (FK anulável, com `CheckConstraint` de coerência com
  `base_taxa`) e `FONTES.slug` (único) entram na primeira migração de `catalogo`, que ainda não
  existe; não há dado a migrar.
- `catalogo/referencia.py` passa a ter a lista de fontes e o `fonte_taxa` de cada indicador; o
  teste de referências verifica que todo slug de fonte usado existe.
- Contrato: exemplos com `fonte.id = 1` (secretarias) e `taxa.fonte.id = 2` (IBGE); `/fontes/` com
  `slug`; `/indicadores/` e `/metadados/` com `fonte_taxa`; status 503 na seção de erros; regra
  de cache para a ausência de carga; testes novos na seção 8. Como a v1 ainda não foi publicada,
  nada disso exige `/api/v2/`.
- A taxa por 100 mil mulheres cita as projeções do IBGE, não as estimativas que a API usa nas
  taxas calculadas. Como a população feminina não está em `POPULACAO`, essa taxa é sempre
  `publicada` (UFs e Brasil) ou nula (regiões), e a fonte exibida é a que o FBSP usou.
- O teste de desempenho depende da importação da planilha real e não entra na cobertura; um p95
  acima do limite falha o CI.
- As URLs das fontes são as páginas de produto em 2026-10-27; quando mudarem, o `update_or_create`
  por `slug` atualiza o catálogo sem mudar os `id`s.

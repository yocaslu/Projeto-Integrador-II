# Modelagem de dados

Transcrição da seção "Modelagem de dados" do Roteiro, atualizada com os ajustes decididos e
implementados (ADRs 0002 a 0005 e 0007). **Este arquivo é a fonte da verdade da modelagem**; onde o
Roteiro diverge dele, vale este arquivo. O diagrama entidade-relacionamento (Figura 3 do Roteiro)
está em [`modelagem/`](modelagem/) (`modelo-er.svg`, gerado de `modelo-er.dot`).

Os modelos ficam em `backend/apps/<app>/models.py`; as escolhas fixas (situação, método, unidade),
em `backend/apps/registros/escolhas.py`. Mudança aqui exige migração no mesmo commit (regra 13).

---

## 1. Visão geral

A partir da planilha do 20º Anuário Brasileiro de Segurança Pública (FBSP, 2026) e das
estimativas populacionais do IBGE, foram definidas **nove entidades**: REGIOES, ESTADOS,
POPULACAO, FONTES, INDICADORES, RECORTES, RECORTE_ITENS, REGISTROS_ANUAIS e CARGAS.

REGISTROS_ANUAIS é a **tabela de fatos**: cada registro guarda o valor de um indicador em um ano e
em uma unidade (vítimas ou ocorrências), para uma localidade e, quando houver, para um recorte, com
a fonte de referência. CARGAS registra cada execução da importação e não se relaciona com as demais.

| App | Entidades |
| :--- | :--- |
| `localidades` | REGIOES, ESTADOS, POPULACAO |
| `catalogo` | FONTES, INDICADORES, RECORTES, RECORTE_ITENS |
| `registros` | REGISTROS_ANUAIS |
| `importacao` | CARGAS |

Só o comando `importar_anuario` grava nessas tabelas (RNF06); a API apenas lê.

## 2. Localidades

As cinco regiões e o total nacional ficam em REGIOES, distinguidos por `tipo` (`regiao` ou
`pais`), e cada estado pertence a exatamente uma região (1:N). Siglas: `BR`, `N`, `NE`, `SE`, `S`,
`CO` e as 27 UFs. O `codigo_ibge` é o código real do IBGE, em texto: UFs `11` a `53`, regiões `1`
a `5` e Brasil `1`. Como Brasil e Norte têm o mesmo código, a unicidade em REGIOES é por (`tipo`,
`codigo_ibge`). A sigla sozinha também é ambígua entre níveis (`SE` = Sergipe ou Sudeste), por
isso a API identifica uma localidade pelo par (nível, código).

POPULACAO guarda as projeções do IBGE de 2012 a 2023 e as estimativas de 2024 e 2025 (ADR 0011) para estados, regiões e Brasil (33
localidades × 2 anos), as mesmas adotadas pelo FBSP, usadas no cálculo das taxas por 100 mil
habitantes.

## 3. Agregados: Brasil e regiões

A planilha publica o total do Brasil em todas as tabelas, mas os totais regionais só na série
histórica de MVI (T02). Os agregados publicados são importados como registros próprios
(`metodo = publicado`), e não somados. Para os demais indicadores, o total de cada região é
**calculado na importação** como a soma das UFs que a compõem (`metodo = soma_ufs`, ADR 0002), que
é o mesmo método do FBSP: na planilha, o Brasil é exatamente a soma das UFs em todas as colunas de
números absolutos, e as regiões da MVI, a soma das UFs de cada região.

- A soma é só geográfica (UF → região), só para números absolutos, dentro do mesmo indicador,
  recorte, unidade e ano; nunca entre um indicador e seus subtipos.
- Se alguma UF da região não informa o dado ("..."), o total regional fica não disponível, e não
  uma soma parcial.
- A taxa regional é calculada pela população da região (base 100 mil habitantes); nas demais bases
  não há denominador regional, e a taxa fica nula. Taxas nunca são somadas nem tiradas em média.
- Os agregados publicados servem de conferência: se divergirem da soma das UFs, a importação é
  interrompida.

Como há registros de UFs, de regiões e do Brasil, cada registro (e cada população) aponta para um
estado **ou** para uma região, e uma restrição de verificação garante que exatamente um dos dois
esteja preenchido.

## 4. Indicadores e hierarquia

Os tipos de crime formam uma hierarquia em INDICADORES, pela autorrelação `indicador_pai`, que
significa **"está contido em", nunca "é a soma de"**:

- MVI → homicídio doloso (→ homicídio de mulheres → feminicídio), latrocínio, lesão corporal
  seguida de morte, morte decorrente de intervenção policial;
- Roubo (total) → veículo, celular, transeunte, residência, estabelecimento comercial, instituição
  financeira, carga;
- Furto → veículo, celular. O Anuário não publica total de furtos: `furto` é um **agrupador sem
  registros**.

Os valores dos indicadores-pai são importados da planilha, e não somados a partir dos filhos: uma
mesma ocorrência pode ser contada em mais de um subtipo de roubo, e o total de roubo é menor que a
soma dos subtipos. `ordem` é a pré-ordem da hierarquia, usada para ordenar indicadores na API; os
18 indicadores, com slug, pai, unidade padrão e base, estão em `docs/importacao.md`, seção 2.

`base_taxa` é o denominador usado pelo FBSP, e `fonte_taxa`, a fonte desse denominador (ADR 0005):

| `base_taxa` | `fonte_taxa` | Indicadores |
| :--- | :--- | :--- |
| 100 mil habitantes | IBGE – Estimativas da população residente | a maioria |
| 100 mil mulheres | IBGE – Projeções da população | homicídio de mulheres, feminicídio |
| 100 mil veículos | Senatran – Frota de veículos | roubo e furto de veículo |
| 100 instituições | Banco Central do Brasil – Instituições financeiras | roubo a instituição financeira |

## 5. Unidade

O Anuário publica, para homicídio doloso, latrocínio e lesão corporal seguida de morte, o número de
**vítimas** e o de **ocorrências** (um fato pode ter mais de uma vítima). A unidade é atributo do
registro (`unidade`) e integra a chave única; INDICADORES guarda a `unidade_padrao`, usada quando
nenhuma é pedida (ADR 0004). A base da taxa vale para as duas unidades.

## 6. Recortes

As características de quem agiu, como a corporação e a situação do policial, são **recortes**. Um
recorte é formado por um ou mais pares de dimensão e valor, guardados em RECORTE_ITENS, o que
representa as combinações publicadas pelo Anuário, como "Polícia Militar, em serviço" nas mortes
decorrentes de intervenção policial (T08). Registros sem recorte são o total do indicador. A
`chave` (`dimensao=valor;…`, pares em ordem) torna a criação idempotente. Dimensões do escopo:
`corporacao` e `situacao_policial`. Perfis de vítimas (sexo, raça/cor, faixa etária) estão fora do
escopo (ADR 0004).

## 7. Taxa, variação e participação

O sistema **calcula** a taxa por 100 mil habitantes a partir de POPULACAO quando há população para
o ano e a localidade (2012 a 2025); nas outras bases, usa a taxa
publicada, guardada em `taxa_publicada` com 12 casas (ADR 0003). A variação percentual entre anos e
a participação de um indicador no seu indicador-pai (ou de um recorte no total do indicador), que
reproduz as proporções publicadas pelo FBSP (T09, T21), são **calculadas na consulta** e não são
armazenadas (`backend/apps/registros/queries.py`, ADR 0008).

## 8. Situação do dado e notas

A planilha usa dois sinais para dados ausentes: "-" (fenômeno inexistente) e "..." (informação não
disponível). No primeiro caso o valor é gravado como zero; no segundo, como nulo. Em ambos,
`situacao` registra a marcação original (`informado`, `inexistente` ou `nao_disponivel`), coerente
com o valor por restrição no banco. `observacao` guarda as notas metodológicas do FBSP associadas
ao dado, e `origem`, a célula da planilha de onde ele veio (ou as células somadas, em `soma_ufs`).

## 9. Entidades e atributos (Quadro 1)

Todas as tabelas têm `id` (chave primária). Valores, taxas e populações em `numeric` (RNF10).

| Entidade (tabela) | Atributos | Restrições |
| :--- | :--- | :--- |
| REGIOES (`localidades_regiao`) | `sigla` (2), `nome`, `tipo` (`regiao` \| `pais`), `codigo_ibge` (2) | `sigla` única; (`tipo`, `codigo_ibge`) único |
| ESTADOS (`localidades_estado`) | `sigla` (2), `nome`, `codigo_ibge` (2), `regiao_id` | `sigla` e `codigo_ibge` únicos |
| POPULACAO (`localidades_populacao`) | `estado_id` (nulo), `regiao_id` (nulo), `fonte_id`, `ano`, `valor` `numeric(12,0)` | exatamente um entre estado e região; (estado, região, ano) único `NULLS NOT DISTINCT` |
| FONTES (`catalogo_fonte`) | `slug`, `nome`, `descricao`, `url` | `slug` único; ids fixos 1 a 5 (ADR 0005) |
| INDICADORES (`catalogo_indicador`) | `slug`, `nome`, `descricao`, `unidade_padrao`, `base_taxa` (nulo), `fonte_taxa_id` (nulo), `indicador_pai_id` (nulo), `ordem` | `slug` e `ordem` únicos; `base_taxa` e `fonte_taxa_id` ambos nulos ou ambos preenchidos |
| RECORTES (`catalogo_recorte`) | `chave`, `rotulo` | `chave` única |
| RECORTE_ITENS (`catalogo_recorteitem`) | `recorte_id`, `dimensao` (`corporacao` \| `situacao_policial`), `valor` | (recorte, dimensão) único |
| REGISTROS_ANUAIS (`registros_registroanual`) | `estado_id` (nulo), `regiao_id` (nulo), `indicador_id`, `recorte_id` (nulo), `fonte_id`, `ano`, `unidade` (`vitimas` \| `ocorrencias`), `valor` `numeric(18,4)` (nulo), `taxa_publicada` `numeric(24,12)` (nulo), `situacao`, `metodo` (`publicado` \| `soma_ufs`), `origem` (200), `observacao` (nulo) | exatamente um entre estado e região; (estado, região, indicador, recorte, unidade, ano) único `NULLS NOT DISTINCT`; valor coerente com a situação; `soma_ufs` sem `taxa_publicada` |
| CARGAS (`importacao_carga`) | `versao` (12), `arquivos` (nome e SHA-256 de cada arquivo), `iniciada_em`, `concluida_em` (nulo), `status` (`em_andamento` \| `concluida` \| `falhou`), `total_registros` (nulo) | — |

Relações: cada registro se relaciona a exatamente um indicador e uma fonte, a um estado ou a uma
região e, opcionalmente, a um recorte; cada uma dessas entidades pode se relacionar a vários
registros (1:N). As chaves estrangeiras usam `PROTECT`, menos RECORTE_ITENS → RECORTES
(`CASCADE`).

Como várias colunas da chave única aceitam nulo, ela é declarada com `NULLS NOT DISTINCT`
(PostgreSQL 18); é isso que torna a importação idempotente (upsert sem duplicar totais nem
regiões). Um índice funcional com `COALESCE` nas colunas anuláveis atende às subconsultas de
variação e participação (ADR 0008).

## 10. Volume da carga atual

| Entidade | Linhas |
| :--- | ---: |
| REGISTROS_ANUAIS | 3.498 (3.038 lidos + 460 regionais calculados, 59 deles não disponíveis) |
| POPULACAO | 462 |
| INDICADORES | 18 |
| REGIOES + ESTADOS | 6 + 27 |
| FONTES | 5 |
| RECORTES | 4 |

Essa estrutura permite consultas como a evolução de um indicador em um estado ao longo dos anos, a
comparação entre UFs em um mesmo ano ou a distribuição das mortes por intervenção policial entre
corporações.

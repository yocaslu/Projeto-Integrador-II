# Modelagem de dados

Nove entidades: REGIOES, ESTADOS, POPULACAO, FONTES, INDICADORES, RECORTES, RECORTE_ITENS,
REGISTROS_ANUAIS (tabela de fatos) e CARGAS (sem relacionamento; versão da carga). A descrição
completa, com atributos, restrições e decisões, está em [`../modelagem.md`](../modelagem.md).

Diagrama entidade-relacionamento (Figura 3 do roteiro):

- `modelo-er.dot`: fonte editável (Graphviz);
- `modelo-er.png` e `modelo-er.svg`: imagens geradas.

Para regenerar as imagens depois de editar o `.dot`:

```bash
dot -Tpng -Gdpi=200 modelo-er.dot -o modelo-er.png && dot -Tsvg modelo-er.dot -o modelo-er.svg
```

O diagrama já inclui os ajustes 1 a 13 ao modelo do roteiro listados no CLAUDE.md (ADRs 0002 a
0005): `slug`, `ordem`, `unidade_padrao` e `fonte_taxa` em INDICADORES; `codigo_ibge` em REGIOES e
ESTADOS; `chave` em RECORTES; `slug` em FONTES; `unidade`, `origem` e `metodo` em REGISTROS_ANUAIS,
com `unidade` na chave única; CHECK e unicidade em POPULACAO; e a entidade CARGAS. Onde o roteiro
diverge do diagrama ou de `docs/modelagem.md`, valem estes.

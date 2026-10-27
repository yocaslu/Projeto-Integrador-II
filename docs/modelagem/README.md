# Modelagem de dados

Oito entidades: REGIOES, ESTADOS, POPULACAO, FONTES, INDICADORES, RECORTES, RECORTE_ITENS e
REGISTROS_ANUAIS (tabela de fatos). A descrição completa está na seção "Modelagem de dados" do
roteiro.

Diagrama entidade-relacionamento (Figura 3 do roteiro):

- `modelo-er.dot`: fonte editável (Graphviz);
- `modelo-er.png` e `modelo-er.svg`: imagens geradas.

Para regenerar as imagens depois de editar o `.dot`:

```bash
dot -Tpng -Gdpi=200 modelo-er.dot -o modelo-er.png && dot -Tsvg modelo-er.dot -o modelo-er.svg
```

O diagrama segue o roteiro. Os ajustes decididos depois (slug, codigo_ibge, chave do recorte,
origem e a entidade CARGAS, listados no CLAUDE.md) entram aqui quando forem registrados em ADR.

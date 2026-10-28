# Fixtures

Planilhas reduzidas usadas nos testes de importação. Os testes não dependem dos arquivos completos
de `dados/brutos/` (a planilha real só é importada pelos testes `planilha_real`).

- `planilhas/brutos/`: `anuario-reduzido.xlsx` (abas T01, T02, T03, T08, T09, T15 e T21, com todas
  as linhas, porque a agregação regional exige todas as UFs de cada região) e as estimativas do
  IBGE só com a aba `BRASIL_E_UFs`.
- `planilhas/README.md`: manifesto com o SHA-256 de cada arquivo, no formato de `dados/README.md`.

Para gerar de novo (só quando a planilha original mudar), dentro de `backend/`:

```bash
uv run python tests/fixtures/gerar_planilhas.py
```

Os testes que alteram uma célula de propósito trabalham numa cópia temporária (fixture
`planilhas` do `tests/conftest.py`), que também regrava o manifesto.

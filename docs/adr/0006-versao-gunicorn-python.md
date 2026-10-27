# 0006. Gunicorn 26.2.0 e Python fixado na série 3.14

- Data: 2026-10-27
- Situação: aceita

## Contexto

A stack fixada no CLAUDE.md e no `backend/pyproject.toml` pedia `gunicorn==26.2.2`. Essa versão
nunca foi publicada: no PyPI, a série 26 tem 26.0.0 (05/05/2026), 26.1.0 (18/08/2026) e 26.2.0
(24/08/2026), a mais recente. Por isso, `uv lock` não conseguia resolver as dependências e o
`backend/uv.lock`, exigido pelo Dockerfile e pelo CI (`--locked`), não podia ser gerado.

A regra 29 do CLAUDE.md exige ADR para mudar versão da stack.

Na mesma linha, o CLAUDE.md dizia "Python 3.14.9", mas `backend/.python-version` (`3.14`), a imagem
Docker (`python:3.14-slim`) e o `requires-python` (`>=3.14`) aceitam qualquer versão da série 3.14.
O documento e a configuração não diziam a mesma coisa.

## Decisão

1. **Gunicorn 26.2.0** (`gunicorn==26.2.0`), a versão publicada mais recente. A equipe testou essa
   versão com a aplicação no Python 3.14, gerando o `uv.lock` e subindo o backend. O PyPI não lista
   classificador de Python 3.14 para o Gunicorn (vai até 3.13; `Requires-Python >=3.10`), então
   esse teste é a evidência de compatibilidade.
2. **Python fixado só na série 3.14**: qualquer versão de correção 3.14.x é aceita. O
   `.python-version` (`3.14`), a imagem `python:3.14-slim` e o `requires-python` continuam como
   estão; o CLAUDE.md passa a dizer "Python 3.14" em vez de "3.14.9".

## Consequências

- O `uv.lock` pode ser gerado e versionado, e o Dockerfile e o CI voltam a funcionar com
  `--locked`.
- Versões de correção do Python entram sem ADR: a imagem `python:3.14-slim` e o runner do CI
  atualizam sozinhos dentro da série. Em troca, o ambiente local, o CI e a produção podem rodar
  correções diferentes da 3.14. Mudar de série (3.15) continua exigindo ADR.
- Quando o Gunicorn publicar uma versão com suporte declarado a Python 3.14, vale atualizar, com
  novo ADR.
- O Roteiro (seção Ferramentas) passa a citar Gunicorn 26.2.0.

FROM ghcr.io/astral-sh/uv:0.13.5 AS uv

# Base comum: Python, uv e dependências de produção
FROM python:3.14-slim AS base
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Desenvolvimento: inclui ferramentas de teste e lint; o código é montado como volume
FROM base AS dev
RUN uv sync --locked --no-install-project
COPY . .

# Produção: Gunicorn atrás do Traefik
FROM base AS prod
COPY . .
ENV DJANGO_SETTINGS_MODULE=config.settings.prod
RUN DJANGO_SECRET_KEY=build uv run --no-dev python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

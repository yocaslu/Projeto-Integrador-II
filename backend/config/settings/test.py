"""Configurações usadas pelo pytest e pelo CI.

Os testes rodam no PostgreSQL, e não no SQLite, porque o modelo usa recursos próprios do
PostgreSQL 18, como restrições de unicidade com NULLS NOT DISTINCT.
"""

from .base import *  # noqa: F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

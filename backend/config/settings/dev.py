"""Configurações do ambiente de desenvolvimento."""

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK

DEBUG = True

# A API navegável do DRF facilita a exploração durante o desenvolvimento.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

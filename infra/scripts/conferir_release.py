#!/usr/bin/env python3
"""Confere se a tag de release é igual às versões do projeto e informa a versão da carga.

Uso: python3 infra/scripts/conferir_release.py v1.2.3

Com tudo igual, escreve `carga=<versao>` na saída, no formato de $GITHUB_OUTPUT. A carga é calculada
como em apps/importacao/processo.py (ler_manifesto e versao_da_carga), mas este script roda sem as
dependências do backend. Divergência termina com erro e não publica nada.
"""

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TAG = re.compile(r"^v(\d+\.\d+\.\d+)$")
LINHA_DO_MANIFESTO = re.compile(r"^\|\s*`([^`]+)`\s*\|.*\|\s*`([0-9a-f]{64})`\s*\|\s*$")
PROJETO_BACKEND = "anuario-backend"


def versoes_do_projeto(raiz: Path) -> dict[str, str]:
    pacote = json.loads((raiz / "frontend/package.json").read_text(encoding="utf-8"))
    trava = json.loads((raiz / "frontend/package-lock.json").read_text(encoding="utf-8"))
    pyproject = tomllib.loads((raiz / "backend/pyproject.toml").read_text(encoding="utf-8"))
    uv = tomllib.loads((raiz / "backend/uv.lock").read_text(encoding="utf-8"))
    return {
        "frontend/package.json": pacote["version"],
        "frontend/package-lock.json": trava["packages"][""]["version"],
        "backend/pyproject.toml": pyproject["project"]["version"],
        "backend/uv.lock": next(p["version"] for p in uv["package"] if p["name"] == PROJETO_BACKEND),
    }


def versao_da_carga(manifesto: Path) -> str:
    hashes = {}
    for linha in manifesto.read_text(encoding="utf-8").splitlines():
        casou = LINHA_DO_MANIFESTO.match(linha.strip())
        if casou:
            hashes[casou.group(1)] = casou.group(2)
    if not hashes:
        raise ValueError(f"Nenhum hash de arquivo encontrado em {manifesto}")
    concatenados = "".join(hashes[nome] for nome in sorted(hashes))
    return hashlib.sha256(concatenados.encode()).hexdigest()[:12]


def main(argumentos: list[str]) -> int:
    casou = TAG.match(argumentos[0]) if len(argumentos) == 1 else None
    if not casou:
        print("Informe uma tag no formato vX.Y.Z.", file=sys.stderr)
        return 1
    esperada = casou.group(1)
    divergentes = {
        arquivo: versao
        for arquivo, versao in versoes_do_projeto(RAIZ).items()
        if versao != esperada
    }
    if divergentes:
        print(f"A tag pede a versão {esperada}, mas:", file=sys.stderr)
        for arquivo, versao in divergentes.items():
            print(f"- {arquivo} está em {versao}", file=sys.stderr)
        return 1
    print(f"carga={versao_da_carga(RAIZ / 'dados/README.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

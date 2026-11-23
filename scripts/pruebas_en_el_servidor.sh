#!/usr/bin/env bash
#
# Corre la batería de Python dentro del servidor, contra la base de
# pruebas · F17-T05
#
#     cd /opt/epic-wallet && ./scripts/pruebas_en_el_servidor.sh
#     ./scripts/pruebas_en_el_servidor.sh tests/api/test_aislamiento_f17.py -v
#
# Por qué hace falta un script y no alcanza `pytest`:
#
# 1. La imagen de la api NO lleva las pruebas adentro (`api/Dockerfile`
#    copia `api/` y `migrations/`, nada más) y tampoco lleva `pytest`.
#    Así tiene que ser: lo que corre en producción no necesita ni una
#    de las dos cosas.
# 2. El repositorio no se puede montar tal cual. El `.env` del
#    servidor es 0600 de root y el contenedor corre como `epic`:
#    `core/config.py` intenta leerlo y muere con «permission denied».
#    Por eso se monta una copia **sin** el `.env`.
# 3. La copia sin `.env` tiene además la ventaja que importa: desde
#    adentro de esa corrida no hay forma de alcanzar la base real,
#    aunque alguien se equivoque. La única URL que entra es la de
#    pruebas, y se arma acá.
#
# `test_el_env_con_los_secretos_no_esta_rastreado` falla siempre acá:
# corre `git ls-files` y la imagen no tiene git. En la máquina de
# desarrollo pasa. Es el único rojo esperado.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COPIA="/tmp/epic-wallet-pruebas"

cd "$RAIZ"

if [[ ! -f .env ]]; then
  echo "ERROR: no hay .env en $RAIZ. Esto se corre en el servidor." >&2
  exit 1
fi

# La base de pruebas: la misma URL de la real con el nombre cambiado.
# Si no existiera, `entorno.py` se niega a correr por el nombre.
URL_REAL="$(grep '^DATABASE_URL=' .env | cut -d= -f2-)"
URL_PRUEBAS="${URL_REAL%/*}/epic_wallet_test"

if [[ "$URL_PRUEBAS" == "$URL_REAL" ]]; then
  echo "ERROR: la URL de pruebas quedó igual a la real. No se corre." >&2
  exit 1
fi

# La copia se borra pase lo que pase: con `set -e`, un rojo en las
# pruebas cortaría el script y la dejaría ahí tirada.
trap 'rm -rf "$COPIA"' EXIT

rm -rf "$COPIA"
mkdir -p "$COPIA"
tar -c --exclude=.env --exclude=.git --exclude=node_modules \
    --exclude=respaldos --exclude=.venv . | tar -x -C "$COPIA"

docker compose run --rm -T \
  -v "$COPIA:/repo" -w /repo \
  -e TEST_DATABASE_URL="$URL_PRUEBAS" \
  -e APP_ENV=development \
  api sh -c '
    pip install -q "pytest>=8.3,<9.0" "pytest-asyncio>=0.24,<1.0" >/dev/null 2>&1
    python -m pytest -p no:cacheprovider -o addopts="--strict-markers --strict-config" "$@"
  ' sh "$@"

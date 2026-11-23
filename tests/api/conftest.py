"""Prepara el entorno de las pruebas de API · F16-T03.

Esto corre **antes** de que se importe cualquier módulo de prueba, y
por lo tanto antes de que se importe la aplicación. Importa, porque
`api/app/core/config.py` lee el entorno una sola vez al importarse y
`core/db.py` construye el motor con lo que haya en ese momento: si las
variables se pusieran más tarde, la aplicación ya estaría apuntando a
otra base.

Dos cosas se fijan acá:

1. `DATABASE_URL` pasa a ser `TEST_DATABASE_URL`, así la aplicación
   bajo prueba habla con la base de pruebas y no con la de trabajo.
2. `JWT_PUBLIC_KEY` pasa a ser la pública de la batería, así la
   aplicación verifica los tokens que estas pruebas firman.

También se vacían las variables del proveedor anterior. No es
cosmético: es lo que garantiza que ninguna prueba pueda alcanzarlo
aunque alguien las deje puestas en su `.env`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

from tests.api import entorno  # noqa: E402

if entorno.URL_BASE:
    os.environ["DATABASE_URL"] = entorno.URL_BASE
os.environ["DB_SCHEMA"] = entorno.ESQUEMA
os.environ["JWT_PUBLIC_KEY"] = entorno.CLAVE_PUBLICA
os.environ["JWT_PRIVATE_KEY"] = ""
# Que no quede ninguna puerta abierta hacia afuera.
for variable in (
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_JWT_SECRET",
):
    os.environ[variable] = ""


@pytest.fixture(scope="session")
def esquema_de_pruebas() -> None:
    """Deja la base de pruebas con el esquema al día.

    Corre `alembic upgrade head` una vez por sesión. Es idempotente: si
    ya está en la última revisión, no hace nada. Así `pytest` funciona
    contra una base recién creada y vacía, sin pasos manuales.
    """
    if not entorno.URL_BASE:
        pytest.skip("sin TEST_DATABASE_URL")
    entorno.comprobar_que_no_es_real(entorno.URL_BASE)

    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=RAIZ,
        env={
            **os.environ,
            "DATABASE_URL": entorno.URL_BASE,
            "DB_SCHEMA": entorno.ESQUEMA,
            # `migrations/env.py` lo exige explícito. Acá es una base de
            # pruebas, pero el valor que habilita migrar es este.
            "APP_ENV": "production",
        },
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        pytest.fail(
            "no se pudo preparar la base de pruebas con alembic:\n"
            f"{resultado.stdout}\n{resultado.stderr}"
        )


@pytest.fixture(scope="module")
def motor(esquema_de_pruebas: None):
    """Motor contra la base de pruebas, con el esquema ya al día."""
    assert entorno.URL_BASE
    return entorno.motor_de_pruebas(entorno.URL_BASE)


@pytest.fixture(scope="module")
def cliente():
    """La aplicación de verdad, en proceso."""
    from api.app.main import app
    from fastapi.testclient import TestClient

    return TestClient(app, raise_server_exceptions=False)

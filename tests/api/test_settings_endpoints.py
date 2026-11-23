"""`GET` y `PUT /api/settings` · F11-T01.

Se prueba contra la API real, con cuentas reales de Supabase — mismo
criterio que `test_investments_endpoints.py`.

Los criterios de aceptación, cada uno con su prueba: sin preferencia
guardada `theme` es `null`; guardarla la devuelve `GET`; guardar
`null` la borra; un valor fuera de "light"/"dark" da 422; el
aislamiento entre cuentas (RLS).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import text

from tests.api.ayudas_db import escritura
from tests.api.entorno import (
    ESQUEMA,
    Cuenta,
    crear_cuenta,
    sin_entorno,
)


def _crear_cuenta() -> Cuenta:
    """Una cuenta descartable nueva, con su token."""
    return crear_cuenta()


pytestmark = pytest.mark.api


@pytest.fixture(scope="module")
def cuentas(motor) -> Iterator[tuple[Cuenta, Cuenta]]:
    a = _crear_cuenta()
    b = _crear_cuenta()
    yield a, b
    with escritura(motor) as con:
        con.execute(text("delete from auth.users where id = any(:ids)"), {"ids": [a.uid, b.uid]})


@pytest.fixture
def limpiar(motor, cuentas):
    a, b = cuentas

    def _limpiar() -> None:
        with escritura(motor) as con:
            con.execute(
                text(f'delete from "{ESQUEMA}".app_settings where user_id = any(:ids)'),
                {"ids": [a.uid, b.uid]},
            )

    _limpiar()
    yield
    _limpiar()


# ===================================================================
#  GET /api/settings
# ===================================================================


@sin_entorno
def test_sin_token_devuelve_401(cliente) -> None:
    assert cliente.get("/api/settings").status_code == 401


@sin_entorno
def test_sin_preferencia_guardada_theme_es_null(
    cliente, cuentas: tuple[Cuenta, Cuenta], limpiar
) -> None:
    a, _ = cuentas
    r = cliente.get("/api/settings", headers=a.cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["theme"] is None


# ===================================================================
#  PUT /api/settings
# ===================================================================


@sin_entorno
def test_guardar_el_tema_y_volver_a_leerlo(
    cliente, cuentas: tuple[Cuenta, Cuenta], limpiar
) -> None:
    a, _ = cuentas
    r = cliente.put("/api/settings", json={"theme": "dark"}, headers=a.cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["theme"] == "dark"

    r = cliente.get("/api/settings", headers=a.cabeceras)
    assert r.json()["theme"] == "dark"

    # Guardar de nuevo no duplica la fila (unique user_id, key): pisa.
    r = cliente.put("/api/settings", json={"theme": "light"}, headers=a.cabeceras)
    assert r.json()["theme"] == "light"


@sin_entorno
def test_guardar_null_borra_la_preferencia(
    cliente, cuentas: tuple[Cuenta, Cuenta], limpiar
) -> None:
    a, _ = cuentas
    cliente.put("/api/settings", json={"theme": "dark"}, headers=a.cabeceras)

    r = cliente.put("/api/settings", json={"theme": None}, headers=a.cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["theme"] is None

    assert cliente.get("/api/settings", headers=a.cabeceras).json()["theme"] is None


@sin_entorno
def test_un_valor_fuera_de_la_lista_da_422(
    cliente, cuentas: tuple[Cuenta, Cuenta], limpiar
) -> None:
    a, _ = cuentas
    r = cliente.put("/api/settings", json={"theme": "azul"}, headers=a.cabeceras)
    assert r.status_code == 422, r.text


@sin_entorno
def test_un_campo_desconocido_da_422(cliente, cuentas: tuple[Cuenta, Cuenta], limpiar) -> None:
    a, _ = cuentas
    r = cliente.put(
        "/api/settings", json={"theme": "dark", "numero_formato": "abreviado"}, headers=a.cabeceras
    )
    assert r.status_code == 422, r.text


# ===================================================================
#  Aislamiento entre cuentas (RLS)
# ===================================================================


@sin_entorno
def test_una_cuenta_no_ve_la_preferencia_de_otra(
    cliente, cuentas: tuple[Cuenta, Cuenta], limpiar
) -> None:
    a, b = cuentas
    cliente.put("/api/settings", json={"theme": "dark"}, headers=a.cabeceras)

    r = cliente.get("/api/settings", headers=b.cabeceras)
    assert r.status_code == 200
    assert r.json()["theme"] is None

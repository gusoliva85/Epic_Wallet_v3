"""`GET /api/patrimony` · F09-T03.

Se prueba contra la API real, con `TestClient` y cuentas reales de la
base de pruebas — mismo criterio que `test_dashboard_endpoint.py`.

Los tres criterios de aceptación de la tarea, cada uno con su prueba:
el endpoint devuelve la composición y el total
(`test_la_composicion_y_el_total_reflejan_el_ahorro_acumulado`), sin
pasivos cargados no falla (`test_una_cuenta_nueva_sin_pasivos_no_falla`,
que además es el caso real de toda cuenta nueva: la tabla existe pero
nadie carga nada ahí) y, aparte de la lista, el `downgrade` de la
migración se probó a mano (`migrations/versions/..._f09_t03_pasivos.py`,
aplicar → bajar → volver a aplicar sobre la base real sin error).

Un pasivo con filas de verdad no tiene endpoint propio en el MVP
(Técnico §6.2: "se crea vacía y no se muestra en la interfaz"), así
que se inserta directo por SQL — mismo patrón que
`test_dashboard_endpoint.py::test_un_mes_historico_no_tiene_diario`
para simular un histórico sin el endpoint que todavía no existía.
"""

from __future__ import annotations

import decimal
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
    """Antes y después de cada prueba: sin meses ni pasivos de ninguna
    de las dos cuentas (por cascada, tampoco movimientos ni totales)."""
    a, b = cuentas

    def _limpiar() -> None:
        with escritura(motor) as con:
            con.execute(
                text(f'delete from "{ESQUEMA}".months where user_id = any(:ids)'),
                {"ids": [a.uid, b.uid]},
            )
            con.execute(
                text(f'delete from "{ESQUEMA}".liabilities where user_id = any(:ids)'),
                {"ids": [a.uid, b.uid]},
            )
            con.execute(
                text(f'delete from "{ESQUEMA}".investments where user_id = any(:ids)'),
                {"ids": [a.uid, b.uid]},
            )

    _limpiar()
    yield
    _limpiar()


def _categoria_id(cliente, cuenta: Cuenta, nombre: str, tipo: str) -> int:
    r = cliente.get("/api/categories", params={"type": tipo}, headers=cuenta.cabeceras)
    for c in r.json():
        if c["name"] == nombre:
            return int(c["id"])
    pytest.fail(f"no se encontró la categoría {nombre!r} de tipo {tipo!r}")


def _cargar(
    cliente, cuenta: Cuenta, *, category_id: int, tipo: str, importe: str, fecha: str
) -> None:
    r = cliente.post(
        "/api/transactions",
        json={
            "category_id": category_id,
            "transaction_date": fecha,
            "transaction_type": tipo,
            "amount": importe,
        },
        headers=cuenta.cabeceras,
    )
    assert r.status_code == 201, r.text


# ===================================================================


@sin_entorno
def test_sin_token_devuelve_401(cliente) -> None:
    assert cliente.get("/api/patrimony").status_code == 401


@sin_entorno
def test_una_cuenta_nueva_sin_pasivos_no_falla(
    cliente, cuentas: tuple[Cuenta, Cuenta], limpiar
) -> None:
    # Criterio de aceptación: la tabla `liabilities` existe pero nadie
    # cargó nada ahí (el caso real de toda cuenta en el MVP).
    a, _ = cuentas
    r = cliente.get("/api/patrimony", headers=a.cabeceras)
    assert r.status_code == 200, r.text
    cuerpo = r.json()

    assert cuerpo["savings_balance"] == "0.00"
    assert cuerpo["investments_value"] == "0.00"
    assert cuerpo["liabilities_total"] == "0.00"
    assert cuerpo["net_worth"] == "0.00"
    # Sin nada que repartir (ahorro + inversiones = 0), ningún
    # porcentaje inventado — mismo criterio que la tasa de ahorro.
    assert cuerpo["composition"] == {"savings_share": None, "investments_share": None}


@sin_entorno
def test_la_composicion_y_el_total_reflejan_el_ahorro_acumulado(
    cliente, cuentas: tuple[Cuenta, Cuenta], limpiar
) -> None:
    a, _ = cuentas
    sueldo = _categoria_id(cliente, a, "Sueldo", "income")
    alquiler = _categoria_id(cliente, a, "Alquiler", "expense")

    hoy = cliente.get("/api/dashboard", headers=a.cabeceras).json()["month"]
    anio, mes_num = hoy["year"], hoy["month"]

    _cargar(
        cliente,
        a,
        category_id=sueldo,
        tipo="income",
        importe="500000.00",
        fecha=f"{anio:04d}-{mes_num:02d}-01",
    )
    _cargar(
        cliente,
        a,
        category_id=alquiler,
        tipo="expense",
        importe="150000.00",
        fecha=f"{anio:04d}-{mes_num:02d}-05",
    )

    r = cliente.get("/api/patrimony", headers=a.cabeceras)
    assert r.status_code == 200, r.text
    cuerpo = r.json()

    assert cuerpo["savings_balance"] == "350000.00"
    assert cuerpo["net_worth"] == "350000.00"  # sin inversiones ni pasivos todavía
    # Sin inversiones, el 100% de la composición es ahorro.
    assert cuerpo["composition"] == {"savings_share": "100.0", "investments_share": "0.0"}


@sin_entorno
def test_un_pasivo_cargado_se_resta_del_total_pero_no_de_la_composicion(
    cliente, motor, cuentas: tuple[Cuenta, Cuenta], limpiar
) -> None:
    # Sin pantalla propia (Técnico §6.2), se inserta directo: lo mismo
    # que ya hace `test_dashboard_endpoint.py` para un mes histórico
    # antes de que existiera su endpoint.
    a, _ = cuentas
    sueldo = _categoria_id(cliente, a, "Sueldo", "income")
    hoy = cliente.get("/api/dashboard", headers=a.cabeceras).json()["month"]
    _cargar(
        cliente,
        a,
        category_id=sueldo,
        tipo="income",
        importe="500000.00",
        fecha=f"{hoy['year']:04d}-{hoy['month']:02d}-01",
    )

    with escritura(motor) as con:
        con.execute(
            text(
                f'insert into "{ESQUEMA}".liabilities (user_id, name, amount) values (:uid, :nombre, :monto)'
            ),
            {"uid": a.uid, "nombre": "Préstamo de prueba", "monto": decimal.Decimal("120000.00")},
        )

    cuerpo = cliente.get("/api/patrimony", headers=a.cabeceras).json()
    assert cuerpo["savings_balance"] == "500000.00"
    assert cuerpo["liabilities_total"] == "120000.00"
    assert cuerpo["net_worth"] == "380000.00"  # 500000 - 120000
    # La barra de composición sigue siendo 100% ahorro: el pasivo no es
    # una porción que se dibuje, ya se restó del total (Técnico §14.2).
    assert cuerpo["composition"] == {"savings_share": "100.0", "investments_share": "0.0"}


@sin_entorno
def test_una_posicion_de_cartera_entra_en_inversiones_y_en_la_composicion(
    cliente, motor, cuentas: tuple[Cuenta, Cuenta], limpiar
) -> None:
    # F10-T04: sin endpoint propio todavía, se inserta directo —mismo
    # criterio que los pasivos, arriba.
    a, _ = cuentas
    sueldo = _categoria_id(cliente, a, "Sueldo", "income")
    hoy = cliente.get("/api/dashboard", headers=a.cabeceras).json()["month"]
    _cargar(
        cliente,
        a,
        category_id=sueldo,
        tipo="income",
        importe="300000.00",
        fecha=f"{hoy['year']:04d}-{hoy['month']:02d}-01",
    )

    with escritura(motor) as con:
        con.execute(
            text(
                f'insert into "{ESQUEMA}".investments '
                "(user_id, symbol, name, investment_type, nominal_quantity, initial_value, "
                "current_value) "
                "values (:uid, 'CEDEAR-TEST', 'Cedear de prueba', 'cedear', 0, :valor, :valor)"
            ),
            {"uid": a.uid, "valor": decimal.Decimal("100000.00")},
        )

    cuerpo = cliente.get("/api/patrimony", headers=a.cabeceras).json()
    assert cuerpo["savings_balance"] == "300000.00"
    assert cuerpo["investments_value"] == "100000.00"
    assert cuerpo["net_worth"] == "400000.00"  # 300000 + 100000
    # 300000/(300000+100000) = 75%, 100000/(300000+100000) = 25%.
    assert cuerpo["composition"] == {"savings_share": "75.0", "investments_share": "25.0"}


@sin_entorno
def test_una_cuenta_no_ve_el_patrimonio_de_otra(
    cliente, motor, cuentas: tuple[Cuenta, Cuenta], limpiar
) -> None:
    a, b = cuentas
    sueldo = _categoria_id(cliente, a, "Sueldo", "income")
    hoy = cliente.get("/api/dashboard", headers=a.cabeceras).json()["month"]
    _cargar(
        cliente,
        a,
        category_id=sueldo,
        tipo="income",
        importe="999999.00",
        fecha=f"{hoy['year']:04d}-{hoy['month']:02d}-01",
    )
    with escritura(motor) as con:
        con.execute(
            text(
                f'insert into "{ESQUEMA}".liabilities (user_id, name, amount) values (:uid, :nombre, :monto)'
            ),
            {"uid": a.uid, "nombre": "Pasivo de la cuenta A", "monto": decimal.Decimal("50000.00")},
        )

    r = cliente.get("/api/patrimony", headers=b.cabeceras)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["savings_balance"] == "0.00"
    assert cuerpo["liabilities_total"] == "0.00"

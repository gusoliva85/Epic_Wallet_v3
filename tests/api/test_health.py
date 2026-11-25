"""Pruebas del endpoint de salud y del formato de errores.

Corresponde a la tarea F00-T07. Usa `httpx.ASGITransport` en lugar de
`TestClient` para hablar con la aplicación en memoria: es lo que pide
§19 del documento técnico y evita el aviso de deprecación de Starlette.

La conexión a la base se simula: estas pruebas no necesitan red.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.main import app


def _cliente() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )


# ==================================================================
#  Salud
# ==================================================================
@pytest.mark.api
async def test_salud_responde_con_la_base_viva(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers import health as modulo

    monkeypatch.setattr(
        modulo,
        "revisar_conexion",
        lambda: {"status": "connected", "latency_ms": 31.4, "schema_exists": True},
    )
    async with _cliente() as c:
        r = await c.get("/api/health")

    assert r.status_code == 200
    cuerpo: dict[str, Any] = r.json()
    assert cuerpo["status"] == "ok"
    assert cuerpo["database"]["status"] == "connected"
    # Lo que pide F00-T09: saber contra qué esquema corre cada entorno.
    assert "db_schema" in cuerpo
    assert cuerpo["environment"] in {"development", "preview", "production"}
    assert cuerpo["version"]


@pytest.mark.api
async def test_salud_no_se_cae_si_la_base_no_responde(monkeypatch: pytest.MonkeyPatch) -> None:
    """El endpoint que sirve para enterarse de que la base falló no puede fallar."""
    from app.routers import health as modulo

    monkeypatch.setattr(
        modulo,
        "revisar_conexion",
        lambda: {"status": "error", "latency_ms": 10000.0, "reason": "OperationalError"},
    )
    async with _cliente() as c:
        r = await c.get("/api/health")

    assert r.status_code == 503, "una base caída es servicio degradado"
    cuerpo = r.json()
    assert cuerpo["status"] == "degraded"
    assert cuerpo["database"]["status"] == "error"
    assert cuerpo["database"]["reason"] == "OperationalError"


@pytest.mark.api
async def test_salud_avisa_si_falta_el_esquema(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin el esquema, las migraciones no corrieron: hay que saberlo."""
    from app.routers import health as modulo

    monkeypatch.setattr(
        modulo,
        "revisar_conexion",
        lambda: {"status": "connected", "latency_ms": 30.0, "schema_exists": False},
    )
    async with _cliente() as c:
        r = await c.get("/api/health")

    assert r.status_code == 503
    assert r.json()["status"] == "degraded"
    assert any("migraciones" in a for a in r.json()["warnings"])


@pytest.mark.api
async def test_la_salud_no_filtra_secretos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ni claves ni la cadena de conexión pueden salir en la respuesta."""
    from app.core.config import settings
    from app.routers import health as modulo

    monkeypatch.setattr(
        modulo,
        "revisar_conexion",
        lambda: {"status": "connected", "latency_ms": 30.0, "schema_exists": True},
    )
    async with _cliente() as c:
        r = await c.get("/api/health")

    texto = r.text
    for secreto in (
        settings.JWT_PRIVATE_KEY,
        settings.DATABASE_URL,
    ):
        if secreto:
            assert secreto not in texto, "la respuesta de salud no debe traer secretos"


# ==================================================================
#  El aviso de respaldo atrasado · F18-T06
# ==================================================================
#
# Lo que se prueba acá es **que el aviso salte**, que es lo único que
# importa de una alarma. La aritmética de las horas ya la cubren las
# 18 pruebas de `tests/unit/test_respaldos.py`; esto comprueba que el
# endpoint la use y que el aviso llegue a `warnings`, que es de donde
# lo lee todo lo demás.
#
# Esperar a que el respaldo falle de verdad para ver si avisa no es una
# prueba: es enterarse tarde.


def _con_base_viva(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers import health as modulo

    monkeypatch.setattr(
        modulo,
        "revisar_conexion",
        lambda: {"status": "connected", "latency_ms": 10.0, "schema_exists": True},
    )


def _con_constancia(monkeypatch: pytest.MonkeyPatch, constancia: dict[str, Any] | None) -> None:
    from app.routers import health as modulo

    monkeypatch.setattr(modulo, "leer_constancia", lambda: constancia)


def _hace(horas: float) -> str:
    from datetime import UTC, datetime, timedelta

    return (datetime.now(UTC) - timedelta(hours=horas)).isoformat()


@pytest.mark.api
async def test_con_el_respaldo_al_dia_no_avisa(monkeypatch: pytest.MonkeyPatch) -> None:
    _con_base_viva(monkeypatch)
    _con_constancia(monkeypatch, {"verificado": True, "fecha": _hace(2)})

    async with _cliente() as c:
        r = await c.get("/api/health")

    datos = r.json()
    assert datos["last_backup"]["up_to_date"] is True
    assert datos["last_backup"]["hours_ago"] == pytest.approx(2, abs=0.2)
    assert not [a for a in datos["warnings"] if "RESPALDO" in a]


@pytest.mark.api
@pytest.mark.parametrize(
    ("caso", "constancia"),
    [
        ("sin constancia", None),
        ("de tres días", {"verificado": True, "fecha": _hace(72)}),
        ("fresca pero sin verificar", {"verificado": False, "fecha": _hace(1)}),
        ("sin fecha", {"verificado": True}),
        ("con fecha ilegible", {"verificado": True, "fecha": "cuando sea"}),
    ],
)
async def test_avisa_cuando_el_respaldo_no_esta(
    monkeypatch: pytest.MonkeyPatch, caso: str, constancia: dict[str, Any] | None
) -> None:
    """Las cinco formas de no tener respaldo, y la tercera es la que
    más engaña: una constancia de un respaldo que no se pudo abrir da
    tranquilidad sin darla."""
    _con_base_viva(monkeypatch)
    _con_constancia(monkeypatch, constancia)

    async with _cliente() as c:
        r = await c.get("/api/health")

    datos = r.json()
    assert datos["last_backup"]["up_to_date"] is False, caso
    assert datos["last_backup"]["reason"], f"{caso}: no dice por qué"
    assert [a for a in datos["warnings"] if a.startswith("RESPALDO:")], f"{caso}: no avisó"


@pytest.mark.api
async def test_un_respaldo_viejo_no_deja_el_servicio_como_caido(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La aplicación funciona perfectamente sin respaldo fresco.

    Lo que falta es la red, no el servicio. Confundirlos haría que un
    monitor externo avise de una caída que no pasó —y que el día que
    haya una de verdad, nadie le crea.
    """
    _con_base_viva(monkeypatch)
    _con_constancia(monkeypatch, {"verificado": True, "fecha": _hace(500)})

    async with _cliente() as c:
        r = await c.get("/api/health")

    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ==================================================================
#  Formato de errores (§9.3)
# ==================================================================
@pytest.mark.api
async def test_una_ruta_inexistente_usa_el_formato_uniforme() -> None:
    async with _cliente() as c:
        r = await c.get("/api/no-existe")

    assert r.status_code == 404
    cuerpo = r.json()
    assert "error" in cuerpo, "todo error sale como {'error': {...}}"
    assert cuerpo["error"]["code"] == "NOT_FOUND"
    assert cuerpo["error"]["message"]


@pytest.mark.api
async def test_un_metodo_no_permitido_usa_el_formato_uniforme() -> None:
    async with _cliente() as c:
        r = await c.post("/api/health")

    assert r.status_code == 405
    assert "error" in r.json()
    assert r.json()["error"]["code"]


@pytest.mark.api
async def test_la_documentacion_interactiva_existe_fuera_de_produccion() -> None:
    from app.core.config import settings

    async with _cliente() as c:
        r = await c.get("/api/docs")

    if settings.es_produccion:
        assert r.status_code == 404, "en producción la documentación no se expone"
    else:
        assert r.status_code == 200

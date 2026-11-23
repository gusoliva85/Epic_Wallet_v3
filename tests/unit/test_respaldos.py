"""El portón que no deja migrar sin respaldo · F18-T04.

Esto se testea porque es lo único que separa «migrar» de «migrar sin
red», y porque se equivoca en silencio: un portón que deja pasar
cuando no debía no da ningún síntoma hasta la noche en que la
migración sale mal y no hay con qué volver atrás. La pantalla no lo
muestra nunca.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.core import respaldos

AHORA = datetime(2026, 11, 23, 20, 0, tzinfo=UTC)


def constancia(**cambios):
    base = {
        "archivo": "diario/epic_wallet_2026-11-23_1900.dump",
        "fecha": (AHORA - timedelta(minutes=30)).isoformat(),
        "tablas": 11,
        "bytes": 48976,
        "etiqueta": "diario",
        "verificado": True,
    }
    base.update(cambios)
    return base


# ===================================================================
#  Cuándo hay red
# ===================================================================


def test_un_respaldo_recien_tomado_deja_migrar():
    assert respaldos.evaluar(constancia(), AHORA).hay_red


def test_sin_constancia_no_se_migra():
    v = respaldos.evaluar(None, AHORA)
    assert not v.hay_red
    assert "no hay ninguna constancia" in v.motivo


def test_un_respaldo_que_no_quedo_verificado_no_sirve():
    """Es el caso peligroso: hay archivo, pero nadie pudo abrirlo.

    Da tranquilidad sin darla, que es peor que no tener nada.
    """
    v = respaldos.evaluar(constancia(verificado=False), AHORA)
    assert not v.hay_red
    assert "no quedó verificado" in v.motivo


def test_el_respaldo_de_anoche_no_alcanza():
    """El nocturno corre a las 3:15. Migrar a las 20:00 con ése
    significaría poder perder el día entero de carga."""
    anoche = (AHORA - timedelta(hours=17)).isoformat()
    v = respaldos.evaluar(constancia(fecha=anoche), AHORA)
    assert not v.hay_red
    assert "17.0 h" in v.motivo


def test_justo_en_el_limite_pasa_y_un_minuto_despues_no():
    casi = (AHORA - timedelta(hours=3) + timedelta(minutes=1)).isoformat()
    pasado = (AHORA - timedelta(hours=3, minutes=1)).isoformat()
    assert respaldos.evaluar(constancia(fecha=casi), AHORA).hay_red
    assert not respaldos.evaluar(constancia(fecha=pasado), AHORA).hay_red


def test_una_fecha_en_el_futuro_no_se_da_por_buena():
    """Un reloj mal puesto haría que cualquier respaldo viejo pasara
    como fresco, que es justo lo que el portón tiene que impedir."""
    futuro = (AHORA + timedelta(hours=5)).isoformat()
    v = respaldos.evaluar(constancia(fecha=futuro), AHORA)
    assert not v.hay_red
    assert "reloj" in v.motivo


@pytest.mark.parametrize("valor", ["", "ayer", "2026-13-45"])
def test_una_fecha_ilegible_no_pasa(valor):
    assert not respaldos.evaluar(constancia(fecha=valor), AHORA).hay_red


def test_el_maximo_se_puede_mover():
    viejo = (AHORA - timedelta(hours=10)).isoformat()
    assert not respaldos.evaluar(constancia(fecha=viejo), AHORA).hay_red
    assert respaldos.evaluar(constancia(fecha=viejo), AHORA, 24).hay_red


# ===================================================================
#  Qué bases están exentas
# ===================================================================


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://epic:x@db:5432/epic_wallet_test",
        "postgresql+psycopg://epic:x@db:5432/epic_wallet_restaurado",
        "postgresql+psycopg://epic:x@db:5432/pruebas_locales",
    ],
)
def test_las_bases_descartables_no_piden_respaldo(url):
    assert respaldos.es_descartable(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://epic:x@db:5432/epic_wallet",
        "postgresql+psycopg://epic:x@localhost:5432/epic_wallet?sslmode=require",
    ],
)
def test_la_base_real_siempre_pide_respaldo(url):
    assert not respaldos.es_descartable(url)


# ===================================================================
#  Leer la constancia del disco
# ===================================================================


def test_se_lee_el_ultimo_json(tmp_path):
    (tmp_path / "ultimo.json").write_text(json.dumps(constancia()), encoding="utf-8")
    assert respaldos.leer_constancia(tmp_path)["tablas"] == 11


def test_una_carpeta_sin_constancia_devuelve_none(tmp_path):
    assert respaldos.leer_constancia(tmp_path) is None


def test_un_json_roto_no_explota_y_cierra_el_porton(tmp_path):
    """Un archivo a medias no puede levantar una excepción: Alembic
    mostraría un volcado en vez del motivo, y el motivo es el punto."""
    (tmp_path / "ultimo.json").write_text('{"fecha": "2026', encoding="utf-8")
    assert respaldos.leer_constancia(tmp_path) is None
    assert not respaldos.evaluar(respaldos.leer_constancia(tmp_path), AHORA).hay_red

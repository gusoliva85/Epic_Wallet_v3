"""La tabla `profiles` y su aislamiento entre cuentas · F02-T03.

Esta es la prueba que importa de toda la tarea: **que una cuenta no
pueda ver ni tocar la fila de otra.** Sin RLS, cualquier consulta con
un token válido devolvería todas las filas, y alcanzaría con crear una
cuenta para ver las finanzas de los demás.

No se simula nada. Se corre contra Postgres de verdad, fijando los
claims del token igual que los pone la aplicación: `auth.uid()` lee
`request.jwt.claims->>'sub'`, así que poniendo ese valor se reproduce
exactamente lo que va a pasar en producción.

Se salta sola si no hay base configurada, para que la suite siga
corriendo en una máquina sin `.env`.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text

from tests.api.ayudas_db import escritura, lectura
from tests.api.entorno import (
    ESQUEMA,
    URL_BASE,
    Cuenta,
    crear_cuenta,
)


def _crear_cuenta() -> Cuenta:
    """Una cuenta descartable nueva, con su token."""
    return crear_cuenta()


pytestmark = pytest.mark.api

URL = URL_BASE

sin_base = pytest.mark.skipif(
    not URL or URL.startswith("sqlite"),
    reason="hace falta Postgres: RLS no existe en SQLite",
)


# ===================================================================
#  DE DÓNDE SALEN LAS DOS CUENTAS DE ESTA PRUEBA
#
#  ESTE FIXTURE BORRA PERFILES, y `profiles` es el padre de todo con
#  `on delete cascade`: borrar un perfil se lleva las categorías, los
#  meses, los movimientos, los totales, las inversiones, los pasivos y
#  las preferencias de esa cuenta.
#
#  Hasta el 2026-11-10 elegía así:
#
#      select id from auth.users order by created_at desc limit 2
#
#  o sea **las dos cuentas más nuevas de la base**. Contra la base de
#  producción eso son dos PERSONAS REALES: el 2026-11-10 esta prueba
#  borró el historial completo de dos cuentas de verdad. No es una
#  hipótesis, pasó, y por eso esta nota es tan larga.
#
#  Ahora sólo acepta cuentas descartables —las que crea la propia
#  batería, con correo `@example.com`— y si no hay dos, se saltea. Una
#  cuenta de una persona no puede entrar acá de ninguna manera.
# ===================================================================

DOMINIO_DESCARTABLE = "%@example.com"


def _dos_cuentas_descartables(motor) -> tuple[str, str]:
    """Dos cuentas descartables, creadas por esta misma batería.

    Hasta F16-T03 esta función **buscaba** cuentas ya existentes y se
    salteaba la prueba si no encontraba dos. Era la corrección de
    urgencia del accidente del 2026-11-10, cuando elegía «las dos
    cuentas más nuevas de la base» y, contra la base real, le borró el
    historial completo a dos personas.

    El efecto no buscado fue que las once pruebas de aislamiento —las
    más importantes de todas— se salteaban en silencio casi siempre.
    Ahora las cuentas se crean acá: son descartables por construcción,
    no por suerte, y las pruebas corren siempre.
    """
    a = crear_cuenta(motor)
    b = crear_cuenta(motor)
    return a.uid, b.uid


@pytest.fixture
def dos_usuarios(motor: Engine) -> Iterator[tuple[str, str]]:
    """Dos perfiles de cuentas distintas, y los borra al terminar.

    Se apoyan en usuarios que ya existen en `auth.users`: la clave
    foránea lo exige, y los crea `crear_cuenta()`, que es el único
    lugar de la batería que da de alta cuentas.
    """
    ids = _dos_cuentas_descartables(motor)

    a, b = ids
    marca = uuid.uuid4().hex[:8]
    with escritura(motor) as con:
        for uid, nombre in ((a, f"rls_a_{marca}"), (b, f"rls_b_{marca}")):
            con.execute(
                text(
                    f'insert into "{ESQUEMA}".profiles (id, username) '
                    "values (:id, :u) on conflict (id) do update set username = :u"
                ),
                {"id": uid, "u": nombre},
            )

    yield a, b

    with escritura(motor) as con:
        con.execute(
            text(f'delete from "{ESQUEMA}".profiles where id = any(:ids)'),
            {"ids": [a, b]},
        )


def _como(con: Any, uid: str) -> None:
    """Deja la conexión hablando como ese usuario.

    Es lo mismo que hace `core/db.py` al atender una petición: el rol
    pasa a `authenticated` y `auth.uid()` lee el `sub` de los claims.
    """
    con.execute(text("set local role authenticated"))
    con.execute(
        text("select set_config('request.jwt.claims', :c, true)"),
        {"c": f'{{"sub":"{uid}","role":"authenticated"}}'},
    )


# ------------------------------------------------- la tabla quedó bien


@sin_base
def test_la_tabla_existe_con_sus_columnas(motor: Engine) -> None:
    with lectura(motor) as con:
        columnas = {
            f[0]: f[1]
            for f in con.execute(
                text(
                    "select column_name, data_type from information_schema.columns "
                    "where table_schema = :e and table_name = 'profiles'"
                ),
                {"e": ESQUEMA},
            )
        }
    esperadas = {
        "id",
        "username",
        "display_name",
        "opening_balance",
        "timezone",
        "active",
        "created_at",
        "updated_at",
        "last_login_at",
    }
    assert esperadas <= set(columnas), f"faltan columnas: {esperadas - set(columnas)}"
    assert columnas["opening_balance"] == "numeric", (
        "el saldo tiene que ser numeric: con float, los centavos se redondean mal"
    )


@sin_base
def test_borrar_la_cuenta_se_lleva_el_perfil(motor: Engine) -> None:
    """La cascada es lo que evita filas huérfanas apuntando a un usuario
    que ya no existe."""
    with lectura(motor) as con:
        regla = con.execute(
            text(
                "select rc.delete_rule from information_schema.referential_constraints rc "
                "join information_schema.table_constraints tc "
                "  on tc.constraint_name = rc.constraint_name "
                "where tc.table_schema = :e and tc.table_name = 'profiles'"
            ),
            {"e": ESQUEMA},
        ).scalar()
    assert regla == "CASCADE"


# --------------------------------------------- el aislamiento entre cuentas


@sin_base
def test_cada_cuenta_ve_solo_su_perfil(motor: Engine, dos_usuarios: tuple[str, str]) -> None:
    """Criterio de aceptación de la tarea."""
    a, b = dos_usuarios

    with escritura(motor) as con:
        _como(con, a)
        filas = [str(f[0]) for f in con.execute(text(f'select id from "{ESQUEMA}".profiles'))]

    assert filas == [a], (
        f"con el token de {a} se ven {len(filas)} filas: {filas}. RLS no está filtrando."
    )
    assert b not in filas


@sin_base
def test_una_cuenta_no_puede_tocar_el_perfil_de_otra(
    motor: Engine, dos_usuarios: tuple[str, str]
) -> None:
    """Ver no alcanza: también hay que impedir escribir.

    Una política que sólo filtrara lecturas dejaría que alguien
    cambiara el saldo inicial de otra persona.
    """
    a, b = dos_usuarios

    with escritura(motor) as con:
        _como(con, a)
        resultado = con.execute(
            text(f'update "{ESQUEMA}".profiles set display_name = :n where id = :id'),
            {"n": "intruso", "id": b},
        )
        assert resultado.rowcount == 0, "pudo modificar el perfil de otra cuenta"

    # Y la fila de B quedó intacta.
    with lectura(motor) as con:
        nombre = con.execute(
            text(f'select display_name from "{ESQUEMA}".profiles where id = :id'),
            {"id": b},
        ).scalar()
    assert nombre != "intruso"


@sin_base
def test_una_cuenta_no_puede_crear_un_perfil_ajeno(
    motor: Engine, dos_usuarios: tuple[str, str]
) -> None:
    """El `with check` de la política. Sin él, se podría insertar una
    fila con el id de otro y después leerla como propia."""
    a, _b = dos_usuarios
    ajeno = str(uuid.uuid4())

    with escritura(motor) as con:
        _como(con, a)
        with pytest.raises(Exception) as caso:
            con.execute(
                text(f'insert into "{ESQUEMA}".profiles (id, username) values (:id, :u)'),
                {"id": ajeno, "u": "ajeno"},
            )
        assert "policy" in str(caso.value).lower() or "violates" in str(caso.value).lower()


@sin_base
def test_sin_token_no_se_ve_nada(motor: Engine, dos_usuarios: tuple[str, str]) -> None:
    """Una conexión autenticada sin `sub` no es nadie: no tiene que ver
    ninguna fila, en lugar de verlas todas."""
    with escritura(motor) as con:
        con.execute(text("set local role authenticated"))
        con.execute(text("select set_config('request.jwt.claims', :c, true)"), {"c": "{}"})
        filas = con.execute(text(f'select count(*) from "{ESQUEMA}".profiles')).scalar()

    assert filas == 0


# ------------------------------------- la protección está realmente activa


@sin_base
def test_rls_esta_activo_y_es_obligatorio(motor: Engine) -> None:
    """`enable` no alcanza: sin `force`, el dueño de la tabla se saltea
    la política y el aislamiento pasa a depender de con qué rol se
    conecte la aplicación."""
    with lectura(motor) as con:
        fila = con.execute(
            text(
                "select relrowsecurity, relforcerowsecurity from pg_class c "
                "join pg_namespace n on n.oid = c.relnamespace "
                "where n.nspname = :e and c.relname = 'profiles'"
            ),
            {"e": ESQUEMA},
        ).one()
    assert fila[0] is True, "RLS no está habilitado"
    assert fila[1] is True, "RLS no es obligatorio para el dueño de la tabla"


@sin_base
def test_la_politica_se_llama_own_profile_y_cubre_todo(motor: Engine) -> None:
    with lectura(motor) as con:
        filas = list(
            con.execute(
                text(
                    "select policyname, cmd from pg_policies where schemaname = :e and tablename = 'profiles'"
                ),
                {"e": ESQUEMA},
            )
        )
    nombres = {f[0] for f in filas}
    assert "own_profile" in nombres, f"políticas encontradas: {nombres}"
    assert any(f[1] == "ALL" for f in filas), (
        "la política tiene que cubrir las cuatro operaciones, no sólo select"
    )


# ------------------------------------------------- el trigger de updated_at


@sin_base
def test_updated_at_se_actualiza_solo(motor: Engine, dos_usuarios: tuple[str, str]) -> None:
    """Va en la base y no en la aplicación: así también cambia cuando
    una fila se toca desde SQL, sin pasar por la API."""
    a, _ = dos_usuarios

    with lectura(motor) as con:
        antes = con.execute(
            text(f'select updated_at from "{ESQUEMA}".profiles where id = :id'),
            {"id": a},
        ).scalar()

    with escritura(motor) as con:
        con.execute(
            text(f'update "{ESQUEMA}".profiles set display_name = :n where id = :id'),
            {"n": "cambiado", "id": a},
        )

    with lectura(motor) as con:
        despues = con.execute(
            text(f'select updated_at from "{ESQUEMA}".profiles where id = :id'),
            {"id": a},
        ).scalar()

    assert despues > antes, "updated_at no se movió al modificar la fila"


@sin_base
def test_la_funcion_del_trigger_no_hereda_el_search_path(motor: Engine) -> None:
    """Es `security definer`: corre con los permisos de quien la creó.

    Sin `search_path = ''`, quien pueda crear una tabla en un esquema
    que esté antes en el camino de búsqueda podría hacer que la función
    llame a SU código con esos permisos.
    """
    with lectura(motor) as con:
        config = con.execute(
            text(
                "select proconfig from pg_proc p join pg_namespace n "
                "on n.oid = p.pronamespace "
                "where n.nspname = :e and p.proname = 'tocar_updated_at'"
            ),
            {"e": ESQUEMA},
        ).scalar()
    assert config and any("search_path=" in c for c in config), (
        f"la función no fija search_path: {config}"
    )

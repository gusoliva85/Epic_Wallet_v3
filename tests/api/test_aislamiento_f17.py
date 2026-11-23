"""Aislamiento entre cuentas, contra la autenticación propia · F17-T05.

`test_aislamiento_f11.py` ya barre los endpoints de datos con dos
cuentas. Lo que no podía probar es lo de ahora: hasta F17 los tokens
los emitía un proveedor ajeno y la batería los firmaba a mano, no había
endpoints de sesión, y `refresh_tokens` y `password_resets` no
existían. Esto rehace el barrido contra la autenticación nueva y le
suma las dos cosas que antes no se podían mirar.

QUÉ AGREGA, Y POR QUÉ CADA PARTE

1. **Las cuentas nacen por el camino de verdad.** Se crean con
   `POST /api/auth/signup` y el token es el que **emitió el servidor**,
   no uno que la prueba se firmó a sí misma. Si el alta, la emisión o
   la verificación quedaran mal pegadas, el barrido entero falla acá y
   no en una pantalla.

2. **El barrido de F11, con esos tokens.** No se copia la lista de
   endpoints: se importa la de F11, que ya tiene su propia prueba
   comparándola contra el esquema OpenAPI. Una lista duplicada se
   queda vieja en silencio, que es el agujero que esta tarea cierra.

3. **Los endpoints de sesión, entre dos cuentas.** Renovar, salir,
   cambiar la contraseña y canjear un enlace son operaciones que tocan
   filas de una cuenta; ninguna puede alcanzar las de otra. Cerrar la
   sesión de B no puede dejar a A afuera, y un enlace de A no puede
   cambiarle la contraseña a B.

4. **RLS, salteando el endpoint.** El criterio de aceptación pide que
   el aislamiento aguante incluso sin pasar por la API. Acá se habla
   con Postgres directamente, con el rol y los claims de B, y se
   intenta leer y borrar las filas de A en **todas** las tablas de
   datos de usuario —descubiertas de `information_schema`, no de una
   lista escrita a mano, así que las tablas nuevas entran solas—.

NO SE REPITE lo que ya cubren otros módulos: que sin token todo dé 401
lo hace `test_api_protegida.py`, y la mecánica de los tokens de sesión
—rotación, familia, tiempos— la hace `test_auth.py`. Acá sólo se mira
el cruce entre dos cuentas.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from tests.api import test_aislamiento_f11 as f11
from tests.api.ayudas_db import lectura
from tests.api.entorno import (
    DOMINIO_DE_PRUEBA,
    ESQUEMA,
    Cuenta,
    borrar_cuentas,
    sin_entorno,
)

pytestmark = sin_entorno

CLAVE_A = "clave-de-la-cuenta-a"
CLAVE_B = "clave-de-la-cuenta-b"


def _correo() -> str:
    return f"epicwallet.{secrets.token_hex(6)}@{DOMINIO_DE_PRUEBA}"


# ===================================================================
#  Las dos cuentas, creadas por el endpoint de alta
# ===================================================================


@dataclass(frozen=True)
class Alta:
    """Una cuenta recién creada y la sesión que devolvió el servidor."""

    cuenta: Cuenta
    clave: str
    renovacion: str


def _dar_de_alta(cliente: Any, clave: str) -> Alta:
    correo = _correo()
    r = cliente.post("/api/auth/signup", json={"email": correo, "password": clave})
    assert r.status_code == 201, r.text
    datos = r.json()
    return Alta(
        cuenta=Cuenta(uid=datos["user"]["id"], correo=correo, token=datos["access_token"]),
        clave=clave,
        renovacion=datos["refresh_token"],
    )


def _entrar(cliente: Any, alta: Alta) -> dict[str, Any]:
    """Una sesión nueva para esa cuenta, por el login de verdad.

    Cada prueba que necesita un token de renovación pide el suyo: así
    ninguna depende de en qué orden corrieron las demás, que con
    tokens rotatorios sería una trampa —el de la prueba anterior quedó
    quemado—.
    """
    r = cliente.post("/api/auth/login", json={"email": alta.cuenta.correo, "password": alta.clave})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def altas(cliente, motor) -> Iterator[tuple[Alta, Alta]]:
    """Dos cuentas para todo el módulo, con sus contraseñas conocidas."""
    a = _dar_de_alta(cliente, CLAVE_A)
    b = _dar_de_alta(cliente, CLAVE_B)
    yield a, b
    borrar_cuentas(motor, a.cuenta.uid, b.cuenta.uid)


@pytest.fixture(scope="module")
def cuentas(altas: tuple[Alta, Alta]) -> tuple[Cuenta, Cuenta]:
    """Lo que esperan el sembrado y el barrido importados de F11.

    Son las mismas dos cuentas de `altas`, con la forma que pide aquel
    módulo: `uid` y `cabeceras`. La diferencia con F11 es de dónde
    salió el token.
    """
    a, b = altas
    return a.cuenta, b.cuenta


# El sembrado de A es el de F11 —una categoría, un movimiento, un mes
# histórico, una inversión y una preferencia—, reusado tal cual para no
# tener dos versiones del mismo escenario. Se registra como fixture de
# este módulo apuntando a la función de allá; toma el `cuentas` de
# acá, que son las cuentas con los tokens nuevos.
datos = f11.datos


@pytest.fixture(scope="module")
def par_descartable(cliente, motor) -> Iterator[tuple[Alta, Alta]]:
    """Otras dos cuentas, para lo que cambia contraseñas.

    Cambiar una contraseña revoca sesiones y vuelve inservible la clave
    anterior. Hacerlo sobre `altas` obligaría a dejar todo como estaba
    después de cada prueba, y una prueba que repara el escenario es una
    prueba que puede repararlo mal. Estas son de usar y tirar.
    """
    a = _dar_de_alta(cliente, "clave-descartable-uno")
    b = _dar_de_alta(cliente, "clave-descartable-dos")
    yield a, b
    borrar_cuentas(motor, a.cuenta.uid, b.cuenta.uid)


def _enlace_para(correo: str) -> str:
    """Un enlace de contraseña nueva, por el mismo camino que el CLI.

    No hay ningún endpoint que emita enlaces —es la decisión de
    F17-T04—, así que la prueba llama al servicio igual que
    `app.cli recuperar`.
    """
    from api.app.core.db import sesion_manual
    from api.app.services import sesiones

    with sesion_manual() as sesion:
        token = sesiones.emitir_enlace(sesion, correo)
    assert token, f"no se pudo emitir un enlace para {correo}"
    return token


# ===================================================================
#  1 · Las cuentas nacen por el camino de verdad
# ===================================================================


def test_el_token_que_emitio_el_servidor_abre_la_cuenta_correcta(
    cliente, altas: tuple[Alta, Alta]
) -> None:
    """La base de todo lo que sigue.

    Si esto fallara, el barrido de abajo podría pasar en verde por el
    motivo equivocado: dos tokens que no abren nada no se cruzan nunca.
    """
    a, b = altas
    for alta in (a, b):
        r = cliente.get("/api/me", headers=alta.cuenta.cabeceras)
        assert r.status_code == 200, r.text
        assert r.json()["id"] == alta.cuenta.uid

    assert a.cuenta.uid != b.cuenta.uid


def test_cada_cuenta_nace_con_sus_propias_21_categorias(cliente, altas: tuple[Alta, Alta]) -> None:
    """Las crea el trigger de la base. Que sean 21 en cada una, y no 42
    en una sola, es la primera señal de que el alta no las cruza."""
    a, b = altas
    for alta in (a, b):
        r = cliente.get("/api/categories", headers=alta.cuenta.cabeceras)
        assert r.status_code == 200, r.text
        assert len(r.json()) == 21, f"{alta.cuenta.correo} quedó con {len(r.json())}"


# ===================================================================
#  2 · El barrido de F11, con los tokens nuevos
# ===================================================================


def test_con_el_token_de_b_ningun_recurso_de_a_es_alcanzable(
    cliente, cuentas: tuple[Cuenta, Cuenta], datos: f11.DatosDeA
) -> None:
    """Criterio de aceptación: ningún recurso ajeno es accesible, ni
    pasando su `id` a mano.

    La lista de endpoints se importa de F11 a propósito: allá hay una
    prueba que la compara contra el esquema OpenAPI y falla si alguien
    agrega un endpoint con id. Copiarla acá sería tener dos listas y
    una sola protegida.
    """
    _, b = cuentas
    extra = {"/api/categories/{category_id}/detail": {"year": 2026, "month": 1}}

    fallos = []
    for metodo, direccion, plantilla, cuerpo in f11._endpoints_con_id(datos):
        kwargs: dict[str, Any] = {"headers": b.cabeceras}
        if cuerpo is not None:
            kwargs["json"] = cuerpo
        if plantilla in extra:
            kwargs["params"] = extra[plantilla]

        r = getattr(cliente, metodo)(direccion, **kwargs)
        if r.status_code != 404:
            fallos.append(f"{metodo.upper()} {plantilla} → {r.status_code} ({r.text[:120]})")

    assert not fallos, "endpoints que no devolvieron 404 con un id ajeno:\n" + "\n".join(fallos)


def test_ninguna_coleccion_de_b_trae_datos_de_a(
    cliente, cuentas: tuple[Cuenta, Cuenta], datos: f11.DatosDeA
) -> None:
    """Se mira el texto crudo de cada respuesta: si un dato de A se
    filtra por un camino que nadie pensó, aparece igual."""
    _, b = cuentas
    agujas = [f11.NOMBRE_CATEGORIA, f11.DESCRIPCION_MOVIMIENTO, f11.SIMBOLO_INVERSION, "@"]

    rutas = [
        "/api/me",
        "/api/categories",
        "/api/transactions",
        "/api/months",
        "/api/months/savings-evolution",
        "/api/investments",
        "/api/patrimony",
        "/api/settings",
        "/api/dashboard",
        "/api/export",
    ]

    fallos = []
    for ruta in rutas:
        r = cliente.get(ruta, headers=b.cabeceras)
        assert r.status_code == 200, f"{ruta} → {r.status_code}: {r.text[:200]}"
        for aguja in agujas:
            # El correo de A es la aguja nueva de F17: antes el token no
            # lo llevaba y ninguna respuesta podía contenerlo.
            objetivo = cuentas[0].correo if aguja == "@" else aguja
            if objetivo in r.text:
                fallos.append(f"{ruta} filtró «{objetivo}»")

    assert not fallos, "\n".join(fallos)


def test_la_cuenta_de_a_quedo_intacta_despues_de_todos_los_intentos(
    cliente, cuentas: tuple[Cuenta, Cuenta], datos: f11.DatosDeA
) -> None:
    """La otra mitad del aislamiento, y la que un 404 no garantiza: un
    endpoint que contesta 404 y borra la fila igual sería peor que no
    tener aislamiento, porque además no se notaría. Los `DELETE` de B ya
    corrieron arriba."""
    a, _ = cuentas

    categorias = cliente.get("/api/categories", headers=a.cabeceras).json()
    assert [c for c in categorias if c["name"] == f11.NOMBRE_CATEGORIA], "B borró la categoría de A"

    movimientos = cliente.get("/api/transactions", headers=a.cabeceras).json()
    mio = [t for t in movimientos if t.get("description") == f11.DESCRIPCION_MOVIMIENTO]
    assert mio, "B borró el movimiento de A"
    assert mio[0]["amount"] == "12345.67", "B cambió el importe del movimiento de A"

    mes = cliente.get(f"/api/months/{datos.mes}", headers=a.cabeceras)
    assert mes.status_code == 200
    assert mes.json()["income_total"] == "900000.00", "B corrigió el mes histórico de A"

    inversiones = cliente.get("/api/investments", headers=a.cabeceras).json()
    assert [i for i in inversiones["positions"] if i["symbol"] == f11.SIMBOLO_INVERSION], (
        "B vendió la posición de A"
    )


# ===================================================================
#  3 · Los endpoints de sesión, entre dos cuentas
# ===================================================================


def test_renovar_devuelve_siempre_la_cuenta_del_token_de_renovacion(
    cliente, altas: tuple[Alta, Alta]
) -> None:
    """El token de renovación es azar puro y no dice de quién es: de eso
    se encarga la fila. Mandar el de A con la cabecera de B no puede
    abrir la sesión de B, ni al revés."""
    a, b = altas
    sesion_de_a = _entrar(cliente, a)

    r = cliente.post(
        "/api/auth/refresh",
        json={"refresh_token": sesion_de_a["refresh_token"]},
        headers=b.cuenta.cabeceras,
    )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["id"] == a.cuenta.uid, "la renovación se fue a la cuenta equivocada"
    assert r.json()["user"]["email"] == a.cuenta.correo

    # Y el par nuevo también es de A.
    nuevo = cliente.get("/api/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert nuevo.json()["id"] == a.cuenta.uid


def test_el_logout_de_b_no_corta_la_sesion_de_a(cliente, altas: tuple[Alta, Alta]) -> None:
    """Salir corta una familia de tokens, no una tabla.

    Si `revocar_familia` se equivocara de fila —o si `salir` filtrara
    por algo que no es la familia—, cerrar sesión en un teléfono
    dejaría afuera a otra persona.
    """
    a, b = altas
    sesion_de_a = _entrar(cliente, a)
    sesion_de_b = _entrar(cliente, b)

    assert (
        cliente.post(
            "/api/auth/logout", json={"refresh_token": sesion_de_b["refresh_token"]}
        ).status_code
        == 204
    )

    # La de B murió…
    muerta = cliente.post("/api/auth/refresh", json={"refresh_token": sesion_de_b["refresh_token"]})
    assert muerta.status_code == 401

    # …y la de A sigue viva.
    viva = cliente.post("/api/auth/refresh", json={"refresh_token": sesion_de_a["refresh_token"]})
    assert viva.status_code == 200, viva.text
    assert viva.json()["user"]["id"] == a.cuenta.uid


def test_cambiar_la_clave_de_b_no_toca_la_cuenta_de_a(
    cliente, par_descartable: tuple[Alta, Alta]
) -> None:
    """Cambiar la contraseña revoca **todas** las sesiones de esa
    cuenta. «Todas» tiene que querer decir las de esa cuenta."""
    a, b = par_descartable
    sesion_de_a = _entrar(cliente, a)

    r = cliente.put(
        "/api/auth/password",
        json={"current_password": b.clave, "new_password": "la-nueva-de-b"},
        headers=b.cuenta.cabeceras,
    )
    assert r.status_code == 200, r.text

    # A entra con su contraseña de siempre y su sesión sigue en pie.
    assert (
        cliente.post(
            "/api/auth/login", json={"email": a.cuenta.correo, "password": a.clave}
        ).status_code
        == 200
    )
    sigue = cliente.post("/api/auth/refresh", json={"refresh_token": sesion_de_a["refresh_token"]})
    assert sigue.status_code == 200, "cambiar la clave de B revocó la sesión de A"
    assert sigue.json()["user"]["id"] == a.cuenta.uid


def test_la_clave_de_otra_cuenta_no_sirve_para_cambiar_la_propia(
    cliente, altas: tuple[Alta, Alta]
) -> None:
    """`PUT /password` pide la contraseña actual. La actual **de quien
    manda el token**, no una cualquiera que ande dando vueltas."""
    a, b = altas
    r = cliente.put(
        "/api/auth/password",
        json={"current_password": a.clave, "new_password": "no-deberia-entrar"},
        headers=b.cuenta.cabeceras,
    )
    assert r.status_code == 400, r.text

    # Y la de B quedó donde estaba.
    assert (
        cliente.post(
            "/api/auth/login", json={"email": b.cuenta.correo, "password": b.clave}
        ).status_code
        == 200
    )


def test_un_enlace_de_recuperacion_sirve_para_una_sola_cuenta(
    cliente, par_descartable: tuple[Alta, Alta]
) -> None:
    """El enlace lleva la cuenta adentro de su fila, no en la URL: nada
    de lo que viaja se puede cambiar para apuntarlo a otra."""
    a, b = par_descartable
    token = _enlace_para(a.cuenta.correo)

    r = cliente.post(
        "/api/auth/reset", json={"token": token, "new_password": "restablecida-para-a"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["id"] == a.cuenta.uid, "el enlace cambió la cuenta equivocada"

    # La contraseña de B es la que B tenga en este punto —otra prueba
    # pudo haberla cambiado—, así que lo que se comprueba es lo que no
    # puede pasar de ninguna manera: que la nueva de A abra la de B.
    cruzado = cliente.post(
        "/api/auth/login",
        json={"email": b.cuenta.correo, "password": "restablecida-para-a"},
    )
    assert cruzado.status_code == 401


def test_pedir_un_enlace_para_una_cuenta_no_anula_el_de_otra(
    cliente, par_descartable: tuple[Alta, Alta]
) -> None:
    """Emitir un enlace quema los anteriores **de esa cuenta**. Si
    quemara los de todas, un segundo pedido rompería la recuperación de
    cualquier otro que estuviera a mitad de camino."""
    a, b = par_descartable
    de_a = _enlace_para(a.cuenta.correo)
    _enlace_para(b.cuenta.correo)

    r = cliente.post(
        "/api/auth/reset", json={"token": de_a, "new_password": "sigue-sirviendo-el-de-a"}
    )
    assert r.status_code == 200, "el enlace de B anuló el de A"
    assert r.json()["user"]["id"] == a.cuenta.uid


def test_el_alta_con_el_correo_de_otra_cuenta_no_la_toca(cliente, altas: tuple[Alta, Alta]) -> None:
    """Registrarse con un correo que ya tiene cuenta se rechaza con un
    mensaje que no confirma nada, y —lo que importa acá— no le cambia
    la contraseña ni le abre una sesión a la cuenta que ya existía."""
    a, _ = altas
    r = cliente.post(
        "/api/auth/signup", json={"email": a.cuenta.correo, "password": "intento-de-tomarla"}
    )
    assert r.status_code == 409
    assert "access_token" not in r.text

    assert (
        cliente.post(
            "/api/auth/login", json={"email": a.cuenta.correo, "password": "intento-de-tomarla"}
        ).status_code
        == 401
    )
    assert (
        cliente.post(
            "/api/auth/login", json={"email": a.cuenta.correo, "password": a.clave}
        ).status_code
        == 200
    )


# ===================================================================
#  4 · RLS, salteando el endpoint
# ===================================================================


def _tablas_de_usuario(motor: Engine) -> list[tuple[str, str]]:
    """Las tablas de datos de usuario y la columna que dice de quién son.

    Se descubren de `information_schema` y no de una lista: una tabla
    nueva tiene que entrar sola a esta prueba. `profiles` va aparte
    porque su dueño es `id` —es la fila de la cuenta, no una fila que
    le pertenece—.
    """
    with lectura(motor) as con:
        filas = [
            f[0]
            for f in con.execute(
                text(
                    "select table_name from information_schema.columns "
                    "where table_schema = :e and column_name = 'user_id' "
                    "order by table_name"
                ),
                {"e": ESQUEMA},
            )
        ]
    return [("profiles", "id"), *((t, "user_id") for t in filas)]


def _como(con: Any, uid: str) -> None:
    """Deja la conexión hablando como ese usuario: el rol que usa la
    aplicación y los claims de los que `auth.uid()` lee el `sub`."""
    from api.app.core.db import ROL_DE_USUARIO

    con.execute(text(f"set local role {ROL_DE_USUARIO}"))
    con.execute(
        text("select set_config('request.jwt.claims', :c, true)"),
        {"c": f'{{"sub":"{uid}","role":"{ROL_DE_USUARIO}"}}'},
    )


# Dónde tiene que haber filas de A para que la prueba signifique algo.
# Si una de estas queda vacía, «B no ve nada de A» se cumple sin haber
# comprobado nada, y eso es lo que la prueba de abajo no permite.
CON_FILAS_DE_A = {
    "profiles",
    "categories",
    "transactions",
    "months",
    "investments",
    "app_settings",
    "refresh_tokens",
    "password_resets",
}


@pytest.fixture(scope="module")
def filas_de_a(cuentas: tuple[Cuenta, Cuenta], datos: f11.DatosDeA) -> str:
    """El uid de A, con una fila suya en cada tabla que importa.

    El sembrado de F11 cubre casi todas; `refresh_tokens` la dejó el
    alta, y `password_resets` se crea acá emitiendo un enlace **que no
    se canjea**: alcanza con que la fila exista.
    """
    a, _ = cuentas
    _enlace_para(a.correo)
    return a.uid


def test_rls_esta_activo_y_es_obligatorio_en_todas_las_tablas(motor: Engine) -> None:
    """La exigencia que CLAUDE.md no negocia, y la parte que se olvida:
    «incluidas las nuevas».

    `enable` sin `force` deja que el dueño de la tabla se saltee la
    política, y entonces el aislamiento pasa a depender de con qué rol
    se conecte la aplicación. `refresh_tokens` y `password_resets` son
    las dos tablas nuevas de F17 y entran acá sin que nadie las anote.
    """
    tablas = _tablas_de_usuario(motor)
    assert len(tablas) >= 11, f"se descubrieron muy pocas tablas: {tablas}"

    with lectura(motor) as con:
        estado = {
            f[0]: (f[1], f[2])
            for f in con.execute(
                text(
                    "select c.relname, c.relrowsecurity, c.relforcerowsecurity "
                    "from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                    "where n.nspname = :e and c.relkind = 'r'"
                ),
                {"e": ESQUEMA},
            )
        }
        politicas = {
            f[0]
            for f in con.execute(
                text("select distinct tablename from pg_policies where schemaname = :e"),
                {"e": ESQUEMA},
            )
        }

    fallos = []
    for tabla, _ in tablas:
        activo, obligatorio = estado.get(tabla, (None, None))
        if activo is not True:
            fallos.append(f"{tabla}: RLS no está habilitado")
        if obligatorio is not True:
            fallos.append(f"{tabla}: RLS no es obligatorio para el dueño de la tabla")
        if tabla not in politicas:
            fallos.append(f"{tabla}: no tiene ninguna política")

    assert not fallos, "\n".join(fallos)


# Postgres: «insufficient_privilege». Es el único error que cuenta
# como bloqueo.
PERMISO_DENEGADO = "42501"


def _intentar(
    motor: Engine, uid_de_quien_pide: str, consultas: list[tuple[str, str]]
) -> dict[str, int | str]:
    """Corre cada consulta con el rol y los claims de ese usuario.

    Devuelve, por tabla, cuántas filas alcanzó, o el código de error de
    Postgres si no llegó a correr.

    **El código se devuelve y no se descarta**, y eso lo enseñó esta
    misma prueba: la primera versión tomaba cualquier excepción por
    «bloqueado», y con eso el intento de `delete` pasaba en verde
    aunque RLS estuviera desactivado —lo frenaba una clave foránea, no
    la política—. Un error que no sea «permiso denegado» no prueba
    nada sobre el aislamiento, así que quien llama lo mira.

    Cada intento va en su propio savepoint: un error aborta la
    transacción, y sin savepoint se llevaría puestos los siguientes.
    """
    resultado: dict[str, int | str] = {}
    with motor.connect() as con:
        exterior = con.begin()
        con.execute(text("reset role"))
        for tabla, sql in consultas:
            punto = con.begin_nested()
            try:
                _como(con, uid_de_quien_pide)
                r = con.execute(text(sql))
                resultado[tabla] = r.scalar() or 0 if r.returns_rows else r.rowcount
                punto.commit()
            except DBAPIError as e:
                punto.rollback()
                resultado[tabla] = str(getattr(e.orig, "sqlstate", "") or "desconocido")
        # Nada de esto se guarda: lo que se mide es a qué llegó, y si
        # llegó a algo hay que dejarlo como estaba para poder decirlo.
        exterior.rollback()
    return resultado


def _revisar(alcanzado: dict[str, int | str], que_intento: str) -> None:
    """Cada tabla tiene que haber dado cero filas o permiso denegado."""
    fallos = [
        f"{tabla}: {resultado}"
        for tabla, resultado in alcanzado.items()
        if resultado not in (0, PERMISO_DENEGADO)
    ]
    assert not fallos, f"B alcanzó filas de A para {que_intento}:\n" + "\n".join(fallos)


def test_b_no_ve_ninguna_fila_de_a_hablandole_a_la_base_directamente(
    motor: Engine, cuentas: tuple[Cuenta, Cuenta], filas_de_a: str
) -> None:
    """Criterio de aceptación: RLS bloquea incluso salteando el filtro
    del endpoint.

    No hay endpoint acá. Es una conexión a Postgres con el rol y los
    claims de B pidiendo explícitamente las filas de A, que es lo que
    pasaría si un día un `where user_id` se escribiera mal.
    """
    a, b = cuentas
    tablas = _tablas_de_usuario(motor)

    # Primero, que haya algo que ver. Sin esto la prueba pasa sola.
    with lectura(motor) as con:
        reales = {
            tabla: con.execute(
                text(f'select count(*) from "{ESQUEMA}"."{tabla}" where {col} = :id'),
                {"id": a.uid},
            ).scalar()
            for tabla, col in tablas
        }
    vacias = [t for t in CON_FILAS_DE_A if not reales.get(t)]
    assert not vacias, (
        f"A no tiene filas en {vacias}: la prueba no estaría comprobando nada ahí. "
        f"Conteos: {reales}"
    )

    visto = _intentar(
        motor,
        b.uid,
        [
            (
                tabla,
                f'select count(*) from "{ESQUEMA}"."{tabla}" where {col} = \'{a.uid}\'',
            )
            for tabla, col in tablas
        ],
    )

    _revisar(visto, "leerlas")


def test_b_no_puede_escribir_ni_una_fila_de_a_hablandole_a_la_base_directamente(
    motor: Engine, cuentas: tuple[Cuenta, Cuenta], filas_de_a: str
) -> None:
    """Leer no es lo único que hay que bloquear.

    Una política de `select` que dejara pasar la escritura sería el
    peor de los dos mundos: nadie ve los datos de otro y cualquiera los
    cambia.

    El intento es un `update` que no cambia nada —le asigna a la
    columna su propio valor—, y es a propósito: lo que se mide es a
    cuántas filas **llegó**, sin meter en el medio las cascadas y las
    claves foráneas de un `delete`, que frenan la consulta por motivos
    que no tienen nada que ver con el aislamiento. Igual corre dentro
    de una transacción que se revierte.
    """
    a, b = cuentas
    tablas = _tablas_de_usuario(motor)

    _revisar(
        _intentar(
            motor,
            b.uid,
            [
                (
                    tabla,
                    f'update "{ESQUEMA}"."{tabla}" set {col} = {col} where {col} = \'{a.uid}\'',
                )
                for tabla, col in tablas
            ],
        ),
        "escribirlas",
    )

    # Y lo de A sigue ahí: la transacción se revirtió, pero esto es lo
    # que lo confirma en vez de darlo por hecho.
    with lectura(motor) as con:
        quedan = con.execute(
            text(f'select count(*) from "{ESQUEMA}".categories where user_id = :id'),
            {"id": a.uid},
        ).scalar()
    assert quedan and quedan >= 21, f"las categorías de A quedaron en {quedan}"


def test_con_los_claims_de_b_la_base_dice_que_es_b(
    motor: Engine, cuentas: tuple[Cuenta, Cuenta]
) -> None:
    """Lo que hace funcionar a todas las políticas.

    `auth.uid()` dejó de ser del proveedor y es una función nuestra
    (F16-T01). Si devolviera `null`, las políticas compararían contra
    nada y el aislamiento se apoyaría sólo en el `where` del endpoint.
    """
    _, b = cuentas
    with motor.connect() as con:
        trans = con.begin()
        con.execute(text("reset role"))
        _como(con, b.uid)
        quien = con.execute(text("select auth.uid()")).scalar()
        trans.rollback()

    assert str(quien) == b.uid, f"auth.uid() devolvió {quien!r} y tenía que devolver el uid de B"

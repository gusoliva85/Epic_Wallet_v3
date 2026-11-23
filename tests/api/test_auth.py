"""Los endpoints de sesión · F17-T02.

Esto se testea entero y sin recortes, aunque la regla del proyecto sea
testear poco: es la puerta. Un error acá no se ve en la pantalla —el
ingreso funciona igual— y deja entrar a quien no debería, o cuenta qué
correos tienen cuenta sin que nadie lo note.

Los casos que no se pueden mirar desde el celular y por eso están acá:
que dos respuestas digan **exactamente** lo mismo, que un token usado
dos veces tire abajo su cadena, y que cambiar la contraseña corte las
demás sesiones.
"""

from __future__ import annotations

import secrets

import pytest
from sqlalchemy import text

from tests.api.entorno import DOMINIO_DE_PRUEBA, borrar_cuentas, sin_entorno

pytestmark = sin_entorno

CLAVE = "contrasenia-de-prueba"


def _correo() -> str:
    return f"epicwallet.{secrets.token_hex(6)}@{DOMINIO_DE_PRUEBA}"


@pytest.fixture
def cuenta(cliente, motor):
    """Una cuenta recién creada por el endpoint de alta.

    Se borra al final por el correo, no por el uuid: si el alta falló a
    mitad de camino igual se limpia lo que haya quedado.
    """
    correo = _correo()
    r = cliente.post("/api/auth/signup", json={"email": correo, "password": CLAVE})
    assert r.status_code == 201, r.text
    datos = r.json()
    yield {"correo": correo, **datos}
    borrar_cuentas(motor, datos["user"]["id"])


# ===================================================================
#  Alta
# ===================================================================


def test_el_alta_devuelve_una_sesion_usable(cuenta, cliente):
    assert cuenta["token_type"] == "bearer"
    assert cuenta["expires_in"] == 3600
    assert cuenta["user"]["email"] == cuenta["correo"]

    r = cliente.get("/api/me", headers={"Authorization": f"Bearer {cuenta['access_token']}"})
    assert r.status_code == 200, r.text


def test_la_cuenta_nueva_nace_con_sus_21_categorias(cuenta, cliente):
    """Las crea el trigger de la base, no el endpoint. Si el alta
    dejara de pasar por `auth.users`, esto se rompería."""
    r = cliente.get(
        "/api/categories", headers={"Authorization": f"Bearer {cuenta['access_token']}"}
    )
    assert r.status_code == 200, r.text
    assert len(r.json()) == 21


def test_el_alta_no_confirma_si_un_correo_ya_tiene_cuenta(cuenta, cliente):
    """Tiene que ser indistinguible de cualquier otro rechazo: si dijera
    «ese email ya existe», el formulario sería un verificador de
    cuentas."""
    r = cliente.post("/api/auth/signup", json={"email": cuenta["correo"], "password": CLAVE})
    assert r.status_code == 409
    mensaje = r.json()["error"]["message"]
    assert "existe" not in mensaje.lower()
    assert "registrad" not in mensaje.lower()


@pytest.mark.parametrize("mala", ["corta", "1234567", ""])
def test_una_contrasenia_corta_se_rechaza(mala, cliente):
    r = cliente.post("/api/auth/signup", json={"email": _correo(), "password": mala})
    assert r.status_code in (400, 422)


def test_una_contrasenia_larguisima_se_rechaza(cliente):
    """Bcrypt ignora lo que pase de 72 bytes, en silencio. Truncar sería
    aceptar una contraseña que no es la que se escribió."""
    r = cliente.post("/api/auth/signup", json={"email": _correo(), "password": "a" * 73})
    assert r.status_code == 400


@pytest.mark.parametrize("correo", ["sinarroba", "a@b", "con espacio@x.com", "@x.com"])
def test_un_correo_con_mala_forma_se_rechaza(correo, cliente):
    r = cliente.post("/api/auth/signup", json={"email": correo, "password": CLAVE})
    assert r.status_code == 422


# ===================================================================
#  Ingreso
# ===================================================================


def test_se_entra_con_la_contrasenia_correcta(cuenta, cliente):
    r = cliente.post("/api/auth/login", json={"email": cuenta["correo"], "password": CLAVE})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["id"] == cuenta["user"]["id"]


def test_el_correo_no_distingue_mayusculas(cuenta, cliente):
    """El teclado del teléfono manda la primera letra en mayúscula por
    su cuenta. Sin esto, quien se registró desde la computadora no
    entraría desde el celular."""
    r = cliente.post(
        "/api/auth/login",
        json={"email": cuenta["correo"].upper(), "password": CLAVE},
    )
    assert r.status_code == 200, r.text


def test_una_cuenta_que_no_existe_y_una_clave_mala_dicen_lo_mismo(cuenta, cliente):
    """El caso que no se ve desde la pantalla, y el que convierte el
    formulario en un verificador de cuentas si se afloja."""
    inexistente = cliente.post("/api/auth/login", json={"email": _correo(), "password": CLAVE})
    equivocada = cliente.post(
        "/api/auth/login", json={"email": cuenta["correo"], "password": "otra-cosa"}
    )

    assert inexistente.status_code == equivocada.status_code == 401
    assert inexistente.json()["error"] == equivocada.json()["error"]


# ===================================================================
#  Renovación y rotación
# ===================================================================


def test_renovar_devuelve_un_par_nuevo(cuenta, cliente):
    r = cliente.post("/api/auth/refresh", json={"refresh_token": cuenta["refresh_token"]})
    assert r.status_code == 200, r.text
    nuevo = r.json()
    assert nuevo["refresh_token"] != cuenta["refresh_token"]
    assert nuevo["user"]["id"] == cuenta["user"]["id"]


def test_el_token_de_renovacion_no_sirve_dos_veces(cuenta, cliente):
    primero = cliente.post("/api/auth/refresh", json={"refresh_token": cuenta["refresh_token"]})
    assert primero.status_code == 200

    segundo = cliente.post("/api/auth/refresh", json={"refresh_token": cuenta["refresh_token"]})
    assert segundo.status_code == 401


def test_repetir_un_token_tira_abajo_toda_la_cadena(cuenta, cliente):
    """El caso que justifica guardar la familia.

    Si un token usado reaparece, o lo copiaron o es el legítimo que
    llegó tarde. No se puede distinguir, así que se cortan los dos y
    vuelven a entrar con la contraseña, que sabe uno solo.
    """
    primero = cliente.post(
        "/api/auth/refresh", json={"refresh_token": cuenta["refresh_token"]}
    ).json()

    # El robado se presenta de nuevo: dispara la detección.
    repetido = cliente.post("/api/auth/refresh", json={"refresh_token": cuenta["refresh_token"]})
    assert repetido.status_code == 401

    # Y ahora el que era bueno tampoco sirve.
    legitimo = cliente.post("/api/auth/refresh", json={"refresh_token": primero["refresh_token"]})
    assert legitimo.status_code == 401


def test_un_token_de_renovacion_inventado_se_rechaza(cliente):
    r = cliente.post("/api/auth/refresh", json={"refresh_token": "no-existe-esto"})
    assert r.status_code == 401


def test_una_renovacion_vencida_se_rechaza(cuenta, cliente, motor):
    """Se envejece la fila en la base en vez de esperar 30 días."""
    with motor.begin() as con:
        con.execute(text("reset role"))
        con.execute(
            text(
                "update refresh_tokens set expires_at = now() - interval '1 day' "
                "where user_id = :uid"
            ),
            {"uid": cuenta["user"]["id"]},
        )
    r = cliente.post("/api/auth/refresh", json={"refresh_token": cuenta["refresh_token"]})
    assert r.status_code == 401
    assert "expir" in r.json()["error"]["message"].lower()


# ===================================================================
#  Salir
# ===================================================================


def test_salir_corta_la_renovacion(cuenta, cliente):
    assert (
        cliente.post(
            "/api/auth/logout", json={"refresh_token": cuenta["refresh_token"]}
        ).status_code
        == 204
    )
    r = cliente.post("/api/auth/refresh", json={"refresh_token": cuenta["refresh_token"]})
    assert r.status_code == 401


@pytest.mark.parametrize("cuerpo", [{}, {"refresh_token": None}, {"refresh_token": "x"}])
def test_salir_siempre_termina_bien(cuerpo, cliente):
    """Un «cerrar sesión» que falla deja a la persona adentro, que es
    justo lo contrario de lo que pidió."""
    assert cliente.post("/api/auth/logout", json=cuerpo).status_code == 204


# ===================================================================
#  Cambiar la contraseña
# ===================================================================


def _cabeceras(sesion):
    return {"Authorization": f"Bearer {sesion['access_token']}"}


def test_cambiar_la_clave_pide_la_actual(cuenta, cliente):
    r = cliente.put(
        "/api/auth/password",
        json={"current_password": "no-es-esta", "new_password": "clave-nueva-123"},
        headers=_cabeceras(cuenta),
    )
    assert r.status_code == 400


def test_cambiar_la_clave_funciona_y_corta_las_demas_sesiones(cuenta, cliente):
    """Si alguien había entrado con la contraseña vieja, cambiarla tiene
    que echarlo. Si no, cambiarla no sirve para lo único que sirve."""
    otra = cliente.post(
        "/api/auth/login", json={"email": cuenta["correo"], "password": CLAVE}
    ).json()

    nueva = "clave-nueva-123"
    r = cliente.put(
        "/api/auth/password",
        json={"current_password": CLAVE, "new_password": nueva},
        headers=_cabeceras(cuenta),
    )
    assert r.status_code == 200, r.text

    # La otra sesión ya no puede renovar.
    assert (
        cliente.post("/api/auth/refresh", json={"refresh_token": otra["refresh_token"]}).status_code
        == 401
    )
    # Con la nueva se entra; con la vieja, no.
    assert (
        cliente.post(
            "/api/auth/login", json={"email": cuenta["correo"], "password": nueva}
        ).status_code
        == 200
    )
    assert (
        cliente.post(
            "/api/auth/login", json={"email": cuenta["correo"], "password": CLAVE}
        ).status_code
        == 401
    )


def test_cambiar_la_clave_sin_sesion_no_se_puede(cliente):
    r = cliente.put(
        "/api/auth/password",
        json={"current_password": CLAVE, "new_password": "clave-nueva-123"},
    )
    assert r.status_code == 401


def test_la_clave_nueva_tambien_tiene_minimo(cuenta, cliente):
    r = cliente.put(
        "/api/auth/password",
        json={"current_password": CLAVE, "new_password": "corta"},
        headers=_cabeceras(cuenta),
    )
    assert r.status_code == 400


# ===================================================================
#  Lo que no se guarda
# ===================================================================


def test_la_contrasenia_no_se_guarda_en_claro(cuenta, motor):
    with motor.begin() as con:
        con.execute(text("reset role"))
        guardado = con.execute(
            text("select encrypted_password from auth.users where id = :id"),
            {"id": cuenta["user"]["id"]},
        ).scalar_one()
    assert CLAVE not in guardado
    assert guardado.startswith("$2")


def test_el_token_de_renovacion_no_se_guarda_en_claro(cuenta, motor):
    with motor.begin() as con:
        con.execute(text("reset role"))
        huellas = [
            f[0]
            for f in con.execute(
                text("select token_hash from refresh_tokens where user_id = :uid"),
                {"uid": cuenta["user"]["id"]},
            ).all()
        ]
    assert huellas
    assert cuenta["refresh_token"] not in huellas
    assert all(len(h) == 64 for h in huellas)

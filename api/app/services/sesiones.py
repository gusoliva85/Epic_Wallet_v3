"""Entrar, renovar y salir · F17-T02.

Acá vive la decisión; el router sólo traduce a HTTP y el repositorio
sólo habla SQL.

LO QUE NO SE CUENTA

Ninguna respuesta de este módulo distingue «ese correo no tiene
cuenta» de «la contraseña está mal». Tampoco el registro: si
contestara «ese email ya existe», el formulario de alta se convertiría
en un verificador de cuentas que cualquiera puede recorrer. Y tampoco
el reloj: contra un correo desconocido se verifica igual contra un
hash de relleno, porque responder en 2 ms cuando no existe y en 250 ms
cuando existe cuenta lo mismo que decirlo.

LAS DOS PIEZAS DE UNA SESIÓN

- El **token de acceso** es un JWT de una hora. Se verifica con la
  clave pública, sin tocar la base: es rápido y no se puede revocar.
- El **token de renovación** es azar puro, dura 30 días, vive hasheado
  en una tabla y **se quema al usarse**. Es lo que se puede cortar.

La rotación es lo que hace que robar un token de renovación no alcance
para quedarse adentro para siempre: en cuanto el legítimo renueva, el
robado deja de servir, y si el robado se usa primero, el legítimo
dispara la detección y se cae la cadena entera.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from dataclasses import dataclass

from fastapi import status
from sqlalchemy.orm import Session

from ..core import claves
from ..core.errors import CONFLICT, UNAUTHENTICATED, VALIDATION_ERROR, ErrorDeApi
from ..core.security import emitir_acceso
from ..repos import auth as repo

log = logging.getLogger("epic_wallet")

# Treinta días. Es cuánto puede estar sin abrir la aplicación alguien
# que la usa de vez en cuando sin que le pida la contraseña de nuevo.
DIAS_DE_RENOVACION = 30

# El mismo texto para los dos casos. Está acá, una sola vez, para que
# no se pueda separar sin querer en un cambio futuro.
CREDENCIALES = "El email o la contraseña no son correctos."


@dataclass(frozen=True)
class Sesion:
    """Lo que se le devuelve a quien entra."""

    usuario_id: str
    email: str
    token_de_acceso: str
    vence_en: int
    token_de_renovacion: str


def _sin_sesion(detalle: str) -> ErrorDeApi:
    return ErrorDeApi(status.HTTP_401_UNAUTHORIZED, UNAUTHENTICATED, detalle)


def _emitir(sesion: Session, *, uid: str, correo: str, familia: str | None) -> Sesion:
    """Arma el par de tokens y deja el de renovación guardado."""
    acceso, vigencia = emitir_acceso(uid, correo)

    renovacion = claves.generar_token_opaco()
    repo.guardar_renovacion(
        sesion,
        user_id=uid,
        huella=claves.huella(renovacion),
        familia=familia or str(uuid.uuid4()),
        vence=dt.datetime.now(dt.UTC) + dt.timedelta(days=DIAS_DE_RENOVACION),
    )

    return Sesion(
        usuario_id=uid,
        email=correo,
        token_de_acceso=acceso,
        vence_en=vigencia,
        token_de_renovacion=renovacion,
    )


# ===================================================================
#  Registrarse
# ===================================================================


def registrar(sesion: Session, correo: str, clave: str) -> Sesion:
    """Crea la cuenta y la deja adentro.

    El correo ya viene validado por Pydantic. De la contraseña se
    comprueba acá el largo, porque el mensaje tiene que poder decir
    cuál es el mínimo.
    """
    motivo = claves.clave_invalida(clave)
    if motivo:
        raise ErrorDeApi(status.HTTP_400_BAD_REQUEST, VALIDATION_ERROR, motivo)

    if repo.buscar_por_correo(sesion, correo) is not None:
        # 409 con un mensaje que no confirma nada. Que el código sea
        # CONFLICT es inevitable —el correo es único y hay que decir
        # algo—, pero el texto no dice «ya existe esa cuenta».
        raise ErrorDeApi(
            status.HTTP_409_CONFLICT,
            CONFLICT,
            "No se pudo crear la cuenta con esos datos.",
        )

    uid = repo.crear_usuario(sesion, correo, claves.hashear_clave(clave))
    # Sin flush, el trigger que crea el perfil y las 21 categorías no
    # corrió todavía y la cuenta entraría a un tablero que no existe.
    sesion.flush()

    log.info("Cuenta creada: %s", uid)
    return _emitir(sesion, uid=uid, correo=correo.strip().lower(), familia=None)


# ===================================================================
#  Entrar
# ===================================================================


def ingresar(sesion: Session, correo: str, clave: str) -> Sesion:
    """Comprueba la contraseña y abre una sesión nueva."""
    usuario = repo.buscar_por_correo(sesion, correo)

    if usuario is None:
        # Se gasta el mismo tiempo que si existiera. Sin esto, medir
        # cuánto tarda la respuesta diría qué correos tienen cuenta.
        claves.gastar_el_mismo_tiempo()
        raise _sin_sesion(CREDENCIALES)

    if not claves.verificar_clave(clave, usuario.hash_de_clave):
        log.info("Contraseña incorrecta para %s", usuario.id)
        raise _sin_sesion(CREDENCIALES)

    return _emitir(sesion, uid=usuario.id, correo=usuario.email, familia=None)


# ===================================================================
#  Renovar
# ===================================================================


def renovar(sesion: Session, token: str) -> Sesion:
    """Canjea un token de renovación por un par nuevo.

    El caso que importa es el tercero: un token **ya usado** que vuelve
    a aparecer. Puede ser el legítimo que llega tarde o una copia; no
    hay forma de distinguirlos, así que se corta la familia entera y
    los dos vuelven a entrar con la contraseña. Sólo uno la sabe.
    """
    fila = repo.buscar_renovacion(sesion, claves.huella(token))

    if fila is None:
        raise _sin_sesion("La sesión no es válida.")

    if fila.usado:
        cortados = repo.revocar_familia(sesion, fila.familia, "token repetido")
        log.warning(
            "Token de renovación repetido para %s: se cortaron %s de su cadena",
            fila.user_id,
            cortados,
        )
        raise _sin_sesion("La sesión no es válida.")

    if fila.revocado:
        raise _sin_sesion("La sesión no es válida.")

    if fila.vencido:
        raise _sin_sesion("La sesión expiró.")

    usuario = repo.buscar_por_id(sesion, fila.user_id)
    if usuario is None:
        # La cuenta se borró con la sesión abierta.
        raise _sin_sesion("La sesión no es válida.")

    repo.marcar_usada(sesion, fila.id)
    return _emitir(sesion, uid=usuario.id, correo=usuario.email, familia=fila.familia)


# ===================================================================
#  Salir
# ===================================================================


def salir(sesion: Session, token: str | None) -> None:
    """Corta la cadena de esa sesión.

    No se queja si el token no existe o ya estaba cortado: «cerrar
    sesión» tiene que terminar bien siempre. Un error acá dejaría al
    usuario con la pantalla trabada y la sesión abierta, que es
    exactamente lo contrario de lo que pidió.

    El token de acceso que tenga en mano sigue valiendo hasta una hora.
    Es el costo de no consultar la base en cada petición; el frontend
    lo borra al salir, así que en la práctica muere ahí.
    """
    if not token:
        return
    fila = repo.buscar_renovacion(sesion, claves.huella(token))
    if fila is None:
        return
    repo.revocar_familia(sesion, fila.familia, "cerró sesión")


def salir_de_todas(sesion: Session, user_id: str) -> int:
    """Corta todas las sesiones de una cuenta. Devuelve cuántas."""
    return repo.revocar_todas_las_del_usuario(sesion, user_id, "cerró todas")


# ===================================================================
#  Cambiar la contraseña
# ===================================================================


def cambiar_clave(sesion: Session, user_id: str, actual: str, nueva: str) -> Sesion:
    """Cambia la contraseña y devuelve una sesión nueva.

    Pide la actual aunque haya sesión abierta, y no es burocracia: sin
    eso, dejar el teléfono desbloqueado un minuto alcanzaría para que
    otro se quedara con la cuenta.

    Al cambiarla se caen **todas** las sesiones de la cuenta y se abre
    una sola, la de acá. Si alguien había entrado con la contraseña
    vieja, cambiarla tiene que echarlo; si no, cambiarla no serviría
    para lo único que sirve.
    """
    motivo = claves.clave_invalida(nueva)
    if motivo:
        raise ErrorDeApi(status.HTTP_400_BAD_REQUEST, VALIDATION_ERROR, motivo)

    usuario = repo.buscar_por_id(sesion, user_id)
    if usuario is None:
        raise _sin_sesion("La sesión no es válida.")

    if not claves.verificar_clave(actual, usuario.hash_de_clave):
        raise ErrorDeApi(
            status.HTTP_400_BAD_REQUEST,
            VALIDATION_ERROR,
            "La contraseña actual no es correcta.",
        )

    repo.cambiar_clave(sesion, user_id, claves.hashear_clave(nueva))
    repo.revocar_todas_las_del_usuario(sesion, user_id, "cambió la contraseña")
    log.info("Contraseña cambiada: %s", user_id)

    return _emitir(sesion, uid=usuario.id, correo=usuario.email, familia=None)

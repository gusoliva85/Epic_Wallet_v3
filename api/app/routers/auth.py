"""Endpoints de sesión · F17-T02.

Referencia: 02_Documento_Tecnico.md §8

**Este router es público**: se monta fuera del `APIRouter` que exige
`current_user_id`. Tiene que serlo —quien va a entrar todavía no tiene
token—, y es la única parte de la API que vive afuera de esa puerta.
Por eso cada endpoint de acá valida por su cuenta lo que los demás dan
por hecho.

La excepción es `PUT /api/auth/password`, que sí pide sesión: cambiar
la contraseña es algo que hace alguien que ya entró.

LOS NOMBRES DE LOS CAMPOS SON LOS DE ANTES

`access_token`, `refresh_token`, `expires_in`. No se renombraron al
castellano, aunque el resto del código lo esté: son el contrato con el
frontend, y mantenerlos es lo que permite reemplazar la librería del
proveedor sin tocar las pantallas.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..core.db import get_session
from ..core.security import UsuarioActual
from ..schemas.auth import (
    CambioDeClave,
    Credenciales,
    Renovacion,
    RespuestaDeSesion,
    Salida,
    UsuarioDeLaSesion,
)
from ..services import sesiones

router = APIRouter(prefix="/auth", tags=["sesión"])

Db = Annotated[Session, Depends(get_session)]


def _respuesta(s: sesiones.Sesion) -> RespuestaDeSesion:
    return RespuestaDeSesion(
        access_token=s.token_de_acceso,
        refresh_token=s.token_de_renovacion,
        expires_in=s.vence_en,
        user=UsuarioDeLaSesion(id=s.usuario_id, email=s.email),
    )


@router.post(
    "/signup",
    response_model=RespuestaDeSesion,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una cuenta y entrar",
)
def signup(datos: Credenciales, db: Db) -> RespuestaDeSesion:
    """Da de alta la cuenta y la deja adentro.

    No hay confirmación por correo porque no hay correo: el servidor no
    manda mensajes a propósito (General §48.1). La cuenta queda usable
    en el acto, con su perfil y sus 21 categorías creados por el
    trigger de la base.
    """
    return _respuesta(sesiones.registrar(db, datos.email, datos.password))


@router.post(
    "/login",
    response_model=RespuestaDeSesion,
    summary="Entrar",
)
def login(datos: Credenciales, db: Db) -> RespuestaDeSesion:
    return _respuesta(sesiones.ingresar(db, datos.email, datos.password))


@router.post(
    "/refresh",
    response_model=RespuestaDeSesion,
    summary="Renovar la sesión",
)
def refresh(datos: Renovacion, db: Db) -> RespuestaDeSesion:
    """Canjea el token de renovación por un par nuevo.

    El viejo se quema. Si vuelve a aparecer, se corta la cadena entera:
    el detalle está en `services/sesiones.py`.
    """
    return _respuesta(sesiones.renovar(db, datos.refresh_token))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión",
)
def logout(datos: Salida, db: Db) -> None:
    """Siempre devuelve 204, haya o no algo que cortar.

    Cerrar sesión no puede fallar: un error acá dejaría a la persona
    con la pantalla trabada y la sesión abierta.
    """
    sesiones.salir(db, datos.refresh_token)


@router.put(
    "/password",
    response_model=RespuestaDeSesion,
    summary="Cambiar la contraseña",
)
def cambiar_password(datos: CambioDeClave, usuario: UsuarioActual, db: Db) -> RespuestaDeSesion:
    """Pide la contraseña actual y devuelve una sesión nueva.

    Todas las demás sesiones de la cuenta se caen. Es el punto de
    cambiar una contraseña: si alguien había entrado con la vieja,
    tiene que quedar afuera.
    """
    return _respuesta(
        sesiones.cambiar_clave(db, usuario, datos.current_password, datos.new_password)
    )

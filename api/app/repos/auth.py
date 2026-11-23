"""Consultas de identidad y sesión · F17-T02.

Dos tablas: `auth.users`, que desde F16-T01 es nuestra, y
`refresh_tokens`, que crea F17-T02.

TODO ESTO CORRE CON EL ROL DUEÑO

Los endpoints de `/api/auth` usan `get_session()`, no
`sesion_de_usuario()`: cuando alguien manda su contraseña todavía no
hay usuario, así que no hay `auth.uid()` que poner y RLS no tendría
contra qué comparar. Es la única parte del backend que trabaja así, y
por eso cada función de acá filtra a mano por el usuario que
corresponde. La red de RLS no está debajo.

`auth.users` se consulta con SQL escrito, no con un modelo. No hay
modelo completo de esa tabla a propósito: declarar sus columnas en
SQLAlchemy invitaría a que `autogenerate` quisiera migrarla, y es la
tabla que menos conviene que una migración automática toque.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import CursorResult, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class UsuarioGuardado:
    """Lo que la base sabe de una cuenta."""

    id: str
    email: str
    hash_de_clave: str


# ===================================================================
#  auth.users
# ===================================================================


def _cuantas(resultado: object) -> int:
    """Cuántas filas tocó un update o un delete.

    `Session.execute` está tipado como `Result`, que no promete
    `rowcount` porque un `select` no lo tiene. Para un `update` sí
    llega un `CursorResult`, que sí. El cast es para el verificador de
    tipos, no para el intérprete.
    """
    return int(cast("CursorResult[Any]", resultado).rowcount or 0)


def _normalizar(correo: str) -> str:
    """El correo como se guarda y como se busca.

    Minúsculas y sin espacios alrededor. Si no se normalizara al
    buscar, quien se registró con `Gustavo@…` no entraría escribiendo
    `gustavo@…`, que es lo que el teclado del teléfono manda por su
    cuenta con la primera letra en mayúscula.
    """
    return correo.strip().lower()


def buscar_por_correo(sesion: Session, correo: str) -> UsuarioGuardado | None:
    """La cuenta de ese correo, o `None`."""
    fila = sesion.execute(
        text(
            "select id::text, email, encrypted_password "
            "from auth.users where lower(email) = :correo"
        ),
        {"correo": _normalizar(correo)},
    ).first()
    if fila is None:
        return None
    return UsuarioGuardado(id=fila[0], email=fila[1], hash_de_clave=fila[2] or "")


def buscar_por_id(sesion: Session, uid: str) -> UsuarioGuardado | None:
    fila = sesion.execute(
        text("select id::text, email, encrypted_password from auth.users where id = :id"),
        {"id": uid},
    ).first()
    if fila is None:
        return None
    return UsuarioGuardado(id=fila[0], email=fila[1], hash_de_clave=fila[2] or "")


def crear_usuario(sesion: Session, correo: str, hash_de_clave: str) -> str:
    """Da de alta la cuenta y devuelve su uuid.

    Sólo inserta en `auth.users`. El perfil y las 21 categorías los
    crea el trigger `crear_perfil_y_categorias` de F02-T04, igual que
    siempre: esta función no sabe que existen y no tiene por qué.

    `email_confirmed_at` va con fecha porque no hay confirmación por
    correo —no hay correo—. La columna se mantiene por compatibilidad
    con los datos que vienen del proveedor anterior.
    """
    uid = str(uuid.uuid4())
    sesion.execute(
        text(
            "insert into auth.users (id, email, encrypted_password, email_confirmed_at) "
            "values (:id, :correo, :hash, now())"
        ),
        {"id": uid, "correo": _normalizar(correo), "hash": hash_de_clave},
    )
    return uid


def cambiar_clave(sesion: Session, uid: str, hash_de_clave: str) -> None:
    sesion.execute(
        text("update auth.users set encrypted_password = :hash where id = :id"),
        {"hash": hash_de_clave, "id": uid},
    )


# ===================================================================
#  refresh_tokens
# ===================================================================


@dataclass(frozen=True)
class Renovacion:
    """Una fila de `refresh_tokens`, ya juzgada."""

    id: str
    user_id: str
    familia: str
    vencido: bool
    usado: bool
    revocado: bool

    @property
    def sirve(self) -> bool:
        return not (self.vencido or self.usado or self.revocado)


def guardar_renovacion(
    sesion: Session,
    *,
    user_id: str,
    huella: str,
    familia: str,
    vence: dt.datetime,
) -> None:
    sesion.execute(
        text(
            "insert into refresh_tokens (user_id, token_hash, familia, expires_at) "
            "values (:uid, :huella, :familia, :vence)"
        ),
        {"uid": user_id, "huella": huella, "familia": familia, "vence": vence},
    )


def buscar_renovacion(sesion: Session, huella: str) -> Renovacion | None:
    """La fila de esa huella, con el veredicto ya calculado.

    El vencimiento lo decide la base y no Python: así no depende del
    reloj del proceso, que en un contenedor puede estar en otra zona.
    """
    fila = sesion.execute(
        text(
            "select id::text, user_id::text, familia::text, "
            "       expires_at <= now() as vencido, "
            "       used_at is not null as usado, "
            "       revoked_at is not null as revocado "
            "from refresh_tokens where token_hash = :huella"
        ),
        {"huella": huella},
    ).first()
    if fila is None:
        return None
    return Renovacion(
        id=fila[0],
        user_id=fila[1],
        familia=fila[2],
        vencido=bool(fila[3]),
        usado=bool(fila[4]),
        revocado=bool(fila[5]),
    )


def marcar_usada(sesion: Session, id_renovacion: str) -> None:
    sesion.execute(
        text("update refresh_tokens set used_at = now() where id = :id"),
        {"id": id_renovacion},
    )


def revocar_familia(sesion: Session, familia: str, motivo: str) -> int:
    """Corta todos los tokens vivos de una cadena. Devuelve cuántos.

    Es lo que corre cuando aparece un token ya usado: no se puede
    saber si el legítimo es quien lo presenta o quien lo copió, así
    que se cae la cadena entera y la persona vuelve a entrar con su
    contraseña. Las otras sesiones del mismo usuario —el teléfono, por
    ejemplo— tienen otra familia y no se tocan.
    """
    resultado = sesion.execute(
        text(
            "update refresh_tokens set revoked_at = now(), revoked_reason = :motivo "
            "where familia = :familia and revoked_at is null"
        ),
        {"familia": familia, "motivo": motivo},
    )
    return _cuantas(resultado)


def revocar_todas_las_del_usuario(sesion: Session, user_id: str, motivo: str) -> int:
    resultado = sesion.execute(
        text(
            "update refresh_tokens set revoked_at = now(), revoked_reason = :motivo "
            "where user_id = :uid and revoked_at is null"
        ),
        {"uid": user_id, "motivo": motivo},
    )
    return _cuantas(resultado)


def borrar_vencidas(sesion: Session, dias_de_gracia: int = 7) -> int:
    """Limpia las filas que ya no pueden servir para nada.

    Con días de gracia porque una fila usada o revocada todavía dice
    algo mientras se investiga una sesión caída; pasada la semana, es
    basura que hace crecer un índice.
    """
    resultado = sesion.execute(
        text("delete from refresh_tokens where expires_at < now() - make_interval(days => :dias)"),
        {"dias": dias_de_gracia},
    )
    return _cuantas(resultado)


# ===================================================================
#  password_resets · F17-T04
# ===================================================================


@dataclass(frozen=True)
class Recuperacion:
    """Una fila de `password_resets`, ya juzgada."""

    id: str
    user_id: str
    vencido: bool
    usado: bool

    @property
    def sirve(self) -> bool:
        return not (self.vencido or self.usado)


def guardar_recuperacion(sesion: Session, *, user_id: str, huella: str, vence: dt.datetime) -> None:
    sesion.execute(
        text(
            "insert into password_resets (user_id, token_hash, expires_at) "
            "values (:uid, :huella, :vence)"
        ),
        {"uid": user_id, "huella": huella, "vence": vence},
    )


def anular_recuperaciones(sesion: Session, user_id: str) -> int:
    """Quema los enlaces anteriores de esa cuenta.

    Pedir un enlace nuevo invalida el viejo. Si no, cada pedido dejaría
    otra llave viva durante media hora, y pedir tres veces porque el
    primero no llegó multiplicaría las puertas abiertas en vez de
    reemplazarlas.
    """
    return _cuantas(
        sesion.execute(
            text(
                "update password_resets set used_at = now() "
                "where user_id = :uid and used_at is null"
            ),
            {"uid": user_id},
        )
    )


def buscar_recuperacion(sesion: Session, huella: str) -> Recuperacion | None:
    fila = sesion.execute(
        text(
            "select id::text, user_id::text, "
            "       expires_at <= now() as vencido, "
            "       used_at is not null as usado "
            "from password_resets where token_hash = :huella"
        ),
        {"huella": huella},
    ).first()
    if fila is None:
        return None
    return Recuperacion(id=fila[0], user_id=fila[1], vencido=bool(fila[2]), usado=bool(fila[3]))


def quemar_recuperacion(sesion: Session, id_recuperacion: str) -> None:
    sesion.execute(
        text("update password_resets set used_at = now() where id = :id"),
        {"id": id_recuperacion},
    )

"""Tokens de renovación · F17-T02.

Referencia: 02_Documento_Tecnico.md §8

El token de acceso dura una hora y no se puede revocar: se verifica con
la clave pública, sin preguntarle a nadie. Lo que mantiene una sesión
viva durante treinta días —y lo que permite cortarla— es esta tabla.

ROTACIÓN, Y POR QUÉ IMPORTA LA FAMILIA

Cada renovación quema el token usado y emite uno nuevo. Si un token ya
usado vuelve a aparecer, hay dos posibilidades y ninguna es buena: o
alguien copió el token, o lo copiaron y ya lo usó. No se puede saber
cuál de los dos tiene el legítimo, así que **se cortan todos los de esa
cadena**: la persona vuelve a entrar con su contraseña y quien robó el
token se queda afuera.

`familia` es lo que hace posible ese corte. Es el mismo uuid para todos
los tokens que descienden del login original, así que revocar la
cadena entera es un `update` por ese campo. Sin eso habría que seguir
una lista enlazada hacia atrás, o revocar todas las sesiones del
usuario —incluida la del teléfono que no tuvo nada que ver—.

NO SE GUARDA EL TOKEN

Se guarda su SHA-256. Quien se lleve la tabla se lleva huellas: no
puede renovar ninguna sesión. El índice único sobre esa huella es lo
que hace que buscarlo sea una lectura y no un barrido.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RefreshToken(Base):
    """Una renovación posible de una sesión."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # El SHA-256 del token en hexadecimal: 64 caracteres fijos.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Todos los tokens que vienen del mismo login comparten familia.
    familia: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Cuándo se canjeó. Con fecha acá, el token ya no sirve: volver a
    # presentarlo es la señal de que algo se copió.
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Cuándo se cortó, y por qué. El motivo se guarda porque es lo
    # único que después explica una sesión caída: «cerraste sesión» y
    # «se detectó un token repetido» se ven igual desde el teléfono.
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Las dos consultas que existen: renovar busca por familia para
        # cortarla, y la limpieza busca por usuario.
        Index("ix_refresh_tokens_familia", "familia"),
        Index("ix_refresh_tokens_user_id", "user_id"),
    )

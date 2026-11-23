"""Enlaces de contraseña nueva · F17-T04.

Referencia: 01_Documento_General.md §48.1

No hay correo saliente en este proyecto, a propósito. El enlace lo
genera Gustavo con `python -m app.cli recuperar <email>` y se lo
entrega a la persona por donde pueda. Esta tabla es lo que hace que
ese enlace valga una sola vez y por poco rato.

POR QUÉ NO ES MÁS DÉBIL QUE EL CORREO

Un «te mandamos un link a tu email» no protege la cuenta: traslada la
protección al buzón. Quien entra a tu correo entra a todo lo que se
recupera por correo, y además lo hace solo, a cualquier hora, sin que
nadie se entere. Acá no existe esa puerta: **no hay ningún endpoint
que cualquiera pueda llamar para que se emita un enlace.** Hay que
pedírselo a una persona que tiene que entrar al servidor.

Lo que sí hay que cuidar es el canal por donde se entrega y la ventana
de media hora. De eso se ocupan las columnas de abajo.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PasswordReset(Base):
    """Un enlace de contraseña nueva, de un solo uso."""

    __tablename__ = "password_resets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # El SHA-256 del token. El token en claro existe en una sola
    # pantalla —la del terminal donde se generó— y en ningún archivo.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Cuándo se quemó. Con fecha acá, el enlace ya no sirve.
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_password_resets_user_id", "user_id"),)

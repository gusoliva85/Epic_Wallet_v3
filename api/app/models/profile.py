"""Perfil del usuario · F02-T03.

Referencia: 02_Documento_Tecnico.md §6.2

`profiles` extiende `auth.users`: la identidad —correo, contraseña,
confirmación— vive ahí y acá sólo lo que es de la aplicación. La clave
primaria **es** el uuid de `auth.users`, no una propia: así no hay dos
identificadores del mismo usuario que puedan desincronizarse.

Las dos tablas son nuestras desde F16-T01; `auth.users` está en su
propio esquema porque así venía de la versión anterior, y se dejó ahí
para que los datos entren sin reescribir ninguna referencia.

`on delete cascade` sobre esa referencia es lo que hace que borrar una
cuenta se lleve sus datos, incluso borrándola desde SQL. Sin eso
quedarían filas huérfanas apuntando a un usuario que ya no existe.

Nota: este modelo no crea tablas. Las crea Alembic contra Postgres; acá
sirve para consultar y para que `autogenerate` tenga con qué comparar.
"""

from __future__ import annotations

import datetime as dt
import decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

# La aplicación razona siempre en hora argentina: con la zona del
# dispositivo, un movimiento del día 1 o del 31 cae en otro mes.
ZONA_POR_DEFECTO = "America/Argentina/Buenos_Aires"


class Profile(Base):
    """Datos de la aplicación para un usuario de `auth.users`."""

    __tablename__ = "profiles"

    # La referencia cruza al esquema `auth`. Alembic no lo compara en
    # el autogenerate (ver `incluir_objeto` en migrations/env.py): sólo
    # apunta.
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Lo deriva del correo el trigger de F02-T04. Único, porque es lo
    # que se muestra cuando no hay nombre visible cargado.
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(Text)

    # El punto de partida del ahorro: lo que había antes de que la
    # aplicación existiera. `numeric(14,2)` y no float, que redondea mal
    # en cuanto hay plata de por medio.
    opening_balance: Mapped[decimal.Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )

    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=ZONA_POR_DEFECTO
    )

    # Se desactiva, no se borra: borrarlo se llevaría todo el histórico
    # por la cascada.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Lo mantiene al día un trigger y no la aplicación: así también
    # cambia cuando una fila se toca desde SQL o desde el panel.
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Profile {self.username} ({self.id})>"

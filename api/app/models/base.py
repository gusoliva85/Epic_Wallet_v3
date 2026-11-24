"""Base declarativa y metadatos de SQLAlchemy.

El esquema sale de la variable de entorno DB_SCHEMA, y hoy es
siempre `public`: el proyecto usa un solo esquema
(02_Documento_Tecnico §4.1.1). Lo que separa los datos de prueba de
los reales es la **base**, no el esquema: las pruebas corren contra
`epic_wallet_test` y se niegan a arrancar si el nombre no lo dice.

En SQLite (sólo tests) no hay esquemas, así que el valor es None.
"""

from __future__ import annotations

import os

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Convención de nombres para índices y restricciones. Sin esto, los
# nombres los inventa el motor y `alembic revision --autogenerate`
# produce migraciones distintas en cada máquina.
CONVENCION_DE_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def esquema_actual() -> str | None:
    """Esquema donde viven las tablas, o None si el motor no los soporta."""
    url = os.getenv("DATABASE_URL", "")
    if url.startswith("sqlite"):
        return None
    esquema = os.getenv("DB_SCHEMA", "public").strip()
    return esquema or "public"


metadata = MetaData(naming_convention=CONVENCION_DE_NOMBRES, schema=esquema_actual())


class Base(DeclarativeBase):
    """Clase padre de todos los modelos del proyecto."""

    metadata = metadata

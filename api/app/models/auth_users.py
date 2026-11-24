"""La columna de `auth.users` a la que apunta `profiles` · F16-T01.

`auth.users` es **nuestra** desde F16-T01: la crea una migración de
este repositorio y la llena el alta de `/api/auth/signup`. Antes era de
un proveedor externo, y de ahí viene que esté en su propio esquema
`auth` y no en `public`; se dejó ahí para que los datos de la versión
anterior entren sin reescribir ninguna referencia.

Acá se declara **sólo lo imprescindible**: la columna a la que apunta
`profiles.id`. El modelo completo no existe a propósito —la tabla se
consulta con SQL explícito en `repos/auth.py`, que es el único lugar
que la toca—.

Por qué hace falta declararla: SQLAlchemy necesita conocer la tabla
destino de una clave foránea para resolver el orden de las operaciones
al guardar. Sin esto, cualquier `UPDATE` sobre `profiles` falla con
«could not find table 'auth.users'» — y falla en tiempo de ejecución,
no al arrancar, así que el primer `PATCH /api/me` se encuentra con un
500 que no dice nada de lo que pasa.
"""

from __future__ import annotations

import os

from sqlalchemy import Column, Table
from sqlalchemy.dialects.postgresql import UUID

from .base import metadata

# Se decide por el MOTOR, no por `esquema_actual()`: esa función
# devuelve None también cuando `DB_SCHEMA` no está en el entorno del
# proceso —algo normal al correr las pruebas, que leen la
# configuración del .env por otro camino—, y entonces la tabla no se
# declaraba y el error volvía.
#
# En SQLite no hay esquemas ni clave foránea, así que no falta.
_es_sqlite = os.getenv("DATABASE_URL", "").startswith("sqlite")

usuarios: Table | None = None

if not _es_sqlite:
    usuarios = Table(
        "users",
        metadata,
        Column("id", UUID(as_uuid=False), primary_key=True),
        schema="auth",
    )

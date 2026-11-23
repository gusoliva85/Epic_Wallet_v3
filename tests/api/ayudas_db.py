"""Transacciones de lectura y escritura para las pruebas · F16-T03.

El `reset role` va **dentro** de la transacción, y eso es lo único que
hace este archivo.

POR QUÉ, Y CÓMO SE APRENDIÓ

Las conexiones se reusan entre transacciones. Si alguien deja un
`set role` de sesión puesto, esa conexión vuelve al pool con el rol
cambiado y se la entrega a quien siga.

Pasó de verdad mientras se escribía F02-T05: una prueba de mutación
cambió `set local role` por `set role` para comprobar que la diferencia
importa, y dejó **todas** las conexiones del proyecto como
`authenticated`. Las pruebas siguientes fallaban con «permission denied
for table users» sin que nada estuviera mal en el código.

`api/app/core/db.py` se defiende solo desde entonces. Esto hace lo
mismo para las pruebas, que abren sus propias conexiones.

El motor está en `entorno.py`, junto con el resto de lo compartido.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, text


@contextmanager
def lectura(motor: Engine) -> Iterator[Any]:
    """Transacción de sólo lectura con el rol de la aplicación."""
    with motor.begin() as con:
        con.execute(text("reset role"))
        yield con


@contextmanager
def escritura(motor: Engine) -> Iterator[Any]:
    """Igual que `lectura`, pero el nombre dice que modifica."""
    with motor.begin() as con:
        con.execute(text("reset role"))
        yield con

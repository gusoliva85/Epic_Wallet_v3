"""Qué dice el último respaldo · F18-T04.

`scripts/respaldo.sh` deja una constancia en `respaldos/ultimo.json`
**después** de verificar el archivo: fecha, tablas, bytes y
`verificado: true`. Este módulo la lee y la juzga.

POR QUÉ ESTO EXISTE

`CLAUDE.md` dice «respaldo primero» desde que el proyecto arrancó, y
es la regla que protege años de contabilidad. Pero una regla escrita
depende de que alguien se acuerde a las once de la noche, y migrar es
la única operación del proyecto que no tiene vuelta atrás salvo por
otro respaldo. Acá la regla deja de depender de la memoria: si no hay
un respaldo fresco y verificado, `migrations/env.py` no migra.

Lo lee también `/api/health` (F18-T06) para avisar cuando hace días
que el respaldo no corre.

TODO ACÁ ES UNA FUNCIÓN PURA

`evaluar()` recibe la constancia y el momento, y no toca disco ni
reloj. Así la decisión —la parte que puede dejar pasar una migración
sin red— se prueba sin montar nada.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Cuántas horas puede tener el respaldo para que migrar siga siendo
# seguro.
#
# Tres, y no veinticuatro, a propósito. El respaldo nocturno corre a
# las 3:15; si alcanzara con ese, migrar a las once de la noche
# significaría poder perder veinte horas de carga. Lo que esta regla
# exige es el respaldo que se toma **en el momento**, que es lo que
# siempre dijo el procedimiento:
#
#     ./scripts/respaldo.sh && alembic upgrade head
MAXIMO_DE_HORAS = 3.0

# Las bases donde migrar no pone nada en riesgo. Si el nombre dice
# que es descartable, no hace falta respaldo.
DESCARTABLES = ("test", "prueba", "restaurado")


@dataclass(frozen=True)
class Veredicto:
    """Si se puede migrar, y por qué no si no se puede."""

    hay_red: bool
    motivo: str
    horas: float | None = None


def ruta_de_respaldos() -> Path:
    """Dónde están los respaldos en esta máquina.

    En el contenedor de la api, `/respaldos` montado de sólo lectura.
    En una máquina de desarrollo, la carpeta del proyecto.
    """
    desde_entorno = os.getenv("RESPALDOS_DIR", "").strip()
    if desde_entorno:
        return Path(desde_entorno)
    return Path(__file__).resolve().parents[3] / "respaldos"


def leer_constancia(carpeta: Path | None = None) -> dict[str, Any] | None:
    """La constancia del último respaldo, o `None` si no hay o no se lee.

    Un archivo ilegible se trata igual que uno ausente: no se levanta
    ningún error. Que no haya constancia no es una falla de este
    módulo, es exactamente lo que el portón tiene que detectar.
    """
    carpeta = carpeta or ruta_de_respaldos()
    try:
        texto = (carpeta / "ultimo.json").read_text(encoding="utf-8")
        datos = json.loads(texto)
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def es_descartable(url_o_nombre: str) -> bool:
    """Que el nombre de la base diga que se puede romper sin consecuencias."""
    nombre = url_o_nombre.rsplit("/", 1)[-1].split("?")[0].lower()
    return any(palabra in nombre for palabra in DESCARTABLES)


def evaluar(
    constancia: dict[str, Any] | None,
    ahora: datetime,
    maximo_de_horas: float = MAXIMO_DE_HORAS,
) -> Veredicto:
    """Decide si hay una red debajo para migrar.

    Se exigen tres cosas, y las tres por separado porque fallan por
    motivos distintos: que haya constancia, que diga `verificado`, y
    que sea reciente. Una constancia de un respaldo que no se pudo
    abrir es peor que ninguna: da tranquilidad sin darla.
    """
    if not constancia:
        return Veredicto(False, "no hay ninguna constancia de respaldo")

    if constancia.get("verificado") is not True:
        return Veredicto(False, "el último respaldo no quedó verificado")

    crudo = str(constancia.get("fecha", "")).strip()
    if not crudo:
        return Veredicto(False, "la constancia no dice cuándo se tomó")
    try:
        fecha = datetime.fromisoformat(crudo)
    except ValueError:
        return Veredicto(False, f"la constancia tiene una fecha ilegible: {crudo!r}")

    # Una constancia sin zona horaria se lee como UTC. Es una
    # suposición, pero la alternativa —compararla contra un momento
    # con zona— explota, y `respaldo.sh` siempre escribe la zona.
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=UTC)

    horas = (ahora - fecha).total_seconds() / 3600

    # Una fecha en el futuro significa un reloj mal puesto, de este
    # lado o del otro. No se da por bueno: el respaldo podría ser de
    # cualquier momento.
    if horas < -0.5:
        return Veredicto(
            False,
            f"la constancia dice que el respaldo es de dentro de "
            f"{abs(horas):.1f} h. Hay un reloj mal puesto",
            horas,
        )

    if horas > maximo_de_horas:
        return Veredicto(
            False,
            f"el último respaldo tiene {horas:.1f} h y se admiten hasta {maximo_de_horas:.0f}",
            horas,
        )

    return Veredicto(True, f"respaldo verificado de hace {max(horas, 0):.1f} h", horas)

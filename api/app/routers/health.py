"""Endpoint de salud. El único público de toda la API.

Sirve para dos cosas: comprobar que el despliegue vive, y saber de un
vistazo **contra qué esquema está corriendo** cada entorno, que es lo
que pide F00-T09 para distinguir una preview de producción.

Referencia: 02_Documento_Tecnico.md §9.1
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.db import revisar_conexion
from ..core.respaldos import MAXIMO_PARA_AVISAR, evaluar, leer_constancia

router = APIRouter(tags=["salud"])


class EstadoDeBase(BaseModel):
    status: str = Field(description="connected | error")
    latency_ms: float = Field(description="Cuánto tardó la comprobación")
    schema_exists: bool | None = Field(
        default=None, description="Si el esquema configurado existe. None en SQLite."
    )
    reason: str | None = Field(default=None, description="Tipo de error, si falló")


class UltimoRespaldo(BaseModel):
    """Qué dice la constancia que dejó `scripts/respaldo.sh` · F18-T06."""

    at: str | None = Field(default=None, description="Cuándo se tomó, en ISO 8601")
    verified: bool = Field(default=False, description="Si el archivo se abrió y traía tablas")
    hours_ago: float | None = Field(default=None, description="Antigüedad en horas")
    up_to_date: bool = Field(default=False, description=f"Si tiene menos de {MAXIMO_PARA_AVISAR} h")
    reason: str | None = Field(default=None, description="Por qué no está al día, si no lo está")


class Salud(BaseModel):
    status: str = Field(description="ok | degraded")
    version: str
    environment: str
    db_schema: str | None = Field(description="Esquema activo: dev o public")
    timezone: str
    database: EstadoDeBase
    last_backup: UltimoRespaldo
    warnings: list[str] = Field(default_factory=list)


def _revisar_respaldo() -> tuple[dict[str, Any], str | None]:
    """El estado del último respaldo y el aviso, si hay que darlo.

    **Un respaldo que falla en silencio es peor que ninguno**: el que
    no tiene respaldo lo sabe, y el que cree tenerlo se entera el día
    que necesita restaurar. Esto es lo que rompe el silencio.

    No cambia el `status` a `degraded`: la aplicación funciona
    perfectamente sin respaldo fresco. Lo que falta es la red, no el
    servicio, y confundir las dos cosas haría que un monitor externo
    avise de una caída que no pasó.
    """
    constancia = leer_constancia()
    veredicto = evaluar(constancia, datetime.now(UTC), maximo_de_horas=MAXIMO_PARA_AVISAR)

    estado = {
        "at": str(constancia.get("fecha")) if constancia else None,
        "verified": bool(constancia and constancia.get("verificado") is True),
        "hours_ago": round(veredicto.horas, 1) if veredicto.horas is not None else None,
        "up_to_date": veredicto.hay_red,
        "reason": None if veredicto.hay_red else veredicto.motivo,
    }
    if veredicto.hay_red:
        return estado, None
    return estado, f"RESPALDO: {veredicto.motivo}"


@router.get(
    "/health",
    response_model=Salud,
    summary="Estado del servicio",
    description=(
        "Público, sin autenticación. Informa versión, entorno, esquema activo y "
        "si la base responde. Devuelve 503 si la base no contesta, para que un "
        "monitor externo lo detecte."
    ),
)
async def salud(response: Response) -> dict[str, Any]:
    base = revisar_conexion()
    avisos = settings.validar_coherencia()

    if base["status"] != "connected":
        # Degradado, no caído: el servicio responde pero no puede trabajar.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        estado = "degraded"
    elif base.get("schema_exists") is False:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        estado = "degraded"
        avisos.append(f"el esquema '{settings.esquema}' no existe: faltan correr las migraciones")
    else:
        estado = "ok"

    respaldo, aviso = _revisar_respaldo()
    if aviso:
        avisos.append(aviso)

    return {
        "status": estado,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "db_schema": settings.esquema,
        "timezone": settings.APP_TIMEZONE,
        "database": base,
        "last_backup": respaldo,
        "warnings": avisos,
    }

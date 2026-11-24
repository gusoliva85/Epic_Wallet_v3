"""Configuración de la aplicación, leída del entorno.

Las variables vienen del entorno del contenedor en el servidor y de
.env en la máquina de desarrollo.
Ninguna tiene valor por defecto si es un secreto: si falta, la
aplicación no arranca, en lugar de arrancar a medias.

Referencia: 02_Documento_Tecnico.md §11
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

Entorno = Literal["development", "preview", "production"]

# Ruta absoluta al .env de la raíz: config.py está en api/app/core/.
# Relativa al directorio actual fallaría según desde dónde se arranque
# (uvicorn desde api/, pytest desde la raíz). En el contenedor no hay
# .env y las variables llegan por el entorno: que el archivo falte no
# es un problema.
RAIZ = Path(__file__).resolve().parents[3]
ARCHIVO_ENV = RAIZ / ".env"


class Settings(BaseSettings):
    """Configuración completa. Se valida una sola vez al arrancar."""

    model_config = SettingsConfigDict(
        env_file=ARCHIVO_ENV,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- base de datos ---
    DATABASE_URL: str
    # Un solo esquema para todo el proyecto. No hay entorno separado.
    DB_SCHEMA: str = "public"

    # --- firma de las sesiones · F17-T01 ---
    # Par de claves ES256 (curva P-256) del proyecto, en formato PEM.
    #
    # La PRIVADA firma, y es el secreto más caro del proyecto: quien la
    # tenga puede fabricar la sesión de cualquier usuario. No entra al
    # repositorio, no va al frontend y no sale del servidor.
    #
    # La PÚBLICA sólo verifica. Que sean distintas es el punto: este
    # backend comprueba sesiones y, hasta F17-T02, ni siquiera las
    # emite.
    #
    # Se aceptan con saltos de línea reales o escapados, que es como
    # sobreviven a un archivo de variables de entorno.
    JWT_PRIVATE_KEY: str = ""
    JWT_PUBLIC_KEY: str = ""

    # --- aplicación ---
    APP_ENV: Entorno = "development"
    APP_TIMEZONE: str = "America/Argentina/Buenos_Aires"
    ALLOWED_ORIGINS: str = ""
    LOG_LEVEL: str = "INFO"
    PUBLIC_APP_URL: str = ""

    # --- cotizaciones ---
    PRICE_PROVIDER_ORDER: str = "manual"
    PRICE_REFRESH_COOLDOWN_MINUTES: int = 15

    # --- versión, para poder identificar qué está desplegado ---
    APP_VERSION: str = "0.1.0"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def es_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def esquema(self) -> str | None:
        """Esquema donde viven las tablas. None en SQLite, que no los soporta."""
        if self.es_sqlite:
            return None
        return self.DB_SCHEMA.strip() or None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def origenes_permitidos(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def proveedores_de_precio(self) -> list[str]:
        return [p.strip() for p in self.PRICE_PROVIDER_ORDER.split(",") if p.strip()]

    @staticmethod
    def _pem(valor: str) -> str:
        """Devuelve la clave lista para que `cryptography` la lea.

        En un archivo de variables de entorno una clave PEM entra en
        una sola línea, con los saltos escapados. Acá se deshacen,
        porque el formato PEM los necesita de verdad.
        """
        return valor.replace("\\n", "\n").strip()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def clave_publica(self) -> str:
        """Con la que se verifican las sesiones."""
        return self._pem(self.JWT_PUBLIC_KEY)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def clave_privada(self) -> str:
        """Con la que se firman. Nunca se registra ni se devuelve."""
        return self._pem(self.JWT_PRIVATE_KEY)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def es_produccion(self) -> bool:
        return self.APP_ENV == "production"

    def validar_coherencia(self) -> list[str]:
        """Avisos de configuración sospechosa, sin impedir el arranque.

        Hasta F15 el primer aviso era el contrario: exigía el puerto
        6543, el del pooler en modo transacción. Ahora la API habla
        directo con su Postgres, así que lo normal es 5432 y lo raro
        sería lo otro.
        """
        avisos: list[str] = []
        if not self.clave_publica:
            avisos.append(
                "JWT_PUBLIC_KEY vacía: no hay con qué verificar las sesiones, "
                "así que ningún endpoint privado responde. Se genera con "
                "`python scripts/generar_claves.py`"
            )
        if self.es_produccion and not self.clave_privada:
            avisos.append(
                "JWT_PRIVATE_KEY vacía: el servidor todavía no puede emitir "
                "sesiones. Es lo esperado hasta F17-T02"
            )
        return avisos


@lru_cache
def get_settings() -> Settings:
    """Una sola instancia por proceso. `lru_cache` la memoriza."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

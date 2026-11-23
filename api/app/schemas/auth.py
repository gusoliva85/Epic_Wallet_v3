"""Lo que entra y sale de `/api/auth` · F17-T02.

POR QUÉ EL CORREO SE VALIDA A MANO Y NO CON `EmailStr`

`EmailStr` de Pydantic necesita el paquete `email-validator`, que
arrastra `dnspython`. Son dos dependencias más en la imagen para
comprobar algo que acá no decide nada: no hay correo de confirmación,
así que la aplicación nunca le escribe a esa dirección. Lo único que
importa es que sea un identificador razonable y único, y para eso
alcanza con mirar que tenga una arroba, un punto después y ningún
espacio. La verdad sobre si el correo existe la tiene la persona que
lo escribió.

LA CONTRASEÑA NO SE VALIDA ACÁ

El largo lo comprueba `services/sesiones.py`. Si lo hiciera Pydantic,
el error saldría como un 422 de validación con la forma de los errores
de campo, y la pantalla de ingreso tendría que manejar dos formas
distintas para el mismo problema. Además, un 422 en el **ingreso**
diría que la contraseña enviada es demasiado corta para ser de este
sistema, que es información de más.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Una arroba, algo antes, algo con un punto después, y nada de
# espacios. Deliberadamente laxo: rechazar correos válidos raros
# molesta más de lo que protege.
CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MAXIMO_DE_CORREO = 254  # el límite del RFC 5321


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EntradaConCorreo(_Base):
    email: str = Field(..., max_length=MAXIMO_DE_CORREO)

    @field_validator("email")
    @classmethod
    def _correo_valido(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if not CORREO.match(valor):
            raise ValueError("El email no parece una dirección válida.")
        return valor


class Credenciales(EntradaConCorreo):
    """Lo que manda el formulario de ingreso y el de alta."""

    password: str = Field(..., min_length=1, max_length=200)


class Renovacion(_Base):
    """El canje de un token de renovación."""

    refresh_token: str = Field(..., min_length=1, max_length=500)


class Salida(_Base):
    """Cerrar sesión. El token es opcional: sin él no hay nada que cortar."""

    refresh_token: str | None = Field(default=None, max_length=500)


class Restablecimiento(_Base):
    """El canje de un enlace de contraseña nueva.

    Se llama `token` y no `token_hash` como en la URL: en la barra de
    direcciones el nombre venía del proveedor anterior y la pantalla lo
    lee de ahí, pero lo que viaja es el token, no su hash.
    """

    token: str = Field(..., min_length=1, max_length=500)
    new_password: str = Field(..., min_length=1, max_length=200)


class CambioDeClave(_Base):
    current_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=1, max_length=200)


class UsuarioDeLaSesion(_Base):
    id: str
    email: str


class RespuestaDeSesion(_Base):
    """La sesión abierta.

    Los nombres son los que ya esperaba el frontend cuando los emitía
    el proveedor anterior —`access_token`, `refresh_token`,
    `expires_in`—, y eso es a propósito: `auth.js` cambia por dentro y
    las otras 50 pantallas no se enteran de nada.
    """

    access_token: str
    refresh_token: str
    expires_in: int
    # No es una contraseña: es el tipo de token que nombra el
    # el RFC 6750. Va fijo porque sólo emitimos de esta clase.
    token_type: str = "bearer"  # noqa: S105
    user: UsuarioDeLaSesion

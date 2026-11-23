"""Lo que comparten las pruebas de API · F16-T03.

QUÉ CAMBIÓ Y POR QUÉ

Hasta F16-T03, cada uno de estos archivos leía `SUPABASE_URL` y
`SUPABASE_ANON_KEY`, creaba sus cuentas llamando al servicio de
registro del proveedor y conseguía los tokens de ahí. O sea: **la
batería de pruebas le pegaba al servidor de producción con credenciales
reales**, y las cuentas que creaba y borraba vivían ahí.

Eso ya no pasa. Ahora:

- La base es local y se pasa por `TEST_DATABASE_URL`.
- Las cuentas se insertan en `auth.users`, que desde F16-T01 es una
  tabla nuestra. El trigger de la base les crea el perfil y las 21
  categorías igual que a una cuenta de verdad.
- Los tokens los firma esta misma batería, con un par de claves ES256
  que se genera al arrancar y vive en memoria. La aplicación los
  verifica con la pública, por el camino de F17-T01.

No queda una sola credencial externa, y ninguna prueba abre una
conexión a internet.

LA BASE DE PRUEBAS NO ES LA BASE DE NADIE

`TEST_DATABASE_URL` tiene que apuntar a una base **dedicada**. Estas
pruebas borran filas sin preguntar. Por eso `_comprobar_que_no_es_real`
se niega a correr si la URL no nombra una base de pruebas: el accidente
del 2026-11-10 —una prueba que borró el historial de dos cuentas
reales— empezó exactamente así, con una batería apuntada a donde no
debía.
"""

from __future__ import annotations

import os
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import Engine, create_engine, text

AUDIENCIA = "authenticated"
ALGORITMO = "ES256"

# El correo de toda cuenta que cree esta batería. `example.com` está
# reservado por la RFC 2606 justamente para esto, y las pruebas de RLS
# lo usan para no tocar ninguna cuenta que no sea descartable.
DOMINIO_DE_PRUEBA = "example.com"

ESQUEMA = os.getenv("DB_SCHEMA", "public").strip() or "public"


# ===================================================================
#  A qué base se apunta
# ===================================================================


def _url_de_pruebas() -> str | None:
    """La base contra la que corren estas pruebas.

    Sólo `TEST_DATABASE_URL`, y a propósito: si cayera por defecto en
    `DATABASE_URL`, un `pytest` distraído correría contra la base de
    trabajo y le borraría filas. Que haya que nombrarla explícitamente
    es la protección.
    """
    url = os.getenv("TEST_DATABASE_URL", "").strip()
    return url or None


def _parece_base_de_pruebas(url: str) -> bool:
    """Que el nombre de la base diga que es de pruebas."""
    nombre = url.rsplit("/", 1)[-1].split("?")[0].lower()
    return "test" in nombre or "prueba" in nombre


URL_BASE = _url_de_pruebas()

sin_entorno = pytest.mark.skipif(
    not URL_BASE or str(URL_BASE).startswith("sqlite"),
    reason=(
        "hace falta TEST_DATABASE_URL apuntando a una base Postgres de "
        "pruebas. Ver README · Pruebas"
    ),
)


def comprobar_que_no_es_real(url: str) -> None:
    """Se niega a correr contra una base que no se llame de pruebas."""
    if not _parece_base_de_pruebas(url):
        pytest.fail(
            "TEST_DATABASE_URL no parece una base de pruebas: "
            f"'{url.rsplit('/', 1)[-1]}'. Estas pruebas borran filas. "
            "El nombre tiene que contener 'test' o 'prueba'."
        )


def motor_de_pruebas(url: str) -> Engine:
    """Motor para las pruebas.

    `NullPool`: cada prueba abre y cierra lo suyo, y así ninguna hereda
    el estado de sesión de la anterior.
    """
    comprobar_que_no_es_real(url)
    from sqlalchemy.pool import NullPool

    return create_engine(
        url,
        poolclass=NullPool,
        connect_args={"connect_timeout": 10, "application_name": "epic-wallet-tests"},
    )


# ===================================================================
#  Las claves con las que esta batería firma sus tokens
# ===================================================================

_privada = ec.generate_private_key(ec.SECP256R1())

CLAVE_PRIVADA = _privada.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()

CLAVE_PUBLICA = (
    _privada.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode()
)


def firmar(
    uid: str,
    *,
    correo: str | None = None,
    vence_en: int = 3600,
    aud: str | None = AUDIENCIA,
    extra: dict[str, Any] | None = None,
    clave: Any = None,
) -> str:
    """Un token como el que emitirá el servidor desde F17-T02.

    `clave` existe para las pruebas que necesitan firmar con la clave
    equivocada y comprobar que se rechaza.
    """
    ahora = int(time.time())
    carga: dict[str, Any] = {"sub": uid, "iat": ahora, "exp": ahora + vence_en}
    if aud is not None:
        carga["aud"] = aud
    if correo:
        carga["email"] = correo
    carga.update(extra or {})
    return jwt.encode(carga, clave or CLAVE_PRIVADA, algorithm=ALGORITMO)


# ===================================================================
#  Cuentas de prueba
# ===================================================================


@dataclass(frozen=True)
class Cuenta:
    """Una cuenta descartable con su token."""

    uid: str
    correo: str
    token: str

    @property
    def cabeceras(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


_motor_compartido: Engine | None = None


def motor_compartido() -> Engine:
    """Un motor para dar de alta y borrar cuentas.

    Existe para que `crear_cuenta()` se pueda llamar desde donde no hay
    un motor a mano, que es como la llaman casi todos los archivos.
    """
    global _motor_compartido
    if _motor_compartido is None:
        assert URL_BASE, "sin TEST_DATABASE_URL"
        _motor_compartido = motor_de_pruebas(URL_BASE)
    return _motor_compartido


def crear_cuenta(motor: Engine | None = None, *, correo: str | None = None) -> Cuenta:
    """Da de alta una cuenta descartable y devuelve su token.

    Se inserta directo en `auth.users`. El trigger
    `crear_perfil_y_categorias` hace el resto —perfil y 21
    categorías—, igual que con una cuenta de verdad: por eso esto
    prueba el camino completo y no un atajo.

    La contraseña no se usa: estas pruebas no pasan por el login, que
    es lo que prueba F17-T02. Se guarda un valor con la forma de un
    hash para que la columna no quede mintiendo.
    """
    uid = str(uuid.uuid4())
    correo = correo or f"epicwallet.{secrets.token_hex(6)}@{DOMINIO_DE_PRUEBA}"
    motor = motor or motor_compartido()

    with motor.begin() as con:
        con.execute(text("reset role"))
        con.execute(
            text(
                "insert into auth.users (id, email, encrypted_password, "
                "email_confirmed_at) values (:id, :correo, :hash, now())"
            ),
            {"id": uid, "correo": correo, "hash": "$2b$12$" + "x" * 53},
        )

    return Cuenta(uid=uid, correo=correo, token=firmar(uid, correo=correo))


def borrar_cuentas(motor: Engine | None, *uids: str) -> None:
    """Borra cuentas de prueba y, en cascada, todo lo que cargaron.

    Sólo borra si el correo es de `example.com`: una cuenta que no sea
    descartable no se toca ni por error.
    """
    if not uids:
        return
    motor = motor or motor_compartido()
    with motor.begin() as con:
        con.execute(text("reset role"))
        con.execute(
            text(
                "delete from auth.users where id = any(:ids) "
                f"and email like '%@{DOMINIO_DE_PRUEBA}'"
            ),
            {"ids": list(uids)},
        )

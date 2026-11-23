"""Genera el par de claves con el que se firman las sesiones · F17-T01.

    python scripts/generar_claves.py            # las imprime
    python scripts/claves/                      # (ver --salida)

Son ES256: curva P-256, el mismo algoritmo que ya usaba el proyecto.
La privada firma; la pública sólo verifica.

QUÉ HACER CON LO QUE IMPRIME

Las dos líneas van al `.env` del servidor y a ningún otro lado:

    JWT_PRIVATE_KEY=...
    JWT_PUBLIC_KEY=...

Los saltos de línea del formato PEM van escapados, porque un archivo
de variables de entorno es de una línea por variable. `core/config.py`
los deshace al leerlos.

LA PRIVADA ES EL SECRETO MÁS CARO DEL PROYECTO

Quien la tenga puede fabricar la sesión de cualquier usuario, sin
contraseña y sin dejar rastro. No entra al repositorio, no va al
frontend, no se pega en un chat y no sale del servidor. Por eso este
script imprime y no escribe: así nadie termina con una copia olvidada
en el disco de su máquina.

Si alguna vez se filtra, se genera un par nuevo y se reemplaza. El
costo es que todas las sesiones abiertas se caen y cada uno vuelve a
entrar; las contraseñas no se tocan.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generar() -> tuple[str, str]:
    """Devuelve (privada, pública) en PEM."""
    privada = ec.generate_private_key(ec.SECP256R1())

    pem_privada = privada.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        # Sin contraseña: la clave ya vive en un archivo que sólo lee
        # root, y una contraseña que hay que guardar al lado de la
        # clave no protege de nada.
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    pem_publica = (
        privada.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return pem_privada, pem_publica


def _una_linea(pem: str) -> str:
    """El PEM con los saltos escapados, listo para un archivo .env."""
    return pem.strip().replace("\n", "\\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--salida",
        type=Path,
        help=(
            "escribe las dos claves en archivos .pem dentro de este "
            "directorio, en lugar de imprimirlas. Sólo para la máquina de "
            "desarrollo: en el servidor van al .env"
        ),
    )
    args = parser.parse_args()

    privada, publica = generar()

    if args.salida:
        args.salida.mkdir(parents=True, exist_ok=True)
        destino_privada = args.salida / "jwt_privada.pem"
        destino_publica = args.salida / "jwt_publica.pem"
        destino_privada.write_text(privada, encoding="utf-8")
        destino_publica.write_text(publica, encoding="utf-8")
        # 0600: sólo el dueño. En Windows no hace nada, y por eso el
        # aviso de abajo no depende de esto.
        destino_privada.chmod(0o600)
        print(f"privada → {destino_privada}")
        print(f"pública → {destino_publica}")
        print()
        print("Revisá que el directorio esté en .gitignore antes de seguir.")
        return 0

    print("# Las dos líneas van al .env del servidor, y a ningún otro lado.")
    print("# La privada permite fabricar la sesión de cualquier usuario.")
    print()
    print(f"JWT_PRIVATE_KEY={_una_linea(privada)}")
    print(f"JWT_PUBLIC_KEY={_una_linea(publica)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

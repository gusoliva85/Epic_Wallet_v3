"""Comandos que se corren a mano, dentro del servidor · F17-T04.

    docker compose exec api python -m app.cli recuperar <email>

Referencia: 01_Documento_General.md §48.1

POR QUÉ ESTO ES UN COMANDO Y NO UNA PANTALLA

Un «olvidé mi contraseña» de formulario es una puerta que cualquiera
puede tocar desde internet, a cualquier hora, sin dejar más rastro que
una línea en un registro. Que funcione depende enteramente de que el
buzón de correo de la persona esté a salvo, y el buzón es justamente
lo que más se roba.

Acá no existe esa puerta. Para que se emita un enlace hay que entrar
al servidor por SSH y escribirlo. No hay nada que un desconocido pueda
disparar.

El costo es claro y conviene decirlo: **quien puede correr esto puede
tomar cualquier cuenta.** A la escala de este proyecto —unos pocos
usuarios conocidos, y el que administra el servidor es el mismo que
administra las cuentas— eso no agrega ningún riesgo: con acceso de
root a la máquina, la base entera ya está a la vista.
"""

from __future__ import annotations

import argparse
import sys

from .core.config import get_settings
from .core.db import sesion_manual
from .services import sesiones

# Dónde vive la aplicación, para armar el enlace. Sale de la
# configuración; el valor de abajo es el del servidor de hoy.
SITIO_POR_DEFECTO = "https://13-140-36-93.sslip.io"


def _sitio() -> str:
    return (get_settings().PUBLIC_APP_URL or SITIO_POR_DEFECTO).rstrip("/")


def recuperar(correo: str) -> int:
    """Imprime un enlace de contraseña nueva para esa cuenta.

    El enlace lleva la forma que ya lee `enlace-correo.js`:
    `?token_hash=…&type=recovery#/nueva-clave`. La pantalla lo saca de
    la barra de direcciones en cuanto lo lee, así que no queda en el
    historial ni en una captura de pantalla.
    """
    with sesion_manual() as sesion:
        token = sesiones.emitir_enlace(sesion, correo)

    if token is None:
        print(f"\n  No hay ninguna cuenta con el correo '{correo}'.", file=sys.stderr)
        print("  Revisá cómo está escrito.\n", file=sys.stderr)
        return 1

    enlace = f"{_sitio()}/?token_hash={token}&type=recovery#/nueva-clave"

    print()
    print(f"  Enlace para {correo}:")
    print()
    print(f"  {enlace}")
    print()
    print(f"  Vale {sesiones.MINUTOS_DE_RECUPERACION} minutos y UNA sola vez.")
    print("  Al usarse se caen todas las sesiones abiertas de esa cuenta.")
    print()
    print("  Es una llave de la cuenta: mandalo por donde puedas borrarlo")
    print("  después, y no lo dejes anotado en ningún lado.")
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)

    p = comandos.add_parser("recuperar", help="enlace de contraseña nueva")
    p.add_argument("email", help="el correo de la cuenta")

    args = parser.parse_args(argv)
    if args.comando == "recuperar":
        return recuperar(args.email)
    parser.error(f"comando desconocido: {args.comando}")
    return 2


if __name__ == "__main__":
    sys.exit(main())

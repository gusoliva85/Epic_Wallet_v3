"""Contraseñas y tokens opacos · F17-T02.

Todo lo de acá son funciones puras: entra un texto, sale un texto. No
tocan la base ni la configuración, y por eso se pueden probar sin
levantar nada. La parte que decide **quién entra** no debería depender
de montar un servidor para comprobarse.

POR QUÉ BCRYPT Y NO ALGO MÁS NUEVO

Porque es el mismo algoritmo que usaba el proveedor anterior. Sus
hashes son cadenas `$2a$`/`$2b$` estándar, así que al importar los
datos en F19 entran tal cual y **nadie tiene que restablecer su
contraseña**. Cambiar a argon2 obligaría a que cada uno vuelva a
elegir una clave el día del corte, que es exactamente el tipo de
fricción que hace que una migración se sienta como una pérdida.

LAS DOS CLASES DE SECRETO, Y POR QUÉ SE GUARDAN DISTINTO

- Una **contraseña** la elige una persona, tiene poca entropía y hay
  que hacer que probarla sea caro. De eso se encarga bcrypt con su
  costo y su sal.
- Un **token de renovación** lo generamos nosotros con 32 bytes de
  azar. Adivinarlo es imposible, así que encarecer la comparación no
  compra nada y sí costaría 100 ms en cada renovación. Se guarda su
  SHA-256: alcanza para que leer la tabla no sirva de nada, y la
  búsqueda sigue siendo un índice.

Usar bcrypt para lo segundo, además, impediría buscar por hash: bcrypt
genera una sal distinta cada vez, así que el mismo token da hashes
distintos y habría que traer todas las filas y probarlas una por una.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

import bcrypt

# Costo de bcrypt. 12 son ~250 ms en el servidor: suficiente para que
# probar contraseñas a mano sea inviable, y poco para que entrar no se
# sienta lento. Es también el costo con el que vienen los hashes del
# proveedor anterior, así que no hay que recalcular nada al importar.
COSTO = 12

# Mínimo de una contraseña. Ocho es lo que pedía la 2.0 y lo que dice
# el mensaje que ya ve el usuario; subirlo ahora dejaría afuera a las
# contraseñas que ya existen.
MINIMO_DE_CLAVE = 8

# Bcrypt ignora todo lo que pase de 72 bytes, en silencio. Si no se
# cortara acá, dos contraseñas largas distintas que comparten los
# primeros 72 bytes abrirían la misma cuenta. Se rechaza en vez de
# truncar: truncar sería aceptar una contraseña que no es la que la
# persona escribió.
MAXIMO_DE_CLAVE = 72


def clave_invalida(clave: str) -> str | None:
    """El motivo por el que la contraseña no sirve, o `None` si sirve."""
    if len(clave) < MINIMO_DE_CLAVE:
        return f"La contraseña tiene que tener al menos {MINIMO_DE_CLAVE} caracteres."
    if len(clave.encode("utf-8")) > MAXIMO_DE_CLAVE:
        return f"La contraseña no puede pasar de {MAXIMO_DE_CLAVE} caracteres."
    return None


def hashear_clave(clave: str) -> str:
    """El hash bcrypt de una contraseña, con sal nueva."""
    return bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt(COSTO)).decode("ascii")


def verificar_clave(clave: str, hash_guardado: str) -> bool:
    """Si la contraseña corresponde al hash.

    Nunca levanta: un hash corrupto, vacío o con un formato que bcrypt
    no entiende devuelve `False`. Si levantara, una fila mal guardada
    convertiría un «contraseña incorrecta» en un error 500, que además
    le contaría a quien prueba que esa cuenta existe y tiene algo raro.
    """
    if not hash_guardado:
        return False
    try:
        return bcrypt.checkpw(clave.encode("utf-8"), hash_guardado.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# El tiempo que tarda verificar una contraseña es información: si
# responder «no existe» fuera instantáneo y «clave incorrecta» tardara
# 250 ms, cronometrar las respuestas diría qué correos tienen cuenta.
# Contra un email desconocido se verifica contra este hash, que no
# corresponde a ninguna contraseña real, para gastar el mismo tiempo.
HASH_DE_RELLENO = hashear_clave(secrets.token_urlsafe(32))


def gastar_el_mismo_tiempo() -> None:
    """Verifica contra un hash de mentira, para no delatar por reloj."""
    verificar_clave("x", HASH_DE_RELLENO)


# ===================================================================
#  Tokens opacos (renovación, recuperación)
# ===================================================================

# 32 bytes de azar del sistema. En base64 son 43 caracteres sin nada
# que escapar, así que viajan igual en una URL, en un JSON o en una
# cabecera.
BYTES_DE_TOKEN = 32


def generar_token_opaco() -> str:
    """Un token imposible de adivinar. Se muestra una sola vez."""
    return secrets.token_urlsafe(BYTES_DE_TOKEN)


def huella(token: str) -> str:
    """El SHA-256 del token, que es lo único que se guarda.

    Si alguien se lleva la tabla, se lleva huellas: no puede renovar
    ninguna sesión ni usar ningún enlace de recuperación.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def huellas_iguales(a: str, b: str) -> bool:
    """Compara dos huellas en tiempo constante."""
    return hmac.compare_digest(a, b)

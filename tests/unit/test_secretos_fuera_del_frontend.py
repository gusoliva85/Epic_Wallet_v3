"""Los secretos no llegan al navegador ni al repositorio · F11-T04.

Es el único de los controles del proyecto que, si falla, **no se puede
deshacer**: un secreto dentro de un archivo que sirve el navegador ya
quedó publicado, y rotarlo no borra a quién lo vio.

QUÉ SECRETO, Y POR QUÉ CAMBIÓ

Hasta F17-T06 esto cuidaba la clave de servicio del proveedor anterior,
que se salteaba RLS. Ese proveedor no existe más y esa clave tampoco.
Lo que hay hoy es peor si se escapa:

- **`JWT_PRIVATE_KEY`** firma las sesiones. Con ella se fabrica la
  sesión de cualquier usuario, sin contraseña y sin dejar rastro. No
  hace falta saltearse RLS: se entra como el dueño de los datos.
- **`DATABASE_URL`** trae la contraseña de Postgres.

POR QUÉ ESTE ARCHIVO EXISTE SI LA POLÍTICA DICE «NO SE TESTEA EL DESPLIEGUE»

Porque esto no es configuración de despliegue, es «lo que protege un
dato», que es el otro lado de la regla. El criterio de CLAUDE.md
aplicado literal —*si el test falla, ¿me enteré de algo que la pantalla
no me hubiera mostrado?*— da sí: una clave privada en un `.js`
publicado no se ve mirando la aplicación en el celular. La pantalla
funciona igual de bien con ella adentro.

DOS REDES, Y HACEN FALTA LAS DOS

1. **Por forma** (`RASTROS`): busca el encabezado de un PEM o una
   cadena de conexión. Atrapa cualquier clave, incluida una que esta
   máquina no conoce, y corre siempre.
2. **Por valor**: compara contra el secreto que haya en el entorno. Es
   más precisa pero sólo existe donde el secreto existe, así que en la
   máquina de desarrollo —donde el `.env` va vacío a propósito— se
   saltea. Por eso no puede ser la única.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
WEB = RAIZ / "web"

# Lo que un navegador puede pedir.
EXTENSIONES = (".js", ".mjs", ".html", ".json", ".css", ".webmanifest")

# La forma de nuestros secretos. Ninguna de estas cadenas tiene por qué
# aparecer nunca en algo que sirva el navegador.
RASTROS = (
    "BEGIN PRIVATE KEY",
    "BEGIN EC PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "postgresql+psycopg://",
    "postgres://",
)

# Los secretos que se comparan por valor, cuando están.
SECRETOS = ("JWT_PRIVATE_KEY", "DATABASE_URL")


def _del_env(clave: str) -> str | None:
    """El valor de esa variable, del entorno o del `.env`, o `None`.

    El espacio alrededor del `=` se busca con `[ \\t]*` y no con `\\s*`,
    y la diferencia no es cosmética: `\\s` incluye el salto de línea, así
    que contra un `.env` donde la variable está **vacía** —como el de la
    máquina de desarrollo— el patrón seguía leyendo y devolvía la línea
    de abajo. La prueba comparaba entonces contra un valor que no era
    el buscado. Lo encontró la reescritura de F17-T06.
    """
    valor = os.getenv(clave, "").strip()
    if valor:
        return valor
    archivo = RAIZ / ".env"
    if not archivo.exists():
        return None
    m = re.search(rf"^{clave}[ \t]*=[ \t]*(.+)$", archivo.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip() if m else None


def archivos_publicados() -> list[Path]:
    """Todo `web/`, no sólo un archivo: si alguien pega un secreto en un
    módulo, en el HTML o en el service worker, hay que verlo igual."""
    return [
        p
        for p in WEB.rglob("*")
        if p.is_file() and p.suffix in EXTENSIONES and "node_modules" not in p.parts
    ]


def archivos_del_repositorio() -> list[Path]:
    """Lo que está versionado, que es lo que se publica al repositorio.

    Se le pregunta a Git en vez de recorrer el disco: `.env` existe en
    esta máquina y puede tener secretos, y está bien que los tenga
    —está en `.gitignore`—. Lo que no puede pasar es que alguno haya
    quedado en un archivo rastreado.

    Sin `git` no hay nada que preguntar y la prueba se saltea. Pasa
    dentro del contenedor de la api, que no lo lleva: la imagen tiene
    el código, no el repositorio. Decirlo como salto y no como falla
    importa, porque una falla acá se lee como «hay un secreto
    publicado», que es exactamente lo contrario de lo que pasó.
    """
    try:
        salida = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except FileNotFoundError:
        pytest.skip("no hay git acá: esta prueba mira el repositorio, no el disco")
    return [RAIZ / n for n in salida.split("\0") if n]


# =================================================== el navegador


def test_el_barrido_encuentra_los_archivos_publicados() -> None:
    """El contrapeso de todo lo que sigue, y no es un adorno.

    Si `archivos_publicados()` devolviera una lista vacía —una carpeta
    renombrada, una extensión que cambió—, las pruebas de abajo
    quedarían en verde sin haber mirado un solo archivo. Verde por
    vacío es el peor verde.
    """
    encontrados = archivos_publicados()
    assert len(encontrados) >= 10, f"el barrido sólo encontró {len(encontrados)} archivos en web/"

    nombres = {a.name for a in encontrados}
    assert "index.html" in nombres, "el barrido no ve ni el index.html"


def test_ninguna_clave_privada_tiene_la_forma_de_estar_publicada() -> None:
    """La red por forma: atrapa cualquier clave, no sólo la de acá."""
    sospechosos = [
        f"{a.relative_to(RAIZ)}: {patron}"
        for a in archivos_publicados()
        for patron in RASTROS
        if patron in a.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not sospechosos, f"hay rastros de un secreto en lo publicado: {sospechosos}"


@pytest.mark.parametrize("variable", SECRETOS)
def test_el_secreto_del_entorno_no_esta_en_ningun_archivo_publicado(variable: str) -> None:
    """La red por valor, para lo que la forma no cubre.

    Una contraseña de base no tiene forma reconocible: la única manera
    de detectarla es comparar contra la que hay.
    """
    secreto = _del_env(variable)
    if not secreto:
        pytest.skip(f"no hay {variable} en este entorno con la que comparar")

    culpables = [
        str(a.relative_to(RAIZ))
        for a in archivos_publicados()
        if secreto in a.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not culpables, (
        f"{variable} aparece en {culpables}. Ya está publicada: hay que "
        "generar un par nuevo en el servidor, no sólo borrarla de ahí."
    )


# =================================================== el repositorio


@pytest.mark.parametrize("variable", SECRETOS)
def test_ningun_secreto_quedo_en_un_archivo_rastreado(variable: str) -> None:
    """La otra mitad del criterio: «ni en el repositorio».

    Se comparan **valores**, no nombres: los nombres de las variables
    aparecen a propósito en `.env.example`, en el README y en el
    documento técnico, y tienen que seguir apareciendo. Lo que no puede
    estar es el valor.

    Por eso acá no se usa `RASTROS`: `scripts/check_db.py` nombra el
    encabezado de un PEM para comprobar que la clave tiene la forma
    correcta, y eso es legítimo. La forma se exige sólo en `web/`.
    """
    secreto = _del_env(variable)
    if not secreto:
        pytest.skip(f"no hay {variable} en este entorno con la que comparar")
    # Un valor corto sería una comparación sin sentido: daría falsos
    # positivos contra cualquier texto.
    assert len(secreto) >= 20, f"{variable} es demasiado corta para ser el secreto real"

    culpables = []
    for archivo in archivos_del_repositorio():
        try:
            if secreto in archivo.read_text(encoding="utf-8", errors="ignore"):
                culpables.append(str(archivo.relative_to(RAIZ)))
        except (OSError, ValueError):
            # Un archivo rastreado que no está en el disco (borrado sin
            # confirmar) o que no se puede leer: no es lo que se busca.
            continue

    assert not culpables, (
        f"{variable} quedó en archivos versionados: {culpables}. "
        "El valor ya está en el historial: hay que rotarlo."
    )


def test_el_env_con_los_secretos_no_esta_rastreado() -> None:
    """Lo que hace que la prueba de arriba no sea trivial.

    `.env` puede tener secretos y está bien que los tenga. El día que
    alguien lo agregue al repositorio —un `git add -f`, o un
    `.gitignore` que alguien «limpia»—, los secretos se publican; la
    prueba de arriba lo detectaría, pero conviene decirlo con el
    nombre del archivo.

    Necesita `git`, así que dentro del contenedor de la api no corre.
    Para eso está `scripts/pruebas_en_el_servidor.sh`, que lo dice.
    """
    rastreados = {a.name for a in archivos_del_repositorio()}
    assert ".env" not in rastreados, ".env está versionado: los secretos ya se publicaron"
    assert ".env.example" in rastreados, "falta .env.example, que sí tiene que estar"

"""Arma el SQL que importa los datos de la versión anterior · F19-T02.

    python scripts/importar_datos_anteriores.py
    python scripts/importar_datos_anteriores.py --todas-las-cuentas

Lee el JSON que bajó F19-T01 (`documentacion/Export Database/todo.csv`,
una sola fila con las diez tablas adentro) y escribe un `.sql` listo
para correr en el servidor. **No se conecta a ninguna base**: lee un
archivo y escribe otro.

POR QUÉ UN SCRIPT Y NO UN SQL ESCRITO A MANO

Porque esto se corre **dos veces**. Hoy, para probar la 3.0 con datos
de verdad; y otra vez el día del corte, cuando la 2.0 deje de usarse —
entre medio Gustavo sigue cargando movimientos allá, así que el archivo
de hoy ya está viejo mañana. Un SQL a mano habría que rehacerlo
entero.

LAS TRES COSAS QUE HACEN FALLAR UNA IMPORTACIÓN, Y CÓMO SE RESUELVEN

1. **El trigger.** `al_crear_usuario_public` crea un perfil y 21
   categorías cada vez que entra una fila en `auth.users`. Con los
   datos reales eso choca: el perfil ya viene, y las categorías
   inventadas se quedarían con ids que los movimientos no referencian.
   Se apaga durante la carga y se vuelve a encender.

2. **Las secuencias.** Las filas entran con su `id` original, pero la
   secuencia de cada tabla sigue en cero. Sin un `setval`, el primer
   movimiento que cargue alguien desde la pantalla pide el id 1 —que ya
   existe— y falla con una violación de clave. No se ve hasta que
   alguien intenta guardar algo.

3. **El orden.** Las claves foráneas exigen que el padre exista antes
   que el hijo: usuarios, perfiles, categorías y meses antes de
   movimientos y totales.

TODO EN UNA SOLA TRANSACCIÓN

El `.sql` abre con `\\set ON_ERROR_STOP on` y `begin`, y cierra con
`commit`. Si algo falla en el medio, no queda ni una fila a medias: se
revierte todo y la base queda como estaba. Es lo que permite correrlo
sin miedo y volver a intentar.

Los valores no se pegan dentro de un `insert`: van por `copy … from
stdin` en formato CSV, y el que interpreta cada valor es Postgres. Así
no hay comilla, acento ni salto de línea que pueda romper el SQL ni
cambiar su significado.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "documentacion" / "Export Database" / "todo.csv"
SALIDA = RAIZ / "documentacion" / "Export Database" / "importar.sql"

# Qué cuentas NO entran.
#
# El export trae cuentas de más: la batería de pruebas creaba y borraba
# cuentas contra producción —el accidente de noviembre que está anotado
# en CLAUDE.md— y quedaron las que no se alcanzaron a borrar. Todas
# usan `example.com`, que la RFC 2606 reserva justamente para esto.
#
# Se descartan por el dominio y no por una lista de los correos que sí
# entran, por dos motivos: una lista de correos de personas no tiene
# por qué vivir en el repositorio, y además habría que mantenerla cada
# vez que haya una cuenta nueva. La regla se mantiene sola.
DOMINIO_DESCARTABLE = "@example.com"

TRIGGER = "al_crear_usuario_public"

# El orden es el de las claves foráneas, y no se puede alterar.
# (clave en el JSON, tabla, columna que dice de quién es la fila)
ORDEN: list[tuple[str, str, str]] = [
    ("auth_users", "auth.users", ""),
    ("profiles", "public.profiles", "id"),
    ("categories", "public.categories", "user_id"),
    ("months", "public.months", "user_id"),
    ("transactions", "public.transactions", "user_id"),
    ("monthly_category_totals", "public.monthly_category_totals", "user_id"),
    ("investments", "public.investments", "user_id"),
    ("liabilities", "public.liabilities", "user_id"),
    ("app_settings", "public.app_settings", "user_id"),
    ("category_dues", "public.category_dues", "user_id"),
]

# Las ocho tablas con `id` autoincremental y su secuencia.
SECUENCIAS = [
    "categories",
    "months",
    "transactions",
    "monthly_category_totals",
    "investments",
    "liabilities",
    "app_settings",
    "category_dues",
]

# Marca de nulo para el COPY. Un campo vacío queda como cadena vacía,
# que no es lo mismo que NULL: con una marca explícita los dos casos se
# distinguen sin ambigüedad.
NULO = "\\N"

# Las columnas `json`/`jsonb`, por tabla.
#
# HACEN FALTA, Y LO DEMOSTRÓ UN ERROR. `app_settings.value` es `jsonb` y
# guarda la cadena `"light"`. Al leer el export, eso llega como el texto
# `light`, igual que el valor de cualquier columna de texto: mirando el
# valor **no hay forma de distinguirlos**. Escrito sin comillas, Postgres
# lo rechaza con «Token "light" is invalid», porque una cadena JSON las
# lleva. La diferencia la tiene el esquema, no el dato, así que está acá.
#
# `auth.users.raw_user_meta_data` no habia fallado de casualidad: guarda
# un objeto, y un diccionario de Python ya se escribía como JSON.
COLUMNAS_JSON: dict[str, set[str]] = {
    "public.app_settings": {"value"},
    "auth.users": {"raw_user_meta_data"},
}


def leer_export(ruta: Path) -> dict[str, list[dict[str, Any]]]:
    """El JSON de una sola celda que dejó F19-T01.

    `field_size_limit` sube el límite del lector de CSV: las diez tablas
    vienen en un solo campo y el valor por defecto (128 KB) no alcanza.

    `parse_float=Decimal` no es un detalle: los importes son
    `numeric(14,2)` y pasarlos por `float` los redondearía mal. Acá sólo
    se vuelven a escribir como texto, pero no hay motivo para que un
    importe se convierta en binario en el camino.
    """
    csv.field_size_limit(10_000_000)
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))
    if len(filas) != 1:
        raise SystemExit(f"{ruta.name} tiene {len(filas)} filas y tendría que tener una")
    return json.loads(filas[0]["todo"], parse_float=Decimal)


def a_texto(valor: Any, *, es_json: bool = False) -> str:
    """Un valor del JSON como lo espera el COPY en formato CSV.

    `es_json` manda sobre todo lo demás: una columna `jsonb` tiene que
    recibir JSON válido, y la cadena `light` sin comillas no lo es.
    """
    if valor is None:
        return NULO
    if es_json:
        return json.dumps(valor, ensure_ascii=False, separators=(",", ":"))
    if valor is True:
        return "true"
    if valor is False:
        return "false"
    if isinstance(valor, Decimal | int | float):
        return str(valor)
    if isinstance(valor, dict | list):
        return json.dumps(valor, ensure_ascii=False, separators=(",", ":"))
    return str(valor)


def bloque_copy(tabla: str, filas: list[dict[str, Any]]) -> str:
    """Un `copy … from stdin` con sus filas y su terminador."""
    columnas = list(filas[0].keys())
    de_json = COLUMNAS_JSON.get(tabla, set())
    buffer = io.StringIO()
    escritor = csv.writer(buffer, lineterminator="\n")
    for fila in filas:
        escritor.writerow([a_texto(fila[c], es_json=c in de_json) for c in columnas])

    lista = ", ".join(f'"{c}"' for c in columnas)
    return (
        f"copy {tabla} ({lista}) from stdin with (format csv, null '{NULO}');\n"
        f"{buffer.getvalue()}\\.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entrada", type=Path, default=ENTRADA)
    ap.add_argument("--salida", type=Path, default=SALIDA)
    ap.add_argument(
        "--todas-las-cuentas",
        action="store_true",
        help="trae también las cuentas de prueba del export; por defecto sólo las tres reales",
    )
    args = ap.parse_args()

    if not args.entrada.exists():
        raise SystemExit(f"no existe {args.entrada}")

    datos = leer_export(args.entrada)

    todos = datos.get("auth_users", [])
    if args.todas_las_cuentas:
        elegidos = todos
    else:
        elegidos = [u for u in todos if not u["email"].lower().endswith(DOMINIO_DESCARTABLE)]

    if not elegidos:
        raise SystemExit("el export no trae ninguna cuenta para importar")

    uids = {u["id"] for u in elegidos}

    partes: list[str] = []
    resumen: list[tuple[str, int, int]] = []
    for clave, tabla, columna in ORDEN:
        filas = datos.get(clave, [])
        if clave == "auth_users":
            mias = elegidos
        elif columna:
            mias = [f for f in filas if f.get(columna) in uids]
        else:
            mias = filas
        resumen.append((tabla, len(filas), len(mias)))
        if mias:
            partes.append(bloque_copy(tabla, mias))

    # `SECUENCIAS` es una lista fija escrita arriba, en este archivo: no
    # sale de la entrada ni de la línea de comando, así que no hay nada
    # que un dato pueda inyectar acá.
    setvals = "\n".join(
        f"select setval('public.{t}_id_seq', "  # noqa: S608
        f"coalesce((select max(id) from public.{t}), 1), "
        f"(select exists(select 1 from public.{t})));"
        for t in SECUENCIAS
    )

    sql = f"""-- Importación de los datos de la versión anterior · F19-T02
-- Generado por scripts/importar_datos_anteriores.py · NO editar a mano.
--
-- Cuentas: {len(elegidos)}
--
-- Una sola transacción: si algo falla, no queda ni una fila a medias.
\\set ON_ERROR_STOP on
begin;

-- El trigger crea un perfil y 21 categorías por cada usuario nuevo.
-- Con los datos reales eso choca: el perfil ya viene en el export.
alter table auth.users disable trigger {TRIGGER};

{"".join(partes)}
-- Las filas entraron con su id original, pero las secuencias siguen en
-- cero. Sin esto, el primer movimiento que alguien cargue desde la
-- pantalla pide un id que ya existe y falla.
{setvals}

alter table auth.users enable trigger {TRIGGER};

commit;
"""

    args.salida.write_bytes(sql.encode("utf-8"))

    print(f"{'tabla':34} {'en el export':>13} {'se importa':>11}")
    print("-" * 62)
    for tabla, total, mias in resumen:
        print(f"{tabla:34} {total:>13} {mias:>11}")
    print()
    for u in sorted(elegidos, key=lambda x: x["email"]):
        print(f"  cuenta: {u['email']}")
    print()
    print(f"escrito: {args.salida}  ({len(sql):,} caracteres)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

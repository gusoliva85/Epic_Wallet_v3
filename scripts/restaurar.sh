#!/usr/bin/env bash
# ============================================================
#  Restaurar un respaldo · F18-T03
#
#  Uso:
#      ./scripts/restaurar.sh respaldos/diario/epic_wallet_....dump
#      ./scripts/restaurar.sh <archivo> --base otra_base
#      ./scripts/restaurar.sh <archivo> --sobre-la-real
#
#  POR QUE NO RESTAURA SOBRE LA BASE REAL
#
#  Por defecto restaura en `epic_wallet_restaurado`, una base aparte
#  que crea y pisa cada vez. Restaurar es una operacion destructiva:
#  borra la base de destino entera antes de empezar. Si el destino por
#  defecto fuera la base real, este script corrido para «probar que
#  anda» borraria la contabilidad.
#
#  Para la base real hace falta `--sobre-la-real` Y escribir el nombre
#  de la base a mano cuando lo pida. Dos pasos deliberados, porque esa
#  es la unica operacion del proyecto que no tiene vuelta atras salvo
#  por otro respaldo.
#
#  QUE SE COMPARA AL FINAL
#
#  Tabla por tabla, cuantas filas tiene la base restaurada contra
#  cuantas tiene la de origen. Si una sola difiere, el script falla.
#  «pg_restore no dio error» no es lo mismo que «los datos estan»: un
#  respaldo tomado a medias restaura limpio y con menos filas, y el
#  unico modo de enterarse es contar.
#
#  TODA llamada a `docker compose exec` lleva `</dev/null`: `exec -T`
#  lee la entrada estandar y si no, se come el resto del script.
# ============================================================
set -uo pipefail

cd "$(dirname "$0")/.."
RAIZ="$(pwd)"

DESTINO_RESPALDOS="${RESPALDOS_DIR:-$RAIZ/respaldos}"
SERVICIO_DB="${SERVICIO_DB:-db}"

rojo()  { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }
gris()  { printf '\033[90m%s\033[0m\n' "$*"; }

leer_env() {
  [ -f "$RAIZ/.env" ] || return 0
  sed -n "s/^$1=//p" "$RAIZ/.env" | head -1
}
USUARIO="${POSTGRES_USER:-$(leer_env POSTGRES_USER)}"
ORIGEN="${POSTGRES_DB:-$(leer_env POSTGRES_DB)}"
USUARIO="${USUARIO:-epic}"
ORIGEN="${ORIGEN:-epic_wallet}"

ARCHIVO=""
BASE="epic_wallet_restaurado"
SOBRE_LA_REAL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --base)
      BASE="${2:-}"
      [ -n "$BASE" ] || { echo "ERROR: --base necesita un nombre" >&2; exit 2; }
      shift 2 ;;
    --sobre-la-real)
      SOBRE_LA_REAL=1; shift ;;
    -h|--help)
      sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)
      echo "ERROR: argumento desconocido: $1" >&2; exit 2 ;;
    *)
      [ -z "$ARCHIVO" ] || { echo "ERROR: sobra '$1'" >&2; exit 2; }
      ARCHIVO="$1"; shift ;;
  esac
done

[ "$SOBRE_LA_REAL" -eq 1 ] && BASE="$ORIGEN"
[ -n "$ARCHIVO" ] || { echo "ERROR: falta el archivo a restaurar. -h para la ayuda" >&2; exit 2; }

psql_en() {
  # $1 = base; el resto, argumentos de psql
  local base="$1"; shift
  docker compose exec -T "$SERVICIO_DB" \
    psql -U "$USUARIO" -d "$base" -v ON_ERROR_STOP=1 "$@" </dev/null
}

# ------------------------------------------------------------
#  1 · El archivo, antes de tocar nada
# ------------------------------------------------------------
# Se verifica ANTES de borrar la base de destino. Al reves, un dump
# ilegible dejaria la base vacia y nada con que llenarla.
echo "Verificando el respaldo..."
if ! ./scripts/respaldo.sh --solo-verificar "$ARCHIVO"; then
  rojo "No se restaura: el respaldo no paso la verificacion."
  exit 1
fi

absoluta="$(cd "$(dirname "$ARCHIVO")" && pwd)/$(basename "$ARCHIVO")"
RELATIVA="${absoluta#"$DESTINO_RESPALDOS"/}"

# ------------------------------------------------------------
#  2 · El destino
# ------------------------------------------------------------
if [ "$BASE" = "$ORIGEN" ] && [ "$SOBRE_LA_REAL" -ne 1 ]; then
  rojo "FALLA · '$BASE' es la base real. Hace falta --sobre-la-real."
  exit 1
fi

if [ "$SOBRE_LA_REAL" -eq 1 ]; then
  rojo "================================================================"
  rojo " VAS A BORRAR LA BASE REAL '$ORIGEN' Y REEMPLAZARLA"
  rojo " por $RELATIVA"
  rojo " Todo lo cargado despues de ese respaldo se pierde."
  rojo "================================================================"
  printf "Escribi el nombre de la base para confirmar: "
  read -r confirmacion < /dev/tty
  if [ "$confirmacion" != "$ORIGEN" ]; then
    rojo "Cancelado."
    exit 1
  fi
fi

echo
echo "Restaurando $RELATIVA -> base '$BASE'"

# ------------------------------------------------------------
#  3 · Base de destino limpia
# ------------------------------------------------------------
# Se cortan las conexiones abiertas: `drop database` falla si queda
# una sola, y la propia aplicacion suele tener varias del pool.
psql_en postgres -q -c \
  "select pg_terminate_backend(pid) from pg_stat_activity
   where datname = '$BASE' and pid <> pg_backend_pid()" >/dev/null 2>&1 || true

if ! psql_en postgres -q -c "drop database if exists \"$BASE\""; then
  rojo "FALLA · no se pudo borrar la base '$BASE'."
  exit 1
fi
if ! psql_en postgres -q -c "create database \"$BASE\" owner \"$USUARIO\""; then
  rojo "FALLA · no se pudo crear la base '$BASE'."
  exit 1
fi

# ------------------------------------------------------------
#  4 · Restaurar
# ------------------------------------------------------------
# `--no-owner --no-privileges`: el dump se tomo igual, y asi la base
# restaurada queda del usuario que la crea sin depender de que los
# roles del original existan aca.
#
# No lleva `--exit-on-error`: pg_restore avisa de cosas que no son
# errores reales —una extension que ya existe, un rol que no hace
# falta— y cortar ahi marcaria como fallidas restauraciones buenas.
# Lo que decide si salio bien es el conteo de filas de mas abajo, que
# es la pregunta que importa.
salida="$(docker compose exec -T "$SERVICIO_DB" \
  pg_restore -U "$USUARIO" -d "$BASE" --no-owner --no-privileges \
  "/respaldos_interno/$RELATIVA" 2>&1 </dev/null)"
codigo=$?

if [ -n "$salida" ]; then
  gris "pg_restore dijo:"
  printf '%s\n' "$salida" | sed 's/^/    /' | head -20
fi

# ------------------------------------------------------------
#  5 · Contar las filas de las dos bases
# ------------------------------------------------------------
# Se cuenta de verdad, tabla por tabla. `n_live_tup` de
# `pg_stat_user_tables` es una estimacion del recolector y despues de
# restaurar todavia dice cero: serviria para quedarse tranquilo sin
# motivo.
armar_consulta() {
  psql_en "$1" -At -c "
    select string_agg(
      format('select %L as tabla, count(*) as filas from %I.%I',
             table_name, table_schema, table_name),
      ' union all ' order by table_name)
    from information_schema.tables
    where table_schema in ('public','auth') and table_type = 'BASE TABLE'"
}

CONSULTA="$(armar_consulta "$ORIGEN")"
if [ -z "$CONSULTA" ]; then
  rojo "FALLA · la base de origen '$ORIGEN' no tiene tablas. Algo esta muy mal."
  exit 1
fi

filas_de() { psql_en "$1" -At -F '|' -c "$CONSULTA" | sort; }

ANTES="$(filas_de "$ORIGEN")"
DESPUES="$(filas_de "$BASE")"

echo
printf '%-28s %10s %12s\n' "TABLA" "ORIGEN" "RESTAURADA"
printf '%-28s %10s %12s\n' "----------------------------" "----------" "------------"

DIFERENCIAS=0
TOTAL=0
while IFS='|' read -r tabla filas; do
  [ -n "$tabla" ] || continue
  TOTAL=$((TOTAL + 1))
  restaurada="$(printf '%s\n' "$DESPUES" | awk -F'|' -v t="$tabla" '$1==t{print $2}')"
  restaurada="${restaurada:-AUSENTE}"
  if [ "$restaurada" = "$filas" ]; then
    printf '%-28s %10s %12s\n' "$tabla" "$filas" "$restaurada"
  else
    printf '\033[31m%-28s %10s %12s  <- DIFIERE\033[0m\n' "$tabla" "$filas" "$restaurada"
    DIFERENCIAS=$((DIFERENCIAS + 1))
  fi
done <<< "$ANTES"

echo
if [ "$DIFERENCIAS" -gt 0 ]; then
  rojo "FALLA · $DIFERENCIAS de $TOTAL tabla(s) no coinciden. La restauracion NO sirve."
  exit 1
fi

if [ "$codigo" -ne 0 ]; then
  gris "(pg_restore salio con codigo $codigo, pero las $TOTAL tablas coinciden)"
fi

verde "OK · '$BASE' tiene exactamente las mismas filas que '$ORIGEN', en las $TOTAL tablas"
echo
gris "Para que la aplicacion la use, en .env:  DATABASE_URL=...@db:5432/$BASE"

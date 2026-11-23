#!/usr/bin/env bash
# ============================================================
#  Respaldo verificado de la base · F18-T01
#
#  Uso:
#      ./scripts/respaldo.sh                 # respaldo del dia
#      ./scripts/respaldo.sh --etiqueta pre-F17   # respaldo de tarea
#      ./scripts/respaldo.sh --solo-verificar <archivo>
#
#  LO IMPORTANTE DE ESTE SCRIPT ES LA PALABRA «VERIFICADO»
#
#  Escribir un dump es facil y sale bien casi siempre. El problema
#  es el «casi»: un disco lleno, un contenedor que se reinicia a
#  mitad de camino o una base que corta la conexion dejan un
#  archivo que existe, pesa algo y NO SIRVE. Y nadie se entera
#  hasta el dia que hace falta.
#
#  Asi que despues de escribirlo, este script lo ABRE con
#  `pg_restore --list`, cuenta las tablas que encuentra y exige un
#  minimo. Si no abre o trae menos tablas de las esperadas, borra
#  el archivo fallado y sale con error. Un respaldo que no se pudo
#  leer no queda guardado dando una falsa sensacion de seguridad.
#
#  RETENCION
#      7 diarios · 4 semanales (lunes) · 6 mensuales (dia 1)
#  Son 17 archivos vivos y el mas viejo tiene medio ano. A 40 MB
#  cada uno es menos de 1 GB: no hay motivo para ser tacano.
#
#  SALIDA
#      respaldos/diario/epic_wallet_AAAA-MM-DD_HHMM.dump
#      respaldos/semanal/...
#      respaldos/mensual/...
#      respaldos/tarea/epic_wallet_AAAA-MM-DD_HHMM_<etiqueta>.dump
#      respaldos/ultimo.json   <- lo lee /api/health y el porton de F18-T04
#
#  Los respaldos de tarea NO los borra la retencion: son la red
#  para volver atras una tarea concreta y se limpian a mano.
# ============================================================
set -uo pipefail

cd "$(dirname "$0")/.."
RAIZ="$(pwd)"

DESTINO="${RESPALDOS_DIR:-$RAIZ/respaldos}"
SERVICIO_DB="${SERVICIO_DB:-db}"

# Cuantas tablas tiene que listar el dump para considerarse sano.
# Son 9 de datos + auth.users + alembic_version. Se pide menos que
# eso a proposito: el numero exacto cambia con cada migracion y lo
# que importa es distinguir «trae el esquema» de «vino vacio».
MINIMO_DE_TABLAS="${MINIMO_DE_TABLAS:-8}"

ETIQUETA=""
SOLO_VERIFICAR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --etiqueta)
      ETIQUETA="${2:-}"
      [ -n "$ETIQUETA" ] || { echo "ERROR: --etiqueta necesita un nombre" >&2; exit 2; }
      shift 2
      ;;
    --solo-verificar)
      SOLO_VERIFICAR="${2:-}"
      [ -n "$SOLO_VERIFICAR" ] || { echo "ERROR: --solo-verificar necesita un archivo" >&2; exit 2; }
      shift 2
      ;;
    -h|--help)
      sed -n '2,45p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "ERROR: argumento desconocido: $1" >&2
      exit 2
      ;;
  esac
done

rojo()  { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }

# ------------------------------------------------------------
#  Datos de la base, del .env del proyecto
# ------------------------------------------------------------
leer_env() {
  # No se usa `source`: el .env puede tener valores con espacios o
  # con caracteres que la shell interpretaria.
  [ -f "$RAIZ/.env" ] || return 0
  sed -n "s/^$1=//p" "$RAIZ/.env" | head -1
}

USUARIO="$(leer_env POSTGRES_USER)"
BASE="$(leer_env POSTGRES_DB)"
USUARIO="${POSTGRES_USER:-${USUARIO:-epic}}"
BASE="${POSTGRES_DB:-${BASE:-epic_wallet}}"

# ------------------------------------------------------------
#  Verificar: abrir el archivo y contar sus tablas
# ------------------------------------------------------------
verificar() {
  local archivo="$1"

  if [ ! -s "$archivo" ]; then
    rojo "FALLA · el archivo no existe o esta vacio: $archivo"
    return 1
  fi

  # La ruta que ve el contenedor es relativa a la carpeta de
  # respaldos: `diario/epic_wallet_....dump`.
  #
  # Se pasa a absoluta primero. Sin eso, un argumento relativo
  # —`respaldos/diario/x.dump`, que es como se escribe a mano— no
  # coincidia con $DESTINO, no se recortaba nada, y pg_restore
  # buscaba `/respaldos_interno/respaldos/diario/x.dump`. El error
  # que salia era «no such file», o sea el script decia que el
  # archivo estaba mal cuando lo que estaba mal era la ruta.
  local absoluta
  absoluta="$(cd "$(dirname "$archivo")" 2>/dev/null && pwd)/$(basename "$archivo")"
  local relativa="${absoluta#"$DESTINO"/}"
  if [ "$relativa" = "$absoluta" ]; then
    rojo "FALLA · el archivo no esta dentro de $DESTINO: $archivo"
    return 1
  fi

  local listado
  if ! listado="$(docker compose exec -T "$SERVICIO_DB" \
        pg_restore --list "/respaldos_interno/$relativa" 2>&1)"; then
    rojo "FALLA · pg_restore no pudo abrir el archivo"
    echo "$listado" | tail -5 | sed 's/^/    /'
    return 1
  fi

  local tablas
  tablas="$(printf '%s\n' "$listado" | grep -c 'TABLE DATA')"
  if [ "$tablas" -lt "$MINIMO_DE_TABLAS" ]; then
    rojo "FALLA · el dump abre pero trae $tablas tablas, y se esperaban $MINIMO_DE_TABLAS o mas"
    return 1
  fi

  verde "OK · el archivo abre y lista $tablas tablas"
  return 0
}

if [ -n "$SOLO_VERIFICAR" ]; then
  verificar "$SOLO_VERIFICAR"
  exit $?
fi

# ------------------------------------------------------------
#  Respaldar
# ------------------------------------------------------------
mkdir -p "$DESTINO/diario" "$DESTINO/semanal" "$DESTINO/mensual" "$DESTINO/tarea"

MARCA="$(date +%Y-%m-%d_%H%M)"
if [ -n "$ETIQUETA" ]; then
  SUBCARPETA="tarea"
  NOMBRE="epic_wallet_${MARCA}_${ETIQUETA}.dump"
else
  SUBCARPETA="diario"
  NOMBRE="epic_wallet_${MARCA}.dump"
fi
ARCHIVO="$DESTINO/$SUBCARPETA/$NOMBRE"

echo "Respaldando '$BASE' -> $ARCHIVO"

# El dump se escribe DENTRO del contenedor, en el volumen que
# tambien ve esta maquina: asi `pg_restore --list` lo lee despues
# sin copiarlo a ningun lado. `-Fc` es el formato propio de
# Postgres: comprimido y restaurable tabla por tabla.
if ! docker compose exec -T "$SERVICIO_DB" sh -c \
      "pg_dump -U '$USUARIO' -d '$BASE' -Fc --no-owner --no-privileges \
       -f '/respaldos_interno/$SUBCARPETA/$NOMBRE'" ; then
  rojo "FALLA · pg_dump no termino bien. No queda ningun archivo a medias."
  rm -f "$ARCHIVO"
  exit 1
fi

if [ ! -s "$ARCHIVO" ]; then
  rojo "FALLA · pg_dump dijo que si, pero el archivo no aparecio en $DESTINO"
  rojo "        Revisa que el volumen de respaldos este montado en el compose."
  exit 1
fi

TAMANIO="$(du -h "$ARCHIVO" | cut -f1)"
echo "Escrito: $TAMANIO"

# ------------------------------------------------------------
#  Y recien ahora, verificarlo
# ------------------------------------------------------------
if ! docker compose exec -T "$SERVICIO_DB" \
      pg_restore --list "/respaldos_interno/$SUBCARPETA/$NOMBRE" >/tmp/listado.$$ 2>&1; then
  rojo "FALLA · el dump se escribio pero NO SE PUEDE ABRIR. Se borra."
  tail -5 /tmp/listado.$$ | sed 's/^/    /'
  rm -f "$ARCHIVO" /tmp/listado.$$
  exit 1
fi

TABLAS="$(grep -c 'TABLE DATA' /tmp/listado.$$ || true)"
rm -f /tmp/listado.$$

if [ "${TABLAS:-0}" -lt "$MINIMO_DE_TABLAS" ]; then
  rojo "FALLA · el dump abre pero trae $TABLAS tablas, y se esperaban $MINIMO_DE_TABLAS o mas."
  rojo "        Un respaldo incompleto no queda guardado. Se borra."
  rm -f "$ARCHIVO"
  exit 1
fi

verde "OK · verificado: abre y trae $TABLAS tablas con datos"

# ------------------------------------------------------------
#  Copias semanales y mensuales
# ------------------------------------------------------------
if [ -z "$ETIQUETA" ]; then
  # Lunes: copia semanal. Dia 1: copia mensual. Son copias y no
  # enlaces: un enlace al diario desaparece cuando la retencion
  # borra el diario, y entonces la copia semanal nunca existio.
  [ "$(date +%u)" = "1" ] && cp "$ARCHIVO" "$DESTINO/semanal/$NOMBRE"
  [ "$(date +%d)" = "01" ] && cp "$ARCHIVO" "$DESTINO/mensual/$NOMBRE"

  # ----------------------------------------------------------
  #  Retencion
  # ----------------------------------------------------------
  # Se ordena por nombre, que empieza con la fecha en formato
  # AAAA-MM-DD: ordenar por nombre es ordenar por fecha, y no
  # depende de la fecha de modificacion del archivo, que una copia
  # o un `rsync` pueden cambiar.
  limpiar() {
    local carpeta="$1" cuantos="$2" borrados=0
    local sobrantes
    sobrantes="$(ls -1 "$carpeta"/*.dump 2>/dev/null | sort | head -n -"$cuantos")"
    [ -n "$sobrantes" ] || return 0
    while IFS= read -r viejo; do
      rm -f "$viejo"
      borrados=$((borrados + 1))
    done <<< "$sobrantes"
    echo "  $(basename "$carpeta"): $borrados borrado(s), se guardan $cuantos"
  }
  echo "Retencion:"
  limpiar "$DESTINO/diario" 7
  limpiar "$DESTINO/semanal" 4
  limpiar "$DESTINO/mensual" 6
fi

# ------------------------------------------------------------
#  Dejar constancia de que este respaldo existe y esta sano
# ------------------------------------------------------------
# Lo lee `/api/health` (F18-T06) y el porton que se niega a migrar
# sin respaldo fresco (F18-T04). Se escribe DESPUES de verificar,
# nunca antes: si se escribiera antes, un respaldo fallado dejaria
# constancia de exito.
cat > "$DESTINO/ultimo.json" <<JSON
{
  "archivo": "$SUBCARPETA/$NOMBRE",
  "fecha": "$(date -Iseconds)",
  "tablas": $TABLAS,
  "bytes": $(wc -c < "$ARCHIVO"),
  "etiqueta": "${ETIQUETA:-diario}",
  "verificado": true
}
JSON

verde "LISTO · $ARCHIVO ($TAMANIO)"

#!/usr/bin/env bash
# ============================================================
#  Verifica que el proyecto no nombre ni dependa de los
#  proveedores externos de los que se mudó (F14).
#
#  Uso:  ./scripts/sin_proveedores.sh            (todo el repositorio)
#        ./scripts/sin_proveedores.sh --docs     (solo documentacion)
#
#  SIN ARGUMENTOS REVISA TODO, Y HOY FALLA A PROPOSITO: el codigo
#  todavia esta atado al proveedor anterior. Esa es la reja final,
#  la que tiene que pasar cuando termine F17. `--docs` revisa solo
#  lo que se escribe para leer, que es lo que cerro F14.
#
#  POR QUÉ ESTE ARCHIVO EXISTE
#  Los nombres de los proveedores tienen que estar escritos en
#  algún lado para poder buscarlos. Que estén acá y en ningún
#  otro lugar es lo que permite que la documentación quede
#  limpia: el resto de los documentos dicen «ejecutar este
#  script», no el nombre.
#
#  Este archivo y `documentacion/04_Migracion_a_Contabo.md` son
#  las dos únicas excepciones, y los dos se borran cuando el
#  traslado termine.
# ============================================================
set -uo pipefail

cd "$(dirname "$0")/.."

# Lo que no puede aparecer en ningún archivo versionado.
PATRONES='vercel|supabase|gotrue|sb_publishable_|sb_secret_'

# Lo que sí puede nombrarlos, por lo dicho arriba.
EXCEPCIONES='^scripts/sin_proveedores\.sh$|^documentacion/04_Migracion_a_Contabo\.md$'

# `--docs` limita la busqueda a lo que se lee, no a lo que corre.
SOLO_DOCS=0
if [ "${1:-}" = "--docs" ]; then
  SOLO_DOCS=1
fi
DOCS='^(documentacion/|docs/|README\.md$|CLAUDE\.md$)'

if [ "$SOLO_DOCS" -eq 1 ]; then
  echo "Buscando referencias a proveedores externos en la documentacion..."
else
  echo "Buscando referencias a proveedores externos en lo versionado..."
fi

hallazgos=0
while IFS= read -r archivo; do
  if [ "$SOLO_DOCS" -eq 1 ] && [[ ! "$archivo" =~ $DOCS ]]; then
    continue
  fi
  if [[ "$archivo" =~ $EXCEPCIONES ]]; then
    continue
  fi
  if coincidencias=$(grep -n -iE "$PATRONES" -- "$archivo" 2>/dev/null); then
    echo
    echo "  $archivo"
    echo "$coincidencias" | sed 's/^/    /'
    hallazgos=$((hallazgos + 1))
  fi
done < <(git ls-files)

echo
if [ "$hallazgos" -eq 0 ]; then
  if [ "$SOLO_DOCS" -eq 1 ]; then
    echo "OK · ningún documento nombra un proveedor externo."
  else
    echo "OK · ningún archivo versionado nombra un proveedor externo."
  fi
  exit 0
fi

echo "FALLA · $hallazgos archivo(s) todavía los nombran."
exit 1

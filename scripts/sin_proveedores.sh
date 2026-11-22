#!/usr/bin/env bash
# ============================================================
#  Verifica que el proyecto no nombre ni dependa de los
#  proveedores externos de los que se mudó (F14).
#
#  Uso:  ./scripts/sin_proveedores.sh
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

echo "Buscando referencias a proveedores externos en lo versionado..."

hallazgos=0
while IFS= read -r archivo; do
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
  echo "OK · ningún archivo versionado nombra un proveedor externo."
  exit 0
fi

echo "FALLA · $hallazgos archivo(s) todavía los nombran."
exit 1

# ============================================================
#  Compila el frontend y termina.
#
#  Contenedor efímero: no queda corriendo ni deja Node en el
#  servidor. Copia `web/` ya compilado al volumen que sirve el
#  proxy de borde.
#
#  El contexto de build es la RAÍZ del repositorio.
# ============================================================
FROM node:20-alpine

WORKDIR /build

# Dependencias primero: mientras el lockfile no cambie, Docker reusa
# esta capa.
COPY package.json package-lock.json ./
RUN npm ci

# El código del frontend y los scripts del build.
COPY web/ ./web/
COPY scripts/ ./scripts/

# Genera web/public/app.css y web/public/config.js.
#
# Si faltan las variables del proveedor de autenticación, el build NO
# falla: escribe una configuración vacía y avisa. Es a propósito —ver
# scripts/generar-config.mjs—. Hasta F17 el servidor propio no las
# tiene, así que la aplicación se publica y se ve, pero nadie puede
# iniciar sesión todavía.
RUN npm run build

CMD ["sh", "-c", "rm -rf /destino/* /destino/.[!.]* 2>/dev/null; cp -a /build/web/. /destino/"]

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

# Compila Tailwind a web/public/app.css. Es todo lo que hace el build.
#
# Hasta F17-T03 generaba además un `config.js` con la URL y la clave
# del proveedor de autenticación, porque el frontend las necesitaba
# para hablarle. Ahora el login es nuestro y vive en el mismo origen:
# no hay ninguna configuración que pasarle al navegador.
RUN npm run build

CMD ["sh", "-c", "rm -rf /destino/* /destino/.[!.]* 2>/dev/null; cp -a /build/web/. /destino/"]

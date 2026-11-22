# Traslado a Contabo — Epic Wallet 3.0

Qué es la 3.0, por qué se mueve y cómo. Este documento manda sobre el
traslado; cuando termine, lo que quede en pie se absorbe en el
`02_Documento_Tecnico.md` y este archivo se borra.

## Por qué

La 2.0 vive en Vercel + Supabase. Funciona, pero los respaldos y el
control de la base dependen de un tercero y de su plan. La 3.0 es la
misma aplicación corriendo en un VPS propio, donde el respaldo es un
archivo que se puede copiar, verificar y restaurar.

**La 2.0 sigue viva y es intocable** hasta que el corte esté aprobado:
ni un push, ni una migración, ni un cambio de variable. Leer está bien;
escribir, no.

## El servidor

| | |
|---|---|
| Proveedor | Contabo, `vmi3573476` |
| Región | US-east (~130-160 ms desde Argentina; Contabo no tiene Sudamérica) |
| Recursos | 4 vCPU · 7,8 GB RAM · 96 GB disco |
| IP | `13.140.36.93` |
| Dominio | `13-140-36-93.sslip.io` — DNS público, sin registro ni vencimiento |
| TLS | Let's Encrypt, renovado solo por Caddy |
| Convive con | Jarvis (Postgres 16 propio, red propia). Bases separadas |

## Las tres decisiones

**1 · Autenticación propia en FastAPI.** Se descartó GoTrue
autohospedado y el stack completo de Supabase. Seis endpoints nuestros,
tabla `auth.users` propia, firma ES256 con par de claves propio. Se
conserva la firma asimétrica del diseño original: quien tenga el
servidor no puede fabricar sesiones con un secreto compartido.

**2 · Postgres 17 en Docker Compose**, con volumen propio, junto a la
API y detrás del proxy compartido.

**3 · Migración por `pg_dump` de `public` + `auth.users`.** Conserva los
identificadores y los hashes bcrypt: **nadie tiene que resetear su
contraseña**.

## El atajo que hace esto barato

El acoplamiento a Supabase son tres puntos: `auth.users`, `auth.uid()` y
GoTrue. Recreando `auth.uid()` como función propia que lee el mismo GUC
`request.jwt.claims` —que ya setea `core/db.py`— y quedándonos con
`auth.users` como tabla nuestra, **las 12 migraciones, las 9 políticas
RLS y `core/db.py` no se tocan**.

En el frontend pasa lo mismo: `web/src/js/auth.js` es el único archivo
que sabe de Supabase. Los otros 50 módulos no se enteran del cambio.

## Sin correo, a propósito

No hay SMTP y no va a haberlo: a esta escala es resolver un problema
que no existe. La recuperación de contraseña se hace desde el servidor,

    docker compose exec api python -m app.cli recuperar <email>

que imprime un link de un solo uso, válido 30 minutos, contra la
pantalla `#/nueva-clave` **que ya existe**. El link se entrega a mano.
Cambiar la contraseña desde Ajustes sigue pidiendo la actual.

## Fases

| | Qué | Verificación |
|---|---|---|
| F00 | Repo v3: sacar Vercel y Supabase, documentación y roadmap de la 3.0 | `pytest` y `npm test` en verde sin credenciales de Supabase |
| F01 | Servidor: swap, firewall, proxy de borde compartido, TLS | `https://13-140-36-93.sslip.io` con candado, Jarvis sigue arriba |
| F02 | Shim de `auth` en Postgres: roles, `auth.uid()`, `auth.users` | las 12 migraciones corren limpias sobre Postgres puro |
| F03 | Auth propia + `auth.js` nuevo + comando de recuperación | entrar, salir, renovar token y cambiar clave, desde el celular |
| F04 | Respaldos de Epic Wallet y de Jarvis | **una restauración probada de verdad**, no un dump que nadie leyó |
| F05 | Importar los datos reales y cortar | los totales del tablero coinciden con los de la 2.0 |

El orden no es negociable en un punto: **F04 antes que F05**. No entran
datos reales a un servidor que todavía no demostró que los puede
devolver.

## Qué se baja de Supabase (sólo lectura)

```bash
# Datos de la aplicación
pg_dump "<cadena>" --schema=public --no-owner --no-privileges -Fc -f epic_public.dump

# Identidades: sólo auth.users, sólo datos (acá están los bcrypt)
pg_dump "<cadena>" --table=auth.users --data-only --no-owner -Fc -f epic_auth_users.dump

# Red de seguridad legible, desde la aplicación
GET /api/export?format=json
```

## Lo que se va del proyecto

`vercel.json`, `.vercelignore`, `api/index.py`, `@supabase/auth-js` y su
copia en `web/src/js/vendor/`, las variables `SUPABASE_*`, el `NullPool`
y el `prepare_threshold=None` que existían por el pooler en modo
transacción, y `*.supabase.co` de la CSP.

Y algo que importa más de lo que parece: hoy `tests/api/` pega contra el
Supabase real con la clave de servicio. En la 3.0 corre contra la base
local. **Las pruebas dejan de tocar producción.**

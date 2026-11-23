# Epic Wallet 3.0

Aplicación personal de gestión financiera. Reemplaza un Excel de varios años. Web responsive + PWA, **prioridad celular**.

La 3.0 es la misma aplicación, **corriendo en un servidor propio**. Se mueve para que el respaldo sea un archivo que podamos copiar, verificar y restaurar, y no un plan de un tercero.

**Escala real: pocos usuarios conocidos**, cada uno con sus propios datos de contabilidad. No es un producto público. Toda decisión se toma a esa escala: lo simple gana.

## La versión anterior es intocable

La versión anterior sigue viva, en los servicios de terceros donde se construyó, y es **el único sistema que hoy funciona**. Hasta que el corte esté aprobado:

- Ni un push a su repositorio, ni una migración, ni un cambio de variable de entorno, ni un script que escriba.
- **Leer está bien** (`pg_dump`, `GET /api/export`). Escribir, no.
- Si algo pareciera necesitar un cambio allá, **se frena y se pregunta**, diciendo qué tabla, qué filas y por qué.

Esta carpeta apunta a `Epic_Wallet_v3` y no tiene forma de alcanzar el repositorio anterior. Que siga así.

## Documentos que mandan

| Archivo | Qué contiene |
|---|---|
| `documentacion/01_Documento_General.md` | **Qué** hace la aplicación. El modelo financiero |
| `documentacion/02_Documento_Tecnico.md` | **Cómo**. Stack, modelo de datos, API, estilo |
| `documentacion/03_Roadmap.md` | **Qué sigue.** Única fuente de tareas. Ninguna tarea se ejecuta fuera de acá |
| `documentacion/04_Migracion_a_Contabo.md` | El traslado: servidor, decisiones y fases. Se borra cuando termine |
| `.claude/skills/epic-wallet-ui/SKILL.md` | Sistema de diseño «Vidrio Grafito». **Cargarlo antes de tocar cualquier HTML, CSS o JS de interfaz** |

## Forma de trabajar

1. **Una tarea del roadmap a la vez.** No adelantar fases.
2. **Dentro de la tarea: cálculo → backend → frontend.** Funciones puras con sus tests, después el endpoint, después la interfaz.
3. **Se para y se espera.** Al terminar una tarea: publicarla en Contabo, decirle a Gustavo **qué tocar y qué tendría que ver**, y **detenerse ahí**. No se empieza la siguiente hasta que él conteste. La tarea queda en `- [~]` y pasa a `- [x]` **sólo cuando él lo dice**.
4. **Se prueba en `https://13-140-36-93.sslip.io`, desde el celular.** Las pruebas automáticas corren contra la base local de pruebas y nunca contra datos reales; Gustavo prueba en Contabo. Son dos cosas distintas y no se confunden.
5. **Un respaldo por tarea, antes de empezar.** Si la tarea toca la base o los datos: **respaldo primero, una sola vez, antes del primer cambio.** No uno por cambio. Si al terminar funciona, se sigue; si no, se vuelve todo atrás con ese archivo. El respaldo del día va al servidor **y** a la carpeta de respaldos.
6. **Escribir corto.** Las entradas del roadmap son «qué hacer» y «cómo se verifica». Sin ensayos, sin relato de los errores encontrados.

> La regla 3 se incumplió durante F14 a F17: se avisaba qué probar pero se seguía con la tarea siguiente sin esperar. Explicitada el 2026-11-23 a pedido de Gustavo.

## Qué se testea y qué no

Se testea **lo que da un número o protege un dato**: `services/calc.py`, el recálculo del mes, los casos borde (ingresos en cero, mes vacío), y que una cuenta no vea los datos de otra.

**No se testea** la estructura del HTML, los tokens de CSS, el contraste, la configuración del despliegue ni el contenido de la documentación. Eso se verifica mirando la pantalla en el celular.

Criterio para el futuro: *si el test falla, ¿me enteré de algo que la pantalla no me hubiera mostrado?* Si no, el test no se escribe. No hay exigencia de cobertura.

**Las pruebas corren contra la base local.** Antes, `tests/api/` pegaba contra el servidor real del proveedor con su clave de servicio. Eso se termina en F16-T03: ninguna prueba toca un servidor de verdad.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic. Capas: `routers` → `services` → `repos` → `core`. Todo cálculo financiero es una **función pura** en `services/calc.py`.
- **Frontend:** HTML + Tailwind v4 + JavaScript ES2022 con módulos nativos. **Sin React ni bundler.** Gráficos en SVG propio, sin Chart.js. Una página, seis vistas, enrutado por hash.
- **Base:** Postgres 17 en Docker, volumen propio, **un solo esquema (`public`)**.
- **Auth:** propia, en FastAPI. JWT firmado **ES256** con par de claves del proyecto; se verifica con la pública. Sin proveedor externo.
- **Servidor:** VPS de Contabo (`13.140.36.93`), Docker Compose detrás de un Caddy compartido con Jarvis. TLS de Let's Encrypt, renovado solo.

## Cosas que no se pueden romper

- **Las dos naturalezas de mes.** Un mes `open` saca sus totales de `transactions`; un mes `historical` de sus propios campos y devuelve **`transactions: null`** — distinto de `[]`. Nunca se inventan movimientos para un mes consolidado.
- **Aislamiento entre cuentas.** `user_id` en toda consulta **y RLS activo** en cada tabla de datos de usuario, incluidas las nuevas. Es la única exigencia de seguridad que no se negocia. `auth.uid()` ahora es una función nuestra, pero las políticas no cambian.
- **El `.env` de la carpeta de trabajo tiene credenciales de producción de la versión anterior**, incluida la clave que se saltea el aislamiento. Ninguna prueba las usa desde F16-T03 y **no se usan para nada**. Si siguen ahí, se las ignora; no son una puerta habilitada.
- **Los datos reales que Gustavo ya cargó no se tocan.** Ningún fix, migración ni script corre un `DELETE`, `TRUNCATE` o `DROP` contra la base real sin explicar antes qué se va a borrar (tabla, filas, motivo) y esperar su confirmación explícita — nunca como efecto secundario de otra cosa. No aplica a las cuentas de prueba que se crean y se borran dentro de una misma tarea de QA, ni a lo que la aplicación ya le permite hacer desde la interfaz (borrar un movimiento, vender una inversión — Reglas 10 y 11 del documento general): eso sigue funcionando como está diseñado.
- **Jarvis convive en el mismo servidor.** Base propia, red propia, volumen propio. Epic Wallet no comparte base con nadie y no toca los contenedores de Jarvis.
- **Importes en `numeric(14,2)`** en la base y `Decimal` en Python. Nunca `float`.
- **Una sola llamada para el dashboard** (`GET /api/dashboard`), por debajo de 400 ms.
- **Tasa de ahorro con ingresos en cero devuelve `null`**, no un error ni una división.
- **Comprar una inversión no es un gasto** y no cambia el patrimonio neto: mueve su composición.
- **Ningún color escrito a mano.** Todo sale de los tokens de `web/src/styles/tokens.css`.

## Migraciones: el procedimiento es el que protege los datos

Hay un solo esquema, así que **una migración toca los datos reales**.

> **`scripts/respaldo.sh` y `scripts/restaurar.sh` todavía no existen** —los escribe F18—. Hasta entonces el paso 1 de abajo no se puede ejecutar, y por lo tanto **no se migra la base real**. F18-T04 hace que el propio Alembic se niegue a correr sin un respaldo fresco, para que esto deje de depender de que alguien se acuerde.

```bash
# 1 · respaldo primero, y verificar que el archivo tiene algo adentro
./scripts/respaldo.sh && ls -lh respaldos/
# 2 · generar y REVISAR el archivo a mano
DB_SCHEMA=public APP_ENV=production alembic revision --autogenerate -m "F03 meses"
# 3 · aplicar
DB_SCHEMA=public APP_ENV=production alembic upgrade head
# 4 · verificar con /api/health, y recién entonces publicar el código
```

`DB_SCHEMA` y `APP_ENV` van explícitos: `migrations/env.py` los exige a propósito. Toda migración lleva su `downgrade` escrito y revisado. Respaldo → migrar → publicar, nunca al revés.

## Comandos

```bash
npm run build          # compila Tailwind a web/public/app.css
npm run dev            # Tailwind en modo watch
pytest                 # tests
ruff check . && mypy . # linter y tipos
cd api && uvicorn app.main:app --reload --port 8000

# en el servidor
ssh jarvis-vps
cd /opt/epic-wallet && docker compose ps
docker compose exec api python -m app.cli recuperar <email>   # link de contraseña nueva
./scripts/respaldo.sh                                          # dump verificado
```

## Convenciones

- **Tablas y columnas en inglés**, `snake_case` (es lo que define el DDL en Postgres). **El resto del código —funciones, clases, variables, docstrings— va en español**, como ya está en `routers/`, `schemas/` y `core/`. **Textos visibles y documentación en español** (voseo argentino: «podés», «tenés»).
- Commits: `tipo(F0X-TYY): descripción en minúscula`. Tipos: `feat`, `fix`, `docs`, `chore`, `merge`.
- Importes se muestran en pesos argentinos con `tabular-nums` para que las cifras no cambien de ancho.
- Zona horaria de presentación: `America/Argentina/Buenos_Aires`.

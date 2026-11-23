# Epic Wallet 3.0

Aplicación personal de gestión financiera. Web responsive y PWA, **pensada primero para el celular** y con un dashboard completo en PC.

Reemplaza la planilla de Excel que vengo usando hace años: conserva su lógica financiera y su simplicidad de uso, y le agrega lo que el Excel no da cómodamente —ver cómo vengo, cómo evolucioné, dónde gasté, cuánto ahorro, cuánto vale mi patrimonio y cómo están mis inversiones.

> **Selecciono una categoría, pongo un importe y sigo con mi día.**

---

## Estado del proyecto

**La aplicación está construida y se usa.** Catorce fases cerradas: cuentas, meses, movimientos, los seis indicadores, los cinco gráficos, histórico, patrimonio, inversiones, escritorio y vencimientos.

**Lo que está en curso es el traslado a un servidor propio** (fases 14 a 19): el respaldo de años de contabilidad deja de depender del plan de un tercero y pasa a ser un archivo que podemos copiar, verificar y restaurar.

El avance tarea por tarea está en [`documentacion/03_Roadmap.md`](documentacion/03_Roadmap.md) y el plan del traslado en [`documentacion/04_Migracion_a_Contabo.md`](documentacion/04_Migracion_a_Contabo.md).

---

## Documentación

Leerla en este orden:

| Documento | Qué contiene |
|---|---|
| [`documentacion/01_Documento_General.md`](documentacion/01_Documento_General.md) | **Qué** hace la aplicación. Especificación funcional completa: modelo financiero, reglas de negocio, pantallas, alcance. |
| [`documentacion/02_Documento_Tecnico.md`](documentacion/02_Documento_Tecnico.md) | **Cómo** se construye. Stack, arquitectura, esquema de datos, contratos de API, sistema de estilo, despliegue y seguridad. |
| [`documentacion/03_Roadmap.md`](documentacion/03_Roadmap.md) | **En qué orden.** Única fuente de tareas; ninguna se ejecuta fuera de ahí. |
| [`documentacion/04_Migracion_a_Contabo.md`](documentacion/04_Migracion_a_Contabo.md) | El traslado al servidor propio. Se borra cuando termine. |
| [`documentacion/mockups/01_Mockup_V1_Grafito_Clasico.html`](documentacion/mockups/01_Mockup_V1_Grafito_Clasico.html) | Diseño aprobado. Se abre con doble clic y es funcional. |
| `docs/` | `COMO_FUNCIONA.md` y los documentos de cierre de las primeras fases. |

Si el documento técnico contradice al general en una decisión funcional, gana el general. Si el general propone una tecnología y el técnico decide otra, gana el técnico y la desviación queda registrada en su sección 4.

---

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | HTML5 · Tailwind CSS v4 · JavaScript (módulos ES) · SVG propio para gráficos · PWA |
| Backend | Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 · Alembic |
| Base de datos | Postgres 17 en contenedor, volumen propio · SQLite sólo para los tests de cálculo |
| Autenticación | Propia: bcrypt para las contraseñas, JWT ES256 con el par de claves del proyecto |
| Servidor | VPS propio con Docker · Caddy como proxy, con TLS automático |

**Sin React, Vue ni Angular, y sin dependencias de terceros en el frontend.** Los detalles y el porqué de cada elección están en el documento técnico.

---

## Estructura

```text
epic-wallet/
├── api/                      # backend (FastAPI sobre uvicorn)
│   └── app/
│       ├── main.py           # creación de FastAPI, middlewares, errores
│       ├── core/             # configuración, base de datos, seguridad, errores
│       ├── models/           # modelos SQLAlchemy
│       ├── schemas/          # esquemas Pydantic (entrada y salida)
│       ├── repos/            # consultas
│       ├── services/         # reglas de negocio y cálculos
│       │   └── prices/       # proveedores de cotizaciones
│       └── routers/          # un archivo por recurso
├── web/                      # frontend estático
│   ├── index.html
│   ├── manifest.json
│   ├── service-worker.js
│   ├── icons/
│   ├── public/               # CSS compilado y config.js (no se versionan)
│   └── src/
│       ├── styles/           # tokens, base y componentes
│       └── js/               # router, api, estado, gráficos, componentes, vistas
├── migrations/               # Alembic
├── scripts/                  # siembra, carga de histórico, respaldo, verificaciones
├── tests/                    # unit · api · js
├── docs/                     # documentación del proyecto
└── documentacion/            # especificación funcional, técnica, roadmap y mockups
```

Las cuatro capas del backend (router → service → repo → core) y la regla de que **todo cálculo financiero es una función pura** están explicadas en la sección 5.1 del documento técnico.

---

## Levantar el proyecto en tu máquina

### Requisitos

- Python 3.12 o superior
- Node.js 20 o superior
- Docker (para la base de datos)
- Git

### Pasos

```bash
# 1 · Clonar
git clone git@github.com:gusoliva85/Epic_Wallet_v3.git epic-wallet
cd epic-wallet

# 2 · Backend: entorno virtual y dependencias
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 3 · Frontend: dependencias y compilación del CSS
npm install
npm run build                    # genera web/public/app.css minificado

# 4 · Variables de entorno
cp .env.example .env             # y completar los valores

# 5 · Base de datos local
docker compose -f docker-compose.yml -f docker-compose.desarrollo.yml up -d db
DB_SCHEMA=public APP_ENV=development alembic upgrade head

# 6 · Levantar
cd api && uvicorn app.main:app --reload --port 8000
npm run dev                                      # CSS en modo watch, en otra terminal
```

### Sobre el CSS

`web/public/app.css` **no se versiona**: lo genera el build. `npm run build` lo compila minificado y `npm run dev` lo deja en modo watch mientras trabajás.

### Sobre las migraciones

**Hay un solo esquema, así que una migración toca los datos reales.** El procedimiento está en la sección 16.4 del documento técnico y no es negociable:

```bash
./scripts/respaldo.sh                       # 1 · respaldo, y se verifica solo
DB_SCHEMA=public APP_ENV=production alembic revision --autogenerate -m "..."
                                            # 2 · revisar el archivo A MANO
DB_SCHEMA=public APP_ENV=production alembic upgrade head
                                            # 3 · aplicar
curl -s https://13-140-36-93.sslip.io/api/health   # 4 · verificar
```

El paso 1 **no se puede saltear**: desde F18-T04, Alembic se niega a migrar la
base real si no hay una constancia verificada de las últimas 3 horas. El
respaldo nocturno no alcanza —lo que se exige es el del momento—, y la salida
de emergencia es `MIGRAR_SIN_RESPALDO=si-entiendo-el-riesgo`, que avisa fuerte.

`DB_SCHEMA` y `APP_ENV` van explícitos a propósito: `migrations/env.py` los exige y no asume nada. Migrar es la operación destructiva del proyecto.

### Recuperar una contraseña

No hay correo saliente, a propósito. El enlace se genera a mano, dentro del
servidor, y se entrega por donde se pueda:

```bash
docker compose exec api python -m app.cli recuperar gustavo@ejemplo.com
```

Vale **30 minutos y una sola vez**, se guarda hasheado, se quema antes de tocar
nada y al usarse corta todas las sesiones abiertas de esa cuenta. Pedir uno
nuevo invalida el anterior.

**Esto es más chico que un «olvidé mi contraseña» por correo, no más grande.**
Un formulario de recuperación es una puerta que cualquiera puede tocar desde
internet y que depende enteramente de que el buzón de la persona esté a salvo —
y el buzón es justo lo que más se roba. Acá esa puerta no existe: para que se
emita un enlace hay que entrar al servidor por SSH.

El costo, dicho claro: **quien puede correr ese comando puede tomar cualquier
cuenta.** A esta escala no agrega riesgo, porque con acceso de root a la máquina
la base entera ya está a la vista.

### Los respaldos

Son tres piezas y cada una vive en un lado distinto. Que estén separadas es
el punto: un respaldo que comparte disco con la base no protege de que el
disco falle.

| Dónde | Qué | Cuándo |
|---|---|---|
| Servidor | `scripts/respaldo.sh` escribe el dump **y lo vuelve a abrir** para contar sus tablas | 3:15, por `cron` |
| Servidor | `/opt/epic-wallet/respaldos/` · 7 diarios, 4 semanales, 6 mensuales | — |
| PC de Gustavo | `scripts/traer_respaldos.ps1` se trae lo que falte a `D:\Respaldos\Epic_Wallet` | 8:00, por el Programador de tareas |

`scripts/restaurar.sh` cierra el circuito. Por defecto restaura en
`epic_wallet_restaurado` —una base aparte que crea y pisa—, nunca encima de la
real: para eso hace falta `--sobre-la-real` y escribir el nombre de la base a
mano. Al terminar **cuenta las filas de cada tabla contra el origen** y falla si
una sola difiere, porque «`pg_restore` no dio error» no es lo mismo que «los
datos están».

**La PC tira del servidor; el servidor no empuja.** Si empujara, necesitaría
una credencial de la PC guardada en su disco, y quien entrara al servidor
entraría también a la PC. Tirando, la credencial nunca sale de la PC. De
yapa: si la PC estuvo una semana apagada, al prenderse se trae la semana.

En la PC **no hay retención**: se guarda todo lo que bajó, incluso lo que el
servidor ya descartó.

```powershell
# instalar la tarea programada, una sola vez
powershell -ExecutionPolicy Bypass -File scripts\instalar_tarea_respaldos.ps1

# traer ahora, sin esperar a mañana
powershell -ExecutionPolicy Bypass -File scripts\traer_respaldos.ps1

Get-ScheduledTaskInfo "Epic Wallet - traer respaldos"   # cuándo corrió y cómo salió
Get-Content D:\Respaldos\Epic_Wallet\traer_respaldos.log -Tail 20
```

### Variables de entorno

Se copian de `.env.example` y se completan. `python scripts/check_db.py` verifica que esté todo, sin imprimir ningún secreto. La lista completa está en la sección 11 del documento técnico.

Dos reglas que no se discuten:

- **La clave privada de firma nunca sale del servidor** ni entra al repositorio. Es el único secreto que, filtrado, permitiría fabricar sesiones de cualquier usuario.
- **El frontend no recibe ningún secreto.** `web/public/config.js` lleva sólo la URL de la API, y `tests/unit/test_secretos_fuera_del_frontend.py` revisa todos los archivos versionados.

---

## Dónde corre

| Entorno | Dónde | Base de datos |
|---|---|---|
| Producción | [13-140-36-93.sslip.io](https://13-140-36-93.sslip.io) | Postgres del servidor |
| Local | `localhost:8000` + `localhost:3000` | Postgres en Docker, en tu máquina |

**Hay un solo entorno publicado.** No hay previews por rama: con un servidor propio, montar un entorno efímero por rama es infraestructura que a esta escala no se paga sola.

**Una prueba en el servidor escribe sobre los datos reales.** Las tareas que prueban escritura usan una segunda cuenta de prueba; RLS garantiza que no se cruzan.

### Publicar un cambio

```bash
ssh jarvis-vps
cd /opt/epic-wallet
git pull && docker compose up -d --build
curl -s https://13-140-36-93.sslip.io/api/health
```

---

## Cómo se trabaja

Una tarea del roadmap a la vez, sin adelantar fases. Dentro de cada tarea: **cálculo → backend → frontend**. Al terminar se avisa qué probar y se espera la aprobación; la tarea pasa a `[x]` sólo entonces.

### Estado de las tareas en el roadmap

| Marca | Significado |
|---|---|
| `- [ ]` | Pendiente |
| `- [~]` | Implementada, esperando prueba |
| `- [x]` | Aprobada e integrada |
| `- [!]` | Rechazada, a corregir |

### Convención de commits

```text
feat(F15-T03): compose con postgres y la api
fix(F06-T02): la línea de ahorro no se dibujaba con ahorro negativo
docs(F14-T04): el documento técnico pasa al servidor propio
```

---

## Pruebas

```bash
pytest                      # unitarios y de API
pytest tests/unit -v        # sólo la lógica de cálculo, sin base
npm test                    # frontend, con node --test
ruff check . && ruff format --check .
mypy api
./scripts/sin_proveedores.sh --docs   # la documentación, limpia
./scripts/sin_proveedores.sh          # todo el repo · reja final de F17, hoy falla a propósito
```

### La base de las pruebas

`tests/api/` necesita un Postgres local y **una base dedicada**. Le borra filas sin preguntar, así que el nombre tiene que contener «test» o «prueba»; si no, las pruebas se niegan a arrancar.

```bash
docker compose -f docker-compose.yml -f docker-compose.desarrollo.yml up -d db
docker compose exec db createdb -U epic epic_wallet_test
# y en .env:  TEST_DATABASE_URL=postgresql+psycopg://epic:...@localhost:5432/epic_wallet_test
pytest
```

El esquema lo crea sola la primera corrida. `TEST_DATABASE_URL` **no** cae por defecto en `DATABASE_URL`: si cayera, un `pytest` distraído le borraría filas a la base de trabajo. Sin esa variable, `tests/api/` se saltea y lo dice.

El override de desarrollo publica la base en `127.0.0.1` y en ninguna otra interfaz. **El servidor no usa ese archivo:** allá la base sigue sin puertos.

Se testea **lo que da un número o protege un dato**: las funciones de `services/calc.py`, el recálculo del mes, los casos borde y que una cuenta no vea los datos de otra.

**No se testea** la estructura del HTML, los tokens de CSS, el contraste ni la configuración del despliegue: eso se verifica mirando la pantalla en el celular. **No hay exigencia de cobertura.** El criterio es: *si el test falla, ¿me enteré de algo que la pantalla no me hubiera mostrado?*

**Ninguna prueba toca un servidor de verdad.** Corren contra la base local, firman sus propios tokens y no abren una sola conexión a internet.

---

## Comandos útiles

```bash
# Migraciones · RESPALDO PRIMERO: hay un solo esquema y son los datos reales
DB_SCHEMA=public APP_ENV=production alembic revision --autogenerate -m "F15 algo"
DB_SCHEMA=public APP_ENV=production alembic upgrade head
DB_SCHEMA=public APP_ENV=production alembic downgrade -1
DB_SCHEMA=public APP_ENV=production alembic current   # en qué revisión está

# Datos
python scripts/load_history.py --dry-run              # carga de histórico, sin escribir

# Respaldo y restauración
./scripts/respaldo.sh                                 # dump verificado
./scripts/restaurar.sh <archivo>                      # restaurar en una base aparte
./scripts/restaurar.sh <archivo> --sobre-la-real      # restaurar ENCIMA de la base real
# y en la PC de Gustavo, no en el servidor:
powershell -File scripts\traer_respaldos.ps1          # traer la copia de afuera

# Cuentas
docker compose exec api python -m app.cli recuperar <email>   # link de contraseña nueva
```

---

## Seguridad

Contiene información financiera personal. HTTPS siempre, contraseñas guardadas sólo como hash bcrypt, aislamiento por usuario con `user_id` en toda consulta **y Row Level Security como segunda barrera**, validación en el servidor sin excepciones, y consultas siempre parametrizadas.

El aislamiento entre cuentas es la única exigencia de seguridad que no se negocia: toda tabla de datos de usuario lleva RLS activo y forzado, incluidas las que se agreguen.

El detalle completo está en la sección 17 del documento técnico.

---

## Licencia

Proyecto personal privado. Todos los derechos reservados.

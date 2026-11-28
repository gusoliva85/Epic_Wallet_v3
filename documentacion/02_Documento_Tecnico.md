# Documento técnico — Epic Wallet 2.0

**Versión:** 1.0
**Fecha:** 03/10/2026
**Estado:** Especificación técnica aprobada para desarrollo
**Documentos relacionados:** `01_Documento_General.md` (qué se construye) · `03_Roadmap.md` (en qué orden) · `mockups/01_Mockup_V1_Grafito_Clasico.html` (diseño aprobado)

---

## 1. Propósito de este documento

`01_Documento_General.md` define **qué** hace la aplicación. Este documento define **cómo** se construye: stack, arquitectura, esquema de datos, contratos de API, sistema de estilo y despliegue.

Regla de precedencia: si este documento contradice al general en una decisión funcional, gana el general. Si el general propone una tecnología y acá se decide otra, gana este documento y la desviación queda registrada en la sección 4.

---

## 2. Principios técnicos

1. **Mobile-first real.** Se desarrolla y prueba primero a 390 px de ancho. El escritorio se gana con `min-width`, nunca se reduce desde escritorio.
2. **Producción desde el día uno.** Cada tarea terminada tiene que ser visible en una URL pública para probarla en el celular. No existe "terminado en local".
3. **Lógica primero, después backend, después frontend.** Cada funcionalidad se implementa en ese orden y se valida en cada paso.
4. **Sin framework de UI.** Nada de React, Vue ni Angular. HTML, CSS (Tailwind) y JavaScript nativo con módulos ES.
5. **Una sola fuente de verdad para los cálculos.** Todo cálculo financiero vive en el backend. El frontend muestra; no recalcula.
6. **Nada se implementa sin probar.** Cada tarea del roadmap tiene criterios de aceptación verificables.
7. **Carga rápida.** Presupuesto: menos de 150 KB de JavaScript y menos de 50 KB de CSS, ambos comprimidos. Primera pintura útil en menos de 1,5 s en 4G.
8. **Los datos son sensibles.** Información financiera personal: HTTPS siempre, validación en servidor, secretos sólo en backend.

---

## 3. Stack definitivo

### Backend

| Componente | Elección | Por qué |
|---|---|---|
| Lenguaje | **Python 3.12** | Pedido del proyecto. |
| Framework web | **FastAPI** | Async, validación con Pydantic incluida, OpenAPI automática, ASGI nativo. Más liviano que Flask para una API pura. |
| Validación | **Pydantic v2** | Esquemas de entrada y salida, errores claros, serialización rápida. |
| Acceso a datos | **SQLAlchemy 2.0** (Core + ORM) | Permite el mismo código contra SQLite y Postgres. Consultas parametrizadas por defecto. |
| Driver Postgres | **psycopg 3** (binary) | Driver recomendado para SQLAlchemy 2.0. |
| Migraciones | **Alembic** | Versionado del esquema, reversible. |
| Autenticación | **Propia** · bcrypt + JWT ES256 con par de claves del proyecto | Sin proveedor externo. Ver sección 8. |
| HTTP cliente | **httpx** | Para el proveedor de cotizaciones (async). |
| Fechas | **zoneinfo** (`America/Argentina/Buenos_Aires`) | Sin dependencias externas. |
| Testing | **pytest** + **pytest-asyncio** + **httpx.AsyncClient** | Tests de lógica y de endpoints. |
| Calidad | **ruff** (lint + format) + **mypy** (modo básico) | Un solo binario para lint y formato. |

### Frontend

| Componente | Elección | Por qué |
|---|---|---|
| Marcado | **HTML5**, una sola página con vistas | Igual que el mockup aprobado. Navegación por hash, sin recargas. |
| Estilos | **Tailwind CSS v4** + capa de tokens propia | Pedido del proyecto. Los tokens del mockup se registran en `@theme`. |
| Scripting | **JavaScript ES2022**, módulos nativos | Sin bundler obligatorio; el navegador importa los módulos. |
| Gráficos | **SVG propio** (código del mockup) | Ver sección 4.3. |
| Fuentes | **Outfit** + **Inter** (Google Fonts, `display=swap`, precarga) | Las del mockup aprobado. |
| PWA | **Web App Manifest** + **Service Worker** propio | Instalable en Android, cache offline. |
| Build | **Tailwind CLI** (único paso de build) | Genera un CSS; nada más que compilar. |
| Testing | **pytest** | Cálculos y endpoints. La interfaz se verifica a mano en el celular (§19). |

### Infraestructura

| Componente | Elección |
|---|---|
| Servidor | **VPS propio** (Contabo, `13.140.36.93`), Debian/Ubuntu con Docker |
| Proxy y TLS | **Caddy**, dueño del 80 y el 443, certificado de Let's Encrypt renovado solo |
| Dirección | `https://13-140-36-93.sslip.io` — DNS público que resuelve a la IP, sin registro ni vencimiento |
| Hosting del frontend | Estáticos servidos por Caddy desde `web/` |
| Hosting de la API | **FastAPI sobre uvicorn**, en contenedor, sin puerto expuesto al exterior |
| Base de datos | **Postgres 17** en contenedor, volumen propio, un solo esquema (`public`) |
| Autenticación | **Propia**, en FastAPI. JWT ES256 con par de claves del proyecto |
| Base de datos local de desarrollo | Postgres en contenedor. **SQLite** sólo para los tests de cálculo |
| Repositorio | **GitHub**. El servidor se actualiza con `git pull` y `docker compose up -d --build` |
| Backups | **`pg_dump` nuestro**, diario, verificado, copiado fuera del servidor y con restauración probada |
| Convivencia | Comparte el servidor con Jarvis, detrás del mismo Caddy. Bases, redes y volúmenes separados |

---

## 4. Desviaciones respecto del documento general

Tres decisiones se apartan de lo propuesto en `01_Documento_General.md`. Quedan registradas con su motivo.

### 4.1 SQLite no es la base de producción

El documento general dice "se utilizará SQLite en la primera versión" (sección 31). La base de producción es **Postgres**, por una razón que no es de comodidad: **el aislamiento entre cuentas se apoya en Row Level Security** (§6.5), y SQLite no tiene políticas de seguridad por fila ni roles. Cambiar de motor significaría mover esa barrera del motor a la aplicación, que es exactamente donde no la queremos. A eso se suman `numeric(14,2)` para los importes y las zonas horarias, que SQLite tampoco resuelve.

Qué se conserva:

- El **modelo de datos** de las secciones 31 a 43 del documento general se respeta tabla por tabla y campo por campo.
- **SQLAlchemy** abstrae el motor, así que el mismo código corre contra SQLite y Postgres.
- SQLite queda disponible para correr los tests rápido (`DATABASE_URL=sqlite+pysqlite:///./test.db`).

Riesgo conocido y cómo se mitiga: SQLite y Postgres no se comportan igual en tipos, `ON CONFLICT`, ordenamiento de texto y zonas horarias. Para evitar bugs que sólo aparecen en producción, **el desarrollo normal usa Postgres**, y SQLite se usa sólo para los tests unitarios. Los tests de integración corren contra Postgres.

### 4.1.1 Un solo esquema

El proyecto trabaja contra **un único esquema: `public`**.

Una versión anterior de este documento definía dos esquemas (`public` para producción y `dev` para desarrollo) y una variable `DB_SCHEMA` para elegir. Esa separación se quitó en la revisión del 07/10/2026: para una aplicación de pocos usuarios conocidos costaba más de lo que protegía —dos juegos de migraciones, un comparador de esquemas, una prueba de paridad y varias guardias de arranque—, todo para cuidar un entorno de pruebas que en la práctica era el único que se usaba.

`DB_SCHEMA` sigue existiendo como variable, con **`public` por defecto**, para no atar el código a un nombre de esquema. Nadie necesita definirla.

**Qué se pierde y cómo se cubre.** Al no haber un esquema de pruebas, una migración equivocada toca los datos reales. El reemplazo es un procedimiento, no una barrera técnica:

1. **Respaldo antes de cada migración**, con `scripts/respaldo.sh`, que además verifica el archivo que acaba de escribir (§18). Y `GET /api/export` permite bajarse todo desde la aplicación.
2. **Toda migración tiene su `downgrade` escrito y probado** antes de aplicarse.
3. **`migrations/env.py` exige que el esquema esté declarado explícitamente** al migrar. Migrar es la operación destructiva: que pida ser explícita está bien.

Con la base en un servidor propio, el punto 1 dejó de depender de nadie: el respaldo es un archivo que podemos abrir, verificar y restaurar, y el procedimiento de restauración está probado de verdad (§18).

### 4.2 Sin plantillas de servidor

El documento general proponía "componentes HTML reutilizables" servidos por el backend. Acá el frontend se sirve estático desde el proxy y la API va aparte. Los componentes se componen **en el cliente** con funciones que devuelven HTML (exactamente como el mockup). Beneficio: la pantalla se pinta sin esperar a Python.

### 4.3 Gráficos con SVG propio en lugar de Chart.js

El documento general propone Chart.js (sección 44). Se decide **mantener el SVG escrito a mano del mockup aprobado** porque:

- Ya está implementado y validado visualmente, incluido el gráfico combinado de barras con la línea de ahorro acumulado y doble eje, que en Chart.js requiere configuración de ejes múltiples y un plugin de tipos mixtos.
- Ahorra unos 70 KB comprimidos, relevante para el presupuesto de la sección 2.
- Hereda el tema claro/oscuro automáticamente porque usa variables CSS como color (`fill="var(--inc)"`), algo que Chart.js no hace sin redibujar.

La especificación completa de cada gráfico está en la sección 14.

---

## 5. Arquitectura

```text
┌───────────────────────────────────────────────────────────────┐
│  NAVEGADOR (Android / escritorio)                             │
│                                                               │
│  index.html  ·  app.css (Tailwind compilado)                  │
│  js/  main.js · router.js · api.js · state.js                 │
│        views/ (inicio, movimientos, historial, inversiones,   │
│                patrimonio, config)                             │
│        components/ (kpi, rows, charts, sheet, form, toast)    │
│  service-worker.js  ·  manifest.json                          │
└───────────────┬───────────────────────────────────────────────┘
                │ fetch + Authorization: Bearer <JWT>
                ▼
┌───────────────────────────────────────────────────────────────┐
│  CADDY — misma URL, mismo dominio, TLS automático             │
│                                                               │
│  /            → estáticos de web/, servidos por el proxy      │
│  /api/*       → FastAPI sobre uvicorn, en contenedor          │
│                                                               │
│  ┌─ routers/   validan entrada y devuelven respuestas         │
│  ├─ services/  reglas de negocio y cálculos                   │
│  ├─ repos/     consultas SQLAlchemy                           │
│  └─ core/      config, seguridad, errores, dependencias       │
└───────────────┬───────────────────────────────────────────────┘
                │ psycopg 3 (pool) + verificación de JWT
                ▼
┌───────────────────────────────────────────────────────────────┐
│  POSTGRES 17 — contenedor propio, volumen propio              │
│    tablas + RLS por usuario                                   │
│    auth.users (identidades) + auth.uid() (nuestra)            │
│    respaldo diario verificado, con copia fuera del servidor   │
└───────────────────────────────────────────────────────────────┘
                ▲
                │ httpx (programado o manual)
┌───────────────┴───────────────────────────────────────────────┐
│  PROVEEDOR DE COTIZACIONES (desacoplado, con fallback manual) │
└───────────────────────────────────────────────────────────────┘
```

### 5.1 Las cuatro capas del backend

Cada capa sólo conoce la de abajo. Esto es lo que permite probar la lógica sin base de datos y sin HTTP.

| Capa | Carpeta | Responsabilidad | Qué **no** hace |
|---|---|---|---|
| **Router** | `api/app/routers/` | Rutas, validación con Pydantic, códigos HTTP | No calcula ni consulta la base |
| **Service** | `api/app/services/` | Reglas de negocio, cálculos, validaciones cruzadas | No sabe de HTTP ni escribe SQL |
| **Repo** | `api/app/repos/` | Consultas SQLAlchemy, transacciones | No decide reglas de negocio |
| **Core** | `api/app/core/` | Configuración, JWT, errores, sesión de base | No contiene lógica financiera |

Regla práctica: **todo cálculo financiero es una función pura en `services/calc.py`** que recibe números y devuelve números. Así se testea sin base de datos, y es lo que se implementa primero en cada tarea del roadmap.

---

## 6. Modelo de datos

Implementa las secciones 31 a 43 del documento general. DDL para Postgres. Los `CHECK` y `UNIQUE` son parte del contrato, no opcionales.

### 6.1 Convenciones

- Claves primarias `bigint generated always as identity`, salvo `profiles.id` que es `uuid` y referencia a `auth.users`.
- Importes en **`numeric(14,2)`**. Nunca `float`: los centavos no se redondean solos.
- Timestamps `timestamptz`, con `default now()`. La aplicación muestra en `America/Argentina/Buenos_Aires`.
- Todas las tablas de datos del usuario llevan `user_id uuid not null` para que RLS funcione.
- Nombres de tablas y columnas en inglés y `snake_case`; los textos visibles van en español en el frontend.
- Todas las tablas viven en el esquema que indica `DB_SCHEMA`, siempre `public` (§4.1.1). El DDL de abajo se aplica dentro de ese esquema; `auth.users` vive en el esquema `auth`, junto a la función `auth.uid()` (§8, §16.2).

### 6.2 DDL

```sql
-- ============ PERFIL (extiende auth.users) ============
create table profiles (
  id            uuid primary key references auth.users(id) on delete cascade,
  username      text not null unique,
  display_name  text,
  opening_balance numeric(14,2) not null default 0,   -- saldo inicial de ahorros
  timezone      text not null default 'America/Argentina/Buenos_Aires',
  active        boolean not null default true,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  last_login_at timestamptz
);

-- ============ MESES ============
create table months (
  id              bigint generated always as identity primary key,
  user_id         uuid not null references profiles(id) on delete cascade,
  year            int  not null check (year between 2000 and 2100),
  month           int  not null check (month between 1 and 12),
  status          text not null default 'open'
                  check (status in ('open','historical')),
  income_total    numeric(14,2) not null default 0,
  expense_total   numeric(14,2) not null default 0,
  saving_total    numeric(14,2) not null default 0,
  opening_balance numeric(14,2) not null default 0,
  closing_balance numeric(14,2) not null default 0,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  constraint months_unique_per_user unique (user_id, year, month)
);
create index months_user_period_idx on months (user_id, year desc, month desc);

-- ============ CATEGORÍAS ============
create table categories (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references profiles(id) on delete cascade,
  name        text not null,
  type        text not null check (type in ('income','expense')),
  active      boolean not null default true,
  sort_order  int not null default 0,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint categories_unique_name_per_type unique (user_id, type, name)
);
create index categories_user_type_idx on categories (user_id, type, active, sort_order);

-- ============ MOVIMIENTOS (sólo meses transaccionales) ============
create table transactions (
  id               bigint generated always as identity primary key,
  user_id          uuid not null references profiles(id) on delete cascade,
  month_id         bigint not null references months(id) on delete cascade,
  category_id      bigint not null references categories(id) on delete restrict,
  transaction_date date not null,
  transaction_type text not null check (transaction_type in ('income','expense')),
  amount           numeric(14,2) not null check (amount > 0),
  description      text,
  source           text not null default 'manual'
                   check (source in ('manual','mercado_pago','system','import')),
  external_id      text,                      -- anti-duplicados de importaciones
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint transactions_external_unique unique (user_id, source, external_id)
);
create index transactions_month_idx    on transactions (user_id, month_id, transaction_date desc, id desc);
create index transactions_category_idx on transactions (user_id, category_id, transaction_date desc);
create index transactions_search_idx   on transactions (user_id, description);
```

El importe es siempre positivo y el signo lo decide `transaction_type` (sección 8.4 del documento general). El `CHECK (amount > 0)` lo garantiza a nivel de base, no sólo de formulario.

```sql
-- ============ TOTALES POR CATEGORÍA ============
-- Mes en curso: is_manual_summary = false, el total se recalcula desde transactions.
-- Mes histórico: is_manual_summary = true,  el total lo cargó el usuario a mano.
create table monthly_category_totals (
  id                bigint generated always as identity primary key,
  user_id           uuid not null references profiles(id) on delete cascade,
  month_id          bigint not null references months(id) on delete cascade,
  category_id       bigint not null references categories(id) on delete restrict,
  total_amount      numeric(14,2) not null default 0,
  is_manual_summary boolean not null default false,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  constraint mct_unique unique (month_id, category_id)
);
create index mct_month_idx on monthly_category_totals (user_id, month_id);

-- ============ HISTORIAL LABORAL ============
create table employment_history (
  id             bigint generated always as identity primary key,
  user_id        uuid not null references profiles(id) on delete cascade,
  company        text not null,
  position       text not null,
  salary         numeric(14,2) not null check (salary >= 0),
  effective_date date not null,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);
create index employment_user_date_idx on employment_history (user_id, effective_date desc);

-- ============ INVERSIONES (cartera actual, sin bitácora) ============
-- Revisado 2026-10-20: sin modo de valuación. initial_value (precio de
-- compra) y current_value (precio actual) son siempre el importe total
-- de la posición, cargado a mano — nunca nominales por un precio
-- unitario. nominal_quantity queda puramente informativo. Se sacaron
-- current_unit_price, valuation_mode, price_source y price_updated_at
-- (migración 7a3f9c2e1d84): los últimos dos estaban preparados para la
-- cotización automática de después del MVP y nadie los llegó a usar.
create table investments (
  id                bigint generated always as identity primary key,
  user_id           uuid not null references profiles(id) on delete cascade,
  symbol            text not null,
  name              text not null,
  investment_type   text not null check (investment_type in
                     ('obligacion_negociable','bono','cedear','accion','fci','otro')),
  nominal_quantity  numeric(18,4) not null default 0 check (nominal_quantity >= 0),
  initial_value     numeric(14,2) not null default 0 check (initial_value >= 0),
  current_value     numeric(14,2) not null default 0,
  active            boolean not null default true,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create index investments_user_idx on investments (user_id, active, symbol);

-- ============ CACHE DE COTIZACIONES (no son operaciones) ============
create table investment_price_cache (
  id           bigint generated always as identity primary key,
  symbol       text not null,
  unit_price   numeric(18,6) not null,
  source       text not null,
  as_of        timestamptz not null,
  fetched_at   timestamptz not null default now(),
  raw_payload  jsonb,
  constraint price_cache_unique unique (symbol, source, as_of)
);
create index price_cache_symbol_idx on investment_price_cache (symbol, as_of desc);

-- ============ ALERTAS ============
create table alerts (
  id           bigint generated always as identity primary key,
  user_id      uuid not null references profiles(id) on delete cascade,
  alert_type   text not null,
  title        text not null,
  message      text not null,
  severity     text not null default 'info'
               check (severity in ('info','warning','pending','critical')),
  context      jsonb,                         -- mes, categoría, importes que la originaron
  created_at   timestamptz not null default now(),
  read_at      timestamptz,
  dismissed_at timestamptz
);
create index alerts_user_open_idx on alerts (user_id, dismissed_at, created_at desc);

-- ============ PREFERENCIAS ============
create table app_settings (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references profiles(id) on delete cascade,
  key        text not null,
  value      jsonb not null,
  updated_at timestamptz not null default now(),
  constraint app_settings_unique unique (user_id, key)
);

-- ============ VENCIMIENTOS (F13-T03) ============
-- Una fila por categoría CONFIGURADA, no por categoría: una categoría
-- sin fila es una categoría sin vencimiento, que es el estado inicial
-- de todas. `enabled` existe además de «tener fila o no» porque apagar
-- un vencimiento no puede perder su configuración: se apaga en marzo,
-- se prende en abril y el día y el aviso siguen ahí.
--
-- `due_day` admite el 31 aunque no exista en todos los meses: significa
-- «el último día», y `services/vencimientos.py` lo recorta mes a mes.
create table category_dues (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references profiles(id) on delete cascade,
  category_id bigint not null references categories(id) on delete cascade,
  enabled     boolean not null default true,
  due_day     integer not null,
  notice_days integer not null default 3,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint category_dues_unique unique (user_id, category_id),
  constraint category_dues_day    check (due_day between 1 and 31),
  constraint category_dues_notice check (notice_days between 0 and 30)
);

-- ============ PASIVOS (preparado, no se usa en el MVP) ============
create table liabilities (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references profiles(id) on delete cascade,
  name        text not null,
  amount      numeric(14,2) not null default 0,
  active      boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
```

La tabla `liabilities` se crea vacía y no se muestra en la interfaz. El cálculo de patrimonio ya la resta (siempre 0), así que incorporar pasivos más adelante no requiere migrar nada ni rehacer el cálculo.

### 6.3 Reglas garantizadas por la base

| Regla del documento general | Cómo se garantiza |
|---|---|
| R1 — Un mes por año/mes | `unique (user_id, year, month)` |
| Importe siempre positivo (8.4) | `check (amount > 0)` |
| Categoría de ingreso no sirve para egresos (34) | Validación en service: `category.type == transaction_type`, más el test correspondiente |
| No duplicar nombre de categoría en el mismo tipo (51) | `unique (user_id, type, name)` |
| No borrar categoría con histórico (7) | `on delete restrict` en `transactions` y `monthly_category_totals` |
| Anti-duplicados de importación (62) | `unique (user_id, source, external_id)` |
| R12 — Contraseñas nunca en texto plano | Sólo se guarda el hash bcrypt, en `auth.users.encrypted_password` |

### 6.4 Trigger de `updated_at`

```sql
create or replace function set_updated_at() returns trigger
language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

-- aplicar a cada tabla con updated_at
create trigger trg_touch before update on transactions
  for each row execute function set_updated_at();
-- (ídem: profiles, months, categories, monthly_category_totals,
--        employment_history, investments, liabilities)
```

### 6.5 Row Level Security

RLS se activa en **todas** las tablas de datos de usuario. Es la red de seguridad que hace imposible leer datos de otro usuario incluso si un endpoint tuviera un bug de filtrado.

```sql
alter table profiles                 enable row level security;
alter table months                   enable row level security;
alter table categories                enable row level security;
alter table transactions              enable row level security;
alter table monthly_category_totals   enable row level security;
alter table employment_history        enable row level security;
alter table investments               enable row level security;
alter table alerts                    enable row level security;
alter table app_settings              enable row level security;
alter table liabilities               enable row level security;
alter table category_dues            enable row level security;

-- patrón aplicado a cada tabla (ejemplo con transactions)
create policy own_rows_select on transactions for select using (user_id = auth.uid());
create policy own_rows_insert on transactions for insert with check (user_id = auth.uid());
create policy own_rows_update on transactions for update using (user_id = auth.uid());
create policy own_rows_delete on transactions for delete using (user_id = auth.uid());

-- profiles usa id en lugar de user_id
create policy own_profile on profiles for all using (id = auth.uid()) with check (id = auth.uid());
```

`investment_price_cache` no lleva `user_id` (las cotizaciones son públicas): queda con RLS activo y sin política de escritura, accesible sólo por el backend con la clave de servicio.

### 6.6 Las dos naturalezas de mes

Es **la decisión estructural más importante del proyecto** (sección 71 del documento general). Se resuelve en un único lugar del backend.

| | Mes en curso (`status = 'open'`) | Mes histórico (`status = 'historical'`) |
|---|---|---|
| Origen de los totales | `SUM(transactions.amount)` por tipo | Campos `income_total` / `expense_total` del mes |
| Totales por categoría | Recalculados desde `transactions` | `monthly_category_totals` con `is_manual_summary = true` |
| Movimientos individuales | Sí | **No existen y no se inventan** (R4) |
| Qué devuelve la API | `transactions: [...]` | `transactions: null` |
| Editable | Sí | Sí (sección 6.3 del general: se puede corregir un error) |

El contrato de API es explícito: **`transactions: null` significa "este mes no tiene movimientos individuales"**, distinto de `transactions: []` que sería "los tiene pero están vacíos". El frontend usa esa diferencia para mostrar el mensaje de mes consolidado en lugar de una lista vacía.

---

## 7. Cálculos

Todos viven en `api/app/services/calc.py` como **funciones puras** sin acceso a base de datos. Esto permite testearlos antes de que exista cualquier endpoint, que es el primer paso de cada tarea del roadmap.

```python
# api/app/services/calc.py
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
def money(v: Decimal) -> Decimal:
    """Redondeo contable a dos decimales."""
    return Decimal(v).quantize(CENT, rounding=ROUND_HALF_UP)

def monthly_saving(income: Decimal, expense: Decimal) -> Decimal:
    return money(income - expense)

def saving_rate(income: Decimal, saving: Decimal) -> Decimal | None:
    """None cuando los ingresos son cero: se muestra N/A, no 0%."""
    if income == 0:
        return None
    return money(saving / income * 100)

def accumulated_balance(opening: Decimal, savings: list[Decimal]) -> Decimal:
    return money(opening + sum(savings, Decimal(0)))

# Revisado 2026-10-20: no hay `investment_value` ni modo de valuación.
# El valor de una posición es el importe total que se carga a mano
# (precio de compra, precio actual) — no hace falta ninguna cuenta
# para armarlo.

def investment_return(current: Decimal, initial: Decimal) -> Decimal:
    return money(current - initial)

def investment_return_pct(current: Decimal, initial: Decimal) -> Decimal | None:
    """None cuando el valor inicial es cero: el porcentaje no se calcula."""
    if initial == 0:
        return None
    return money((current / initial - 1) * 100)

def net_worth(savings: Decimal, investments: Decimal,
              other_assets: Decimal = Decimal(0),
              liabilities: Decimal = Decimal(0)) -> Decimal:
    return money(savings + investments + other_assets - liabilities)

def daily_saving_series(income_by_day: list[Decimal],
                        expense_by_day: list[Decimal]) -> list[Decimal]:
    """Ahorro del mes acumulado día por día: sube con los ingresos y
    baja con cada gasto. Alimenta la línea del gráfico diario."""
    out, acc = [], Decimal(0)
    for inc, exp in zip(income_by_day, expense_by_day):
        acc += inc - exp
        out.append(money(acc))
    return out
```

### 7.1 Casos borde de obligado cumplimiento

| Caso | Resultado esperado |
|---|---|
| Ingresos = 0 al pedir la tasa de ahorro | `null` → la interfaz muestra `N/A`, nunca `0%` ni división por cero |
| Valor inicial = 0 al pedir rendimiento % | `null` → se muestra `—` |
| Mes sin ningún movimiento | Totales en 0, ahorro 0, y se genera la alerta "mes sin cargar" |
| Ahorro negativo (gasté más de lo que ingresé) | Se muestra con signo menos; es un resultado válido, no un error |
| Mes histórico al pedir el gráfico diario | La API no devuelve serie diaria; el frontend muestra el mensaje de mes consolidado |
| Suma de categorías ≠ total de egresos en carga histórica | Advertencia con el texto exacto del documento general; el usuario puede corregir o guardar igual |
| Desglose por categoría (General §15, F07-T01) | Los `share` de un mismo tipo (todos los ingresos, todos los egresos) suman exactamente 100 — `calc.porcentajes_de_categorias`, método del mayor resto, no `participacion()` categoría por categoría |
| Categoría sin movimientos en el mes | No aparece en el desglose del dashboard (`GET /api/dashboard`); pedida por su propio detalle (`GET /api/categories/{id}/detail`), da total `"0.00"` y `transactions: []` |

### 7.2 Recálculo del mes

Cada alta, edición o baja de movimiento dispara `recalculate_month(month_id)`, **dentro de la misma transacción de base de datos**:

1. Recalcular `income_total`, `expense_total` y `saving_total` desde `transactions`.
2. Regenerar `monthly_category_totals` del mes (sólo filas con `is_manual_summary = false`).
3. Recalcular `closing_balance` del mes y de **todos los meses posteriores** en cadena, porque el saldo acumulado es una suma corrida.
4. Reevaluar las alertas que dependan de ese mes.

Si cualquier paso falla, la transacción se revierte entera: no puede quedar un movimiento guardado con totales viejos.

### 7.3 Compra y venta de inversiones

Regla 7 del documento general: comprar **no es un gasto de consumo**, es una transferencia patrimonial. El patrimonio neto no cambia por el hecho de comprar.

```text
Comprar $500.000:   ahorro líquido −500.000   ·   cartera +500.000   ·   patrimonio igual
Vender  $1.200.000: cartera −1.200.000        ·   ahorro +1.200.000  ·   patrimonio igual
```

**Decisión final de Gustavo (2026-10-17, segunda revisión del día — pisa las dos versiones anteriores de este párrafo).** La cartera es información, no bitácora de gastos: **comprar y vender en la pantalla de Cartera no generan ningún movimiento** en `transactions`, bajo ningún caso. `POST`, `PUT` y `DELETE /api/investments` nunca escriben en `transactions` ni abren un mes.

Motivo: lo que Gustavo deposita en su cuenta de inversión (por ejemplo, $1.000.000 este mes) **no coincide** con lo que termina comprando — queda plata sin invertir, por cobrar, pendiente de liquidar. Una versión anterior de esta tarea (F10-T06) generaba un movimiento automático por el importe exacto de cada compra bajo una categoría "Inversiones"; esa versión asumía que el importe de la cartera y el importe que sale del bolsillo son el mismo número, y en la práctica no lo son.

Diseño final, en dos partes independientes:

1. **El depósito a la cuenta de inversión se carga a mano, como cualquier otro movimiento**, en `POST /api/transactions`, bajo la categoría "Inversiones" (una categoría normal, visible y elegible como cualquier otra — no hace falta que el backend la cree ni la mueva sola). El importe lo decide la persona; no tiene que coincidir con ninguna posición de la cartera.
2. **La cartera (`investments`) es una tabla aparte, sin relación con `transactions`.** `GET/POST/PUT/DELETE /api/investments` sólo leen y escriben posiciones — nominales, valor inicial, valor actual. `investments.current_value` sigue sumando al patrimonio neto (§6.2, `services/patrimony.py`), que es lo que la hace útil más allá de ser una lista: la foto de cuánto hay invertido hoy, aparte de cuánto se depositó en total.

Esto es independiente del rendimiento de una inversión (Regla 9): la ganancia o pérdida de una posición nunca se informó como ingreso ni en la versión anterior ni en ésta.

## 8. Cuentas de usuario, autenticación y sesión

### 8.1 Decisión

**Autenticación propia, en FastAPI.** El backend guarda el hash de la contraseña (bcrypt), firma los tokens y los verifica. No hay proveedor externo en el camino.

No fue la decisión original. La primera versión del proyecto delegaba la identidad en un servicio externo, con el argumento —correcto— de que registro, rotación de tokens y recuperación por mail ya están resueltos ahí y no valía la pena construirlos. Lo que cambió es el contexto: al mudarse a un servidor propio, sostener esa dependencia significaba o bien seguir atado al servicio que se quiso dejar, o bien autohospedar ocho contenedores para no reescribir un archivo.

El costo real de hacerlo propio son seis endpoints y un módulo de frontend, porque **el diseño original ya lo había previsto**: toda la dependencia del proveedor estaba contenida en `core/security.py` y en `web/src/js/auth.js`.

Qué se conserva de aquella decisión, porque era buena:

- **Firma asimétrica (ES256).** La privada firma, la pública verifica. Con un secreto compartido, quien lo tenga puede fabricar sesiones; acá, quien tenga la pública sólo puede comprobarlas.
- **bcrypt** para las contraseñas: es lo que usaba el proveedor anterior, y es lo que permite importar sus hashes sin que nadie tenga que resetear nada.
- **Los mismos claims** (`sub`, `aud: authenticated`, `exp`, `email`), así el resto del backend no se enteró del cambio.

### 8.2 La aplicación es multiusuario

El documento general plantea "1 usuario, con posibilidad de ampliar a pocos usuarios autenticados". Esa posibilidad **se construye desde el MVP**, no se deja para después:

- **Cualquiera puede registrarse** desde la pantalla de registro.
- **Cada cuenta es un mundo aparte**: sus meses, categorías, movimientos, inversiones, historial laboral, alertas y preferencias. Nadie ve los datos de nadie.
- El aislamiento no depende de que los endpoints filtren bien: **Row Level Security** lo garantiza a nivel de base (§6.5). Aunque un endpoint tuviera un bug, Postgres no devolvería filas de otro usuario.

Esto no agrega complejidad al modelo de datos porque **ya estaba previsto**: todas las tablas llevan `user_id` desde el primer día (§6.1). Lo que se agrega es el ciclo de vida de la cuenta.

### 8.3 Ciclo de vida de una cuenta

```text
REGISTRO
  pantalla de registro (email + contraseña + repetir)
     ↓  POST /api/auth/signup
  la API crea la fila en auth.users con el hash bcrypt
     ↓  el trigger de Postgres crea su profile y sus 21 categorías
  devuelve access_token + refresh_token
     ↓
  tablero de su mes actual, vacío y listo para cargar

INICIO DE SESIÓN
  email + contraseña  →  POST /api/auth/login  →  access_token + refresh_token

RENOVACIÓN
  POST /api/auth/refresh con el token de renovación
     ↓  el token usado se quema y se entrega uno nuevo (rotación)
  access_token nuevo

RECUPERACIÓN DE CONTRASEÑA  (sin correo, §8.5)
  Gustavo corre en el servidor:  python -m app.cli recuperar <email>
     ↓  imprime un link de un solo uso, válido 30 minutos
  el link se entrega a mano
     ↓  abre /#/nueva-clave con el token del link
  contraseña nueva + repetir  →  POST /api/auth/reset  →  el token se quema

CAMBIO DE CONTRASEÑA ESTANDO ADENTRO
  configuración → contraseña actual + nueva  →  POST /api/auth/cambiar-clave
```

**No hay confirmación por correo.** Una cuenta nace utilizable. A esta escala —usuarios conocidos, cuentas creadas de a una— confirmar la dirección no protege de nada que importe.

### 8.4 Creación automática del perfil y las categorías

Cuando nace una cuenta hay que darle su fila en `profiles` y sus 21 categorías iniciales (las del documento general §7.1 y §7.2). Se hace con un **trigger en Postgres sobre `auth.users`**, no desde el backend: así una cuenta no puede existir sin su perfil, la cree quien la cree.

Por qué el trigger y no el backend: si el perfil se creara en el primer acceso a `/api/...`, una cuenta podría existir sin perfil en el medio, y habría que manejar ese estado en todos los endpoints. Con el trigger, una fila en `auth.users` sin su perfil es imposible — la cree el endpoint de registro, un script de importación o alguien a mano desde SQL.

```sql
-- Se aplica en el esquema que corresponda (dev o public).
create or replace function crear_perfil_y_categorias()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  nuevas_categorias text[][] := array[
    -- ingresos
    array['Sueldo','income'], array['Aguinaldo','income'], array['Otros','income'],
    -- egresos
    array['Alquiler','expense'], array['Expensas','expense'], array['Cochera','expense'],
    array['ABL','expense'], array['Gas','expense'], array['Luz','expense'],
    array['Internet','expense'], array['Da Vinci','expense'], array['Tarjeta','expense'],
    array['Tuenti','expense'], array['Nafta','expense'], array['Subte','expense'],
    array['Mercadería','expense'], array['Verdulería','expense'],
    array['Carnicería / Pollería','expense'], array['Delivery / Salida','expense'],
    array['Comida Trabajo','expense'], array['Otros','expense']
  ];
  fila text[];
  orden int := 0;
begin
  insert into dev.profiles (id, username, display_name)
  values (
    new.id,
    split_part(new.email, '@', 1),
    coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1))
  );

  foreach fila slice 1 in array nuevas_categorias loop
    orden := orden + 1;
    insert into dev.categories (user_id, name, type, sort_order)
    values (new.id, fila[1], fila[2], orden);
  end loop;

  return new;
end $$;

create trigger al_crear_usuario
  after insert on auth.users
  for each row execute function crear_perfil_y_categorias();
```

Tres detalles que importan: `security definer` para que el trigger pueda escribir saltando RLS; `set search_path = ''` para que no sea vulnerable a una tabla intrusa en otro esquema; y `username` derivado del email, con `display_name` editable después. El trigger es **idempotente en la práctica** porque `auth.users` sólo dispara un `insert` por cuenta.

### 8.5 Sin correo saliente, a propósito

**La aplicación no manda mails y no va a mandarlos.** No es una deuda: es una decisión tomada a la escala del proyecto (Gustavo, 2026-11-22). Montar y mantener un SMTP —dominio verificado, remitente, plantillas, reputación— es resolver un problema que con un puñado de usuarios conocidos no existe.

Lo único que el correo resolvía era la recuperación de contraseña. Se resuelve así:

```bash
docker compose exec api python -m app.cli recuperar gustavo@ejemplo.com
→ https://13-140-36-93.sslip.io/#/nueva-clave?token=a1b2c3…   (vale 30 minutos)
```

El link se entrega a mano y abre **la pantalla de contraseña nueva que ya existe**. El token se guarda hasheado, se quema al usarse y vence solo. El documento general ya había previsto exactamente esto en §48.1: «contactate con quien te dio la cuenta».

Si algún día hay más usuarios y el correo vuelve a tener sentido, lo que falta es el envío: el flujo, la pantalla y el token de un solo uso ya están.

### 8.6 El link de recuperación

Un token opaco de 32 bytes al azar, guardado **hasheado** en la base junto a su vencimiento y al usuario. No es un JWT: no tiene que ser verificable sin la base, y que sea opaco significa que no revela nada si se ve de reojo.

| Regla | Valor |
|---|---|
| Vigencia | 30 minutos |
| Usos | 1 — al canjearlo se borra la fila |
| Alcance | sólo cambiar la contraseña de ese usuario |
| Al canjear | se invalidan todos los tokens de renovación de esa cuenta |

Lo último importa: si alguien pidió una contraseña nueva, las sesiones abiertas de antes tienen que caerse.

### 8.7 Flujo técnico de la sesión

```text
1. El usuario carga index.html (estático, servido por el proxy).
2. Ingresa email y contraseña.
3. El frontend llama a POST /api/auth/login.
4. La API verifica el hash bcrypt y devuelve access_token (JWT, 1 h) y refresh_token (30 días).
5. El frontend guarda la sesión y la renueva sola antes de que expire.
6. Cada llamada a /api/* envía: Authorization: Bearer <access_token>
7. El backend verifica la firma del JWT con la clave pública y extrae el user_id (claim "sub").
8. El backend abre la transacción a nombre de ese usuario, así RLS filtra por auth.uid() (§6.5).
```

El frontend suma tres módulos a los de la sección 10: `auth.js` (sesión), y las vistas `registro`, `recuperar` y `nueva-clave`.

**Tres cosas que `auth.js` tiene que sostener solo**, y que antes venían dadas por la librería del proveedor:

1. **Renovar antes de que venza**, con un margen de un minuto: una petición que sale con un token que vence en dos segundos puede llegar vencida. El temporizador no corre con la pestaña dormida, así que `token()` además fuerza la renovación al volver.
2. **Una sola renovación en vuelo.** Dos peticiones simultáneas con el token vencido tienen que compartir la misma promesa, no pedir dos renovaciones —con rotación de tokens, la segunda llegaría con uno ya quemado.
3. **Sincronía entre pestañas**, por el evento `storage`: cerrar sesión en una no puede dejar a la otra creyendo que sigue adentro.

### 8.8 Verificación del JWT en el backend

**Firma asimétrica, ES256** (ECDSA sobre la curva P-256). La privada vive en el servidor y sólo firma; la pública sólo verifica.

| Dato | Valor |
|---|---|
| Algoritmo | `ES256` |
| Clave privada | archivo montado en el contenedor de la API, nunca en el repositorio |
| Clave pública | variable de entorno; es la única que necesita el verificador |
| Audiencia | `authenticated` |
| Vigencia del token de acceso | 3600 s |
| Tolerancia de reloj | 30 s |

Esto obliga a `PyJWT[crypto]`: sin el extra `crypto` (que trae `cryptography`), PyJWT falla con `MissingCryptographyError` al intentar ES256.

```python
# api/app/core/security.py
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

bearer = HTTPBearer(auto_error=False)

async def current_user_id(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión requerida")
    try:
        payload = jwt.decode(
            cred.credentials,
            settings.JWT_PUBLIC_KEY,
            algorithms=["ES256"],
            audience="authenticated",
            leeway=30,
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida")
    return payload["sub"]
```

Todas las rutas bajo `/api` dependen de `current_user_id`. **No existe endpoint de datos sin autenticación.** Lo único público es `/api/health`.

La verificación es **local**: no hay viaje de red, ni caché de claves, ni dependencia de que un servicio ajeno responda. La versión anterior buscaba la clave pública en un endpoint remoto; eso desapareció junto con el proveedor, y con ello un arranque en frío más lento y un punto de falla.

**Tolerancia de reloj de 30 segundos, y no es comodidad.** Sin eso, un token recién emitido se rechaza si el reloj del servidor está apenas atrasado: medido en su momento, **0,2 segundos de desfase bastaban** para fallar con «the token is not yet valid (iat)». En producción se vería como un 401 intermitente justo después de entrar, imposible de reproducir a voluntad.

Hacia afuera, un token inválido dice siempre «la sesión no es válida». **No se cuenta por qué**: «firma incorrecta» o «audiencia equivocada» le dicen a quien está probando exactamente qué le falta ajustar. El detalle va al registro.

### 8.9 Reglas de contraseña

El servidor valida el mínimo; la interfaz lo refuerza para dar una respuesta inmediata:

- Mínimo **8 caracteres**, comprobado en el servidor y en la pantalla.
- Se muestra un medidor de fortaleza orientativo, nunca bloqueante más allá del mínimo.
- El campo tiene **botón de mostrar y ocultar**: escribir una contraseña a ciegas en un teléfono es la principal causa de errores de tipeo.
- En el registro se pide **repetir** la contraseña; en el login, no.
- Nunca se dice si un email existe o no. Login y registro responden igual ante un email desconocido y ante una contraseña equivocada. Evita que el formulario se convierta en un verificador de cuentas.

### 8.10 Protección contra abuso

Al haber registro abierto, hay que acotar el abuso:

- **Límite de intentos de login por dirección IP y por cuenta**, con espera creciente. Es la única defensa real contra probar contraseñas a mano.
- `scripts/` incluye una consulta para revisar las cuentas creadas, por si hiciera falta limpiar.
- Para **cerrar el registro**, una variable de entorno (`REGISTRO_ABIERTO=false`) que rechaza `signup` y hace que el frontend oculte el enlace. A esta escala puede ser lo razonable: las cuentas las crea Gustavo.

### 8.11 Dónde se guarda la sesión en el cliente

`localStorage`, gestionado por `auth.js` y por nadie más. Se evaluó la alternativa de cookie `HttpOnly` —más resistente a XSS— y se mantiene la decisión original: con el frontend y la API en el mismo dominio dejó de haber un impedimento técnico, pero el cambio obliga a rehacer el manejo de sesión de los seis módulos que hoy piden el token, y no es lo que está en juego en este traslado. Queda anotado como mejora posible. Como compensación se aplican las mitigaciones de XSS de la sección 17: Content Security Policy estricta y cero `innerHTML` con datos sin escapar.

---

## 9. API REST

Base: `/api`. JSON en todo. Fechas en ISO 8601 (`2026-10-03`). Importes como **string decimal** (`"42000.00"`) para no perder precisión en JavaScript; el frontend los convierte con un helper único.

### 9.1 Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/api/health` | Estado del servicio, esquema activo y conectividad con la base. Público. |
| `GET` | `/api/me` | Perfil, saldo inicial, preferencias. |
| `PATCH` | `/api/me` | Actualizar nombre visible y saldo inicial. |
| `POST` | `/api/me/bootstrap` | Red de seguridad: crea el perfil y las 21 categorías si el trigger no corrió. Idempotente. |
| `GET` | `/api/dashboard?year&month` | **Respuesta única del dashboard** (ver 9.2). |
| `GET` | `/api/months` | Lista de meses con sus totales y saldo acumulado. |
| `GET` | `/api/months/savings-evolution` | El saldo acumulado real, un punto por mes (gráfico de evolución del ahorro, F06-T07). |
| `GET` | `/api/months/{id}` | Detalle de un mes con totales por categoría. |
| `POST` | `/api/months/historical` | Crear o actualizar un mes histórico consolidado. |
| `PATCH` | `/api/months/{id}` | Corregir un mes histórico. |
| `GET` | `/api/transactions` | Filtros: `year`, `month`, `type`, `category_id`, `date_from`, `date_to`, `q`, `limit`, `offset`. |
| `POST` | `/api/transactions` | Alta. Recalcula el mes. |
| `PUT` | `/api/transactions/{id}` | Edición. Recalcula el mes. |
| `DELETE` | `/api/transactions/{id}` | Baja. Recalcula el mes. |
| `GET` | `/api/categories` | Lista con filtro `type` y `active`. |
| `POST` | `/api/categories` | Alta. |
| `PUT` | `/api/categories/{id}` | Edición, activar y desactivar. |
| `PATCH` | `/api/categories/reorder` | Reordenamiento por lote. |
| `GET` | `/api/categories/{id}/detail?year&month` | Total del mes, última carga y movimientos de esa categoría (General §16, F07-T01). `transactions: null` si el mes es histórico. |
| `GET` | `/api/categories/{id}/history?months=N` | La serie mes a mes de esa categoría y las seis cifras del pie (F13-T02). `months=0` o ausente es todo el histórico; el recorte es por el final (los N más nuevos). Un mes sin esa categoría viene con `total: null`, **nunca cero**. Los meses consolidados entran igual que los abiertos: sale de `monthly_category_totals`. |
| `GET` | `/api/dues` | Los ítems con su vencimiento y el estado de hoy (F13-T03). Una fila por categoría de **egreso activa**, tenga o no vencimiento configurado. Con `enabled: false`, `state` y `severity` vienen en `null`. |
| `PUT` | `/api/dues/{category_id}` | Prende, apaga o reconfigura el vencimiento de un ítem. Upsert: no hay alta ni baja, porque los ítems ya existen. Reemplaza los tres campos juntos. Una categoría de ingreso da 404. |
| `GET` | `/api/investments` | Cartera con totales y rendimientos. |
| `POST` | `/api/investments` | Alta de posición. No toca el ahorro (§7.3). |
| `PUT` | `/api/investments/{id}` | Edición y actualización manual de valor. |
| `DELETE` | `/api/investments/{id}` | Venta. No toca el ahorro (§7.3). |
| `POST` | `/api/investments/refresh-prices` | Actualiza cotizaciones. Devuelve qué se actualizó y qué falló. |
| `GET` | `/api/employment` | Historial salarial con variaciones calculadas. |
| `POST` | `/api/employment` | Alta de registro laboral. |
| `PUT` | `/api/employment/{id}` | Edición. |
| `DELETE` | `/api/employment/{id}` | Baja. |
| `GET` | `/api/patrimony` | Ahorros, inversiones, pasivos, patrimonio neto y composición. |
| `GET` | `/api/analytics` | Métricas históricas de la sección 53 del general. |
| `GET` | `/api/alerts` | Alertas no descartadas. |
| `POST` | `/api/alerts/evaluate` | Reevalúa y genera alertas. |
| `POST` | `/api/alerts/{id}/read` | Marcar leída. |
| `POST` | `/api/alerts/{id}/dismiss` | Descartar. |
| `GET` | `/api/export?format=json\|csv` | Exportación de respaldo. |
| `GET` | `/api/settings` · `PUT` | Preferencias. |

### 9.2 `GET /api/dashboard` — el contrato central

Una sola llamada alimenta todo el dashboard. Evita seis peticiones en el arranque, que en 4G es la diferencia entre rápido y lento.

```jsonc
{
  "month": {
    "id": 7, "year": 2026, "month": 10,
    "label": "Octubre 2026",
    "status": "open",                    // "open" | "historical"
    "consolidated": false,
    "income_total": "3541280.00",
    "expense_total": "2419425.00",
    "saving_total": "1121855.00",
    "saving_rate": "31.7",               // null si income_total = 0
    "is_current": true
  },
  "navigation": {
    "previous": { "year": 2026, "month": 9 },
    "next": null,                        // null = no hay mes siguiente cargable
    "current": { "year": 2026, "month": 10 }
  },
  "indicators": {
    "income": "3541280.00",
    "expense": "2419425.00",
    "saving": "1121855.00",
    "savings_balance": "8649377.00",
    "investments_value": "37714543.00",
    "net_worth": "46363920.00",
    "vs_previous": { "income": "1.4", "expense": "-16.6", "saving": "90.6" }
  },
  "daily": {                             // null cuando el mes es histórico
    "days": 24,
    "income":  ["3491280.00", "0.00", "..."],
    "expense": ["763400.00", "78200.00", "..."],
    "saving_cumulative": ["2727880.00", "2649680.00", "..."],
    "peak_expense": { "day": 10, "amount": "311225.00" },
    "days_without_expense": 0
  },
  "last_six_months": [
    { "year": 2026, "month": 5, "label": "Junio 2026",
      "income": "4988971.00", "expense": "2690300.00",
      "saving": "2298671.00", "saving_rate": "46.1" }
  ],
  "categories": [
    { "category_id": 10, "name": "Alquiler", "type": "expense",
      "total": "553000.00", "share": "22.9", "variation": "0.0",
      "transaction_count": 1, "last_date": "2026-10-01" }
  ],
  "alerts": [
    { "id": 3, "type": "category_above_average", "severity": "warning",
      "title": "Mercadería sobre el promedio",
      "message": "Este mes llevás ..." }
  ]
}
```

`daily.saving_cumulative` es la serie que dibuja **la línea de ahorro sobre el gráfico de barras**, el cambio que pediste sobre el mockup.

El ciclo de vida de la cuenta vive bajo `/api/auth` y es el único grupo de endpoints **públicos** además de `/api/health`: `signup`, `login`, `refresh`, `logout`, `reset`. `cambiar-clave` sí exige sesión. El detalle está en §8.3.

### 9.3 Formato de errores

Uniforme en toda la API, para que el frontend tenga un único camino de manejo:

```jsonc
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "La suma de las categorías no coincide con el total de egresos.",
    "details": [
      { "field": "categories", "expected": "2419425.00", "received": "2401225.00" }
    ]
  }
}
```

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Datos mal formados o reglas de negocio violadas |
| 401 | `UNAUTHENTICATED` | Falta el token, está vencido o es inválido |
| 403 | `FORBIDDEN` | El recurso existe pero no es del usuario |
| 404 | `NOT_FOUND` | No existe |
| 409 | `CONFLICT` | Mes duplicado, nombre de categoría repetido |
| 422 | `UNPROCESSABLE` | Error de esquema de Pydantic |
| 502 | `UPSTREAM_ERROR` | Falló el proveedor de cotizaciones |
| 500 | `INTERNAL_ERROR` | Lo inesperado. Nunca expone stack trace al cliente. |

### 9.4 Validaciones de entrada

| Entidad | Reglas |
|---|---|
| Movimiento | `amount > 0`; `category_id` existe, está activa y su `type` coincide con `transaction_type`; `transaction_date` válida y dentro del mes indicado; `description` ≤ 500 caracteres |
| Mes histórico | `year`/`month` válidos y no futuros; totales ≥ 0; si vienen categorías, su suma se compara con el total de egresos y se advierte la diferencia |
| Categoría | `name` obligatorio, 1–60 caracteres, único por tipo; `type` ∈ {income, expense} |
| Inversión | `symbol` y `name` obligatorios; `investment_type` del enum; `initial_value > 0` (precio de compra); `nominal_quantity ≥ 0`, informativo, no entra en ninguna cuenta (revisado 2026-10-20) |
| Registro laboral | `company`, `position`, `salary ≥ 0`, `effective_date` válida |
| Preferencias | `theme` ∈ {light, dark, null}; `null` borra la preferencia guardada (F11-T01) |

No se permite seleccionar un mes futuro que todavía no exista (sección 12.1 del general): `navigation.next` llega en `null` y el botón se deshabilita.

### 9.5 Proveedor de cotizaciones

Interfaz desacoplada, tal como pide la sección 25 del documento general. Nunca se depende de una sola fuente.

```python
# api/app/services/prices/base.py
from typing import Protocol
from decimal import Decimal
from datetime import datetime

class Quote(TypedDict):
    symbol: str
    unit_price: Decimal
    as_of: datetime
    source: str

class InvestmentPriceProvider(Protocol):
    name: str
    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]: ...
```

Implementaciones, en orden de intento: `ByMaProvider` → `PublicProvider` → `ManualProvider` (que no consulta nada y deja el valor como está). El orquestador recorre la cadena, cachea en `investment_price_cache`, y **por cada símbolo que no se pudo actualizar genera una alerta** `investment_price_stale`. Nunca falla toda la operación por un símbolo: devuelve `{"updated": [...], "failed": [...]}`.

Advertencia registrada: según su documentación, las APIs de Market Data de BYMA están disponibles para personas jurídicas. **No se asume acceso**: la arquitectura trata la actualización automática como un extra y la carga manual como el camino garantizado.

### 9.6 Límite de frecuencia

No se requiere tiempo real (sección 26). El endpoint de refresco tiene un límite de **una ejecución cada 15 minutos por usuario**, y la interfaz muestra la fecha de última actualización. Así se evita consumir cuota sin necesidad.

---

## 10. Estructura del repositorio

```text
epic-wallet/
├── api/                              # backend (FastAPI sobre uvicorn)
│   ├── index.py                      # punto de entrada: expone `app`
│   └── app/
│       ├── main.py                   # creación de FastAPI, middlewares, errores
│       ├── core/
│       │   ├── config.py             # Settings con pydantic-settings
│       │   ├── db.py                 # engine, sesión, propagación del JWT
│       │   ├── security.py           # verificación del JWT
│       │   └── errors.py             # excepciones y handlers
│       ├── models/                   # modelos SQLAlchemy
│       ├── schemas/                  # esquemas Pydantic (entrada/salida)
│       ├── repos/                    # consultas
│       ├── services/
│       │   ├── calc.py               # cálculos puros
│       │   ├── months.py             # recálculo y cierre
│       │   ├── dashboard.py          # armado de la respuesta del dashboard
│       │   ├── investments.py
│       │   ├── analytics.py
│       │   ├── alerts.py
│       │   └── prices/               # proveedores de cotización
│       └── routers/                  # un archivo por recurso
├── web/                              # frontend estático
│   ├── index.html
│   ├── manifest.json
│   ├── service-worker.js
│   ├── icons/
│   ├── src/
│   │   ├── styles/
│   │   │   ├── tokens.css            # tokens del mockup (@theme)
│   │   │   ├── base.css              # fondo, ruido, tipografía
│   │   │   └── components.css        # .shell, .cg, .kpi, .row, .sheet…
│   │   ├── app.css                   # entrada de Tailwind
│   │   └── js/
│   │       ├── main.js               # arranque
│   │       ├── router.js             # navegación por hash
│   │       ├── api.js               # cliente HTTP + manejo de errores
│   │       ├── auth.js               # sesión: login, token y renovación
│   │       ├── state.js              # estado y caché en memoria
│   │       ├── format.js             # fmt, fmtK, pct, fechas
│   │       ├── charts/               # daily, six, categories, line, stack
│   │       ├── components/
│   │       └── views/               # login, registro, recuperar, nueva-clave,
│   │                                # inicio, movimientos, historial,
│   │                                # inversiones, patrimonio, config
│   └── public/                       # CSS compilado y assets
├── migrations/                       # Alembic
├── scripts/
│   ├── seed_categories.py            # categorías iniciales del general
│   ├── seed_demo.py                  # datos de demostración
│   └── load_history.py               # carga asistida de meses históricos
├── tests/
│   ├── unit/                         # calc.py y servicios
│   ├── api/                          # endpoints
├── docs/                             # documentación por fase (ver roadmap)
├── .env.example
├── package.json                      # Tailwind CLI y scripts
├── pyproject.toml                    # dependencias y config de ruff/mypy
└── compose.yml                        # api + postgres, para el servidor
```

---

## 11. Configuración y variables de entorno

```ini
# .env.example
# --- Base de datos ---
# El host es el nombre del servicio de Postgres dentro del compose.
DATABASE_URL=postgresql+psycopg://epic:CONTRASENA@db:5432/epic_wallet
DB_SCHEMA=public                         # único esquema del proyecto — ver §4.1.1
# sólo para los tests de cálculo:
# DATABASE_URL=sqlite+pysqlite:///./test.db
# DB_SCHEMA=main

# --- Autenticación ---
# Par de claves ES256 del proyecto. La privada se monta como archivo en
# el contenedor y NUNCA entra al repositorio; la pública puede ir en el
# entorno, porque sólo sirve para verificar.
JWT_PRIVATE_KEY_FILE=/run/secrets/jwt_private.pem
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----"
JWT_TTL_MINUTOS=60                       # vida del token de acceso
REFRESH_TTL_DIAS=30                      # vida del token de renovación
REGISTRO_ABIERTO=true                    # false cierra el alta de cuentas (§8.10)

# URL pública, para armar los links de recuperación (§8.6).
PUBLIC_APP_URL=https://13-140-36-93.sslip.io

# --- Aplicación ---
APP_ENV=production                       # development | preview | production
APP_TIMEZONE=America/Argentina/Buenos_Aires
ALLOWED_ORIGINS=https://13-140-36-93.sslip.io
PRICE_PROVIDER_ORDER=byma,public,manual
PRICE_REFRESH_COOLDOWN_MINUTES=15
LOG_LEVEL=INFO
```

Reglas no negociables:

- **La clave privada de firma nunca sale del servidor** y nunca se escribe en el repositorio. Si se filtrara, cualquiera podría fabricar sesiones de cualquier usuario. Es el único secreto del proyecto con esa propiedad.
- **El frontend no recibe ningún secreto.** `web/public/config.js`, generado en el build, lleva únicamente la URL de la API. `tests/unit/test_secretos_fuera_del_frontend.py` revisa todos los archivos versionados.
- **La contraseña de Postgres** vive en el `.env` del servidor, que no se versiona. La base no publica ningún puerto al exterior: sólo la alcanza la API, por la red interna del compose.
- `DB_SCHEMA` es siempre `public` (§4.1.1); `scripts/check_db.py` verifica que esté definida y que valga eso. Lo que sí exige `APP_ENV=production` explícito en la línea de comando es **migrar** (`migrations/env.py`, §16.4): es la operación destructiva del proyecto, y que pida ser consciente es deliberado.

---

## 12. Frontend

### 12.1 Una página, seis vistas

Igual que el mockup: un solo `index.html` con seis `<section class="view">`, de las cuales una está activa. La navegación cambia el hash (`#/inicio`, `#/movimientos`, …), lo que da historial del navegador y botón "atrás" sin recargar.

*(Revisado 2026-10-21: "Análisis" se sacó de la navegación — ver General §47.)*

```javascript
// web/src/js/router.js
// Rutas públicas (sin sesión) y privadas (con sesión).
const PUBLICAS = ['login','registro','recuperar','nueva-clave'];
const PRIVADAS = ['inicio','movimientos','historial','inversiones',
                  'patrimonio','config'];
const routes = [...PUBLICAS, ...PRIVADAS];

export function navigate(id, { replace = false } = {}) {
  if (!routes.includes(id)) id = 'inicio';
  const url = `#/${id}`;
  replace ? history.replaceState(null,'',url) : history.pushState(null,'',url);
  render(id);
}

window.addEventListener('popstate', () => render(currentRoute()));
```

### 12.2 Estado y caché

Objeto único en memoria, sin librería. El dashboard se cachea por mes para que volver a un mes ya visto sea instantáneo; cualquier escritura invalida el caché del mes afectado y de los posteriores (porque el saldo acumulado es una suma corrida).

```javascript
// web/src/js/state.js
export const state = {
  user: null,
  view: { year: null, month: null },
  cache: new Map(),              // "2026-10" -> respuesta de /api/dashboard
  categories: [],                // se piden una vez
  ui: { catSort:'amount', dailyMode:'both', sixMode:'bars', movFilter:'all' },
};

export function invalidateFrom(year, month) {
  for (const key of [...state.cache.keys()])
    if (key >= `${year}-${String(month).padStart(2,'0')}`) state.cache.delete(key);
}
```

### 12.3 Cliente de API

Un solo punto de salida: agrega el token, maneja el 401 renovando la sesión y reintentando una vez, y traduce los errores al formato de toast.

```javascript
// web/src/js/api.js
import { getToken, refresh } from './auth.js';

async function request(path, options = {}, retry = true) {
  const res = await fetch(`/api${path}`, {
    ...options,
    headers: { 'Content-Type':'application/json',
               Authorization: `Bearer ${await getToken()}`,
               ...options.headers },
  });
  if (res.status === 401 && retry) { await refresh(); return request(path, options, false); }
  const body = res.status === 204 ? null : await res.json();
  if (!res.ok) throw new ApiError(body?.error ?? { code:'INTERNAL_ERROR' });
  return body;
}

export const api = {
  dashboard: (y,m)      => request(`/dashboard?year=${y}&month=${m}`),
  createTransaction: (d) => request('/transactions', { method:'POST', body: JSON.stringify(d) }),
  deleteTransaction: (id)=> request(`/transactions/${id}`, { method:'DELETE' }),
  // …
};
```

### 12.4 Componentes

Funciones que reciben datos y devuelven un string de HTML, igual que el mockup. Sin ciclo de vida ni estado interno.

```javascript
// web/src/js/components/kpi.js
export function kpiMetric({ label, value, sub, color, icon }) {
  return `<article class="kpi kpi-metric shell" style="--c:${color}">
    <div class="kpi-top">
      <div class="kpi-label">${esc(label)}</div>
      <span class="kpi-ico"><svg viewBox="0 0 24 24">${icon}</svg></span>
    </div>
    <div class="kpi-num num">${esc(value)}</div>
    <div class="kpi-sub">${sub}</div>
  </article>`;
}
```

**Regla de seguridad obligatoria:** todo dato que venga del backend pasa por `esc()` antes de entrar en una plantilla. Una descripción de movimiento con `<script>` no puede ejecutarse.

```javascript
// web/src/js/format.js
export const esc = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
```

### 12.5 Manejo de importes

El backend manda strings decimales. El frontend los convierte en un único lugar y nunca hace aritmética financiera: sólo formatea.

```javascript
export const toNum = v => Number(v ?? 0);
export const fmt   = v => '$' + Math.round(Math.abs(toNum(v))).toLocaleString('es-AR');
export const fmtS  = v => (toNum(v) < 0 ? '−' : '') + fmt(v);
export const fmtK  = v => { /* $1,2M · $340k · negativos con − */ };
export const pct   = v => v == null ? 'N/A'
  : (toNum(v) > 0 ? '+' : toNum(v) < 0 ? '−' : '') +
    Math.abs(toNum(v)).toFixed(1).replace('.',',') + '%';
```

### 12.6 Estados de carga, error y vacío

Cada vista implementa los cuatro estados. No se muestra una pantalla en blanco nunca.

| Estado | Tratamiento |
|---|---|
| Cargando | Esqueletos con la forma del contenido final (mismas alturas, para que no salte el layout) |
| Error | Tarjeta con el mensaje y un botón "Reintentar" |
| Vacío | Texto explicativo. Para un mes consolidado, el texto específico: "Información histórica consolidada" |
| Sin conexión | Banda superior "Sin conexión — se muestran los últimos datos guardados" y lectura desde el caché del service worker |

---

## 13. Sistema de estilo

Esta sección es **normativa**. Ningún componente nuevo introduce colores, sombras ni radios fuera de estos tokens.

> **F20-T01, 2026-11-27.** El sistema es **Neumorfismo**, aprobado por Gustavo sobre un mockup de prueba de cuatro pantallas. Reemplaza a **Vidrio Grafito**, que rigió desde la Fase 1 y está en el historial de Git junto con su mockup. Lo que sigue describe el sistema vigente; donde algo cambió de raíz, se dice qué había antes y por qué.

### 13.1 Identidad

Una sola pieza de material. El relieve no es un borde ni una capa encima: son **dos sombras del mismo material** —una abajo-derecha oscura y una arriba-izquierda clara— sobre una superficie que es casi el mismo color que el fondo. De ahí sale toda la profundidad de la interfaz.

**La gramática tiene dos palabras y hay que respetarlas:**

| Forma | Qué significa | Dónde |
|---|---|---|
| **Levantado** | esto se toca | tarjetas, paneles, botones, píldoras, barras, hojas |
| **Hundido** | esto está elegido, o es un contenedor de contenido | surco del conmutador, campo de texto, bloque de gráfico, fila, botón apretado |

Un botón que se hunde al apretarlo y un filtro que queda hundido mientras está activo son la misma idea, y es lo que hace que el sistema se entienda sin explicarlo.

**Las dos paletas, con su reparto:**

| Tema | 60% material | 30% dato y acción | 10% señal |
|---|---|---|---|
| claro | Ivory Porcelain `#f1ece3` | Jade Lacquer `#1d6b58` | Scarlet Signal `#c62b36` |
| oscuro | Raven Black `#191c21` | Pewter Grey `#8d949d` | Molten Orange `#ff6a1f` |

**Sin neón, sin saturaciones altas, sin degradados estridentes.** El color se usa para significar (ingreso, egreso, ahorro, alerta), no para decorar. Y una regla que es propia de este sistema: **el fondo no tiene dibujo propio**. Los lavados radiales de color y la capa de ruido de Vidrio Grafito se fueron en F20-T01, porque cualquier textura detrás de las dos sombras de una pieza se lee como suciedad alrededor del borde.

### 13.2 Tokens

Se declaran en `web/src/styles/tokens.css` y se registran en Tailwind con `@theme`, de modo que se puedan usar como `text-ink-3` además de como `var(--color-ink-3)`.

**Los nombres de token no cambiaron con el sistema.** `--glass-shell-bg` sigue llamándose así y ahora vale un color sólido; `--sh-md` sigue siendo «la sombra de una pieza» y ahora son dos. Se conservaron a propósito: renombrar 4.700 líneas de CSS para cambiar de estilo es de donde salen los `var()` sin definir, que no avisan (§13.3.2).

```css
@theme {
  /* material */
  --color-bg-1: #ebe5db;  --color-bg-2: #e7e0d5;

  /* tinta: 4 niveles, calibrados sobre la pieza (#f1ece3) */
  --color-ink:   #2a2620;  /* 12,8:1 · títulos y cifras */
  --color-ink-2: #544d44;  /*  7,4:1 · texto normal */
  --color-ink-3: #6d665b;  /*  4,9:1 · secundario y etiquetas */
  --color-ink-4: #8c8373;  /*  3,1:1 · deshabilitado y ejes */

  /* acento: Jade Lacquer */
  --color-accent: #1d6b58;  --color-accent-2: #14503f;
  --color-on-accent: #f3efe6;

  /* semántica financiera */
  --color-inc: #1d6b58;  --color-egr: #c62b36;  --color-sav: #1d6b58;

  /* las cuatro tarjetas teñidas del tablero */
  --color-card-inc: #1d6b58;  --color-card-egr: #c62b36;
  --color-card-dia: #5f7d72;  --color-card-pat: #1d6b58;

  /* severidad de alertas */
  --color-ok: #1d6b58; --color-warn: #9c7400;
  --color-pend: #b35a16; --color-crit: #c62b36;
}
```

**La severidad dobla la paleta a propósito.** Con tres colores no se pueden representar cuatro severidades: `warn` y `pend` son un ámbar y un naranja quemado, dentro de la temperatura cálida del material. Siguen cumpliendo la regla que importa: el color nunca es el único portador — cada severidad lleva su icono y su nombre.

Fuera de `@theme`, en `:root`, viven las superficies y el relieve:

```css
:root{
  /* las dos sombras: todo lo demás se arma con éstas */
  --sh-lo: rgba(170,158,138,.52);   /* el material en sombra */
  --sh-hi: #fffdf8;                 /* el material iluminado */

  /* las superficies */
  --surf:   #f1ece3;   /* la pieza levantada */
  --surf-2: #e7e0d5;   /* lo hundido */
  --kpi-surf:#e8e1d4;  /* base de la tarjeta de indicador */

  /* levantado, a tres distancias */
  --sh-sm: 4px 4px  9px var(--sh-lo), -4px -4px  9px var(--sh-hi);
  --sh-md: 6px 6px 14px var(--sh-lo), -6px -6px 14px var(--sh-hi);
  --sh-lg: 9px 9px 20px var(--sh-lo), -8px -8px 18px var(--sh-hi);

  /* hundido, a dos profundidades */
  --hundido:    inset 5px 5px 11px var(--sh-lo), inset -5px -5px 11px var(--sh-hi);
  --hundido-sm: inset 3px 3px  7px var(--sh-lo), inset -3px -3px  7px var(--sh-hi);

  /* el canto iluminado de una pieza levantada: no es un borde */
  --glass-in: inset 1px 1px 0 rgba(255,253,248,.75);
  --borde-pieza: transparent;

  /* la tarjeta héroe, única superficie maciza */
  --hero: #1d6b58;  --on-hero: #fffaf6;
}
```

Tema oscuro: **las mismas variables redefinidas** bajo `html[data-theme="dark"]` y bajo `@media (prefers-color-scheme: dark)`. Ningún componente conoce el tema; sólo usa tokens.

```css
html[data-theme="dark"]{
  --color-bg-1:#13151a; --surf:#191c21; --surf-2:#14171b; --kpi-surf:#23272d;
  --sh-lo: rgba(0,0,0,.70);  --sh-hi: rgba(86,94,104,.30);
  --color-accent:#8d949d; --color-on-accent:#14171b;
  --color-inc:#a7aeb6; --color-egr:#ff6a1f; --color-sav:#ff8a4c;
  --hero:#c4511a; --on-hero:#fffaf6;   /* naranja profundo: el texto va en blanco */
  /* …más el resto */
}
```

**Dos pares de sombras de color, no uno.** `--hero-sh-*` tiñe los dos lados y es sólo para la tarjeta héroe; `--acc-sh-*` tiñe el lado oscuro y deja el claro en la luz del material, y es para toda pieza chica de acento (el sello, el botón principal, la píldora sólida). En una pieza de 46 px el halo de color se lee como un aura verde —naranja en oscuro— alrededor del botón. Se vio en la primera captura de F20-T01.

### 13.3 Las dos capas del material

Toda la profundidad de la interfaz sale de dos clases. No se inventan variantes.

| Clase | Uso | Forma | Fondo (claro) |
|---|---|---|---|
| `.shell` | Contenedores: topbar, tarjetas, paneles, hojas, navegación | levantado: `--glass-in, --sh-md` | `#f1ece3` |
| `.cg` | Contenido dentro de un `.shell`: filas, fichas, campos | hundido: `--hundido-sm` | `#e7e0d5` |

Ninguna de las dos lleva borde (`--borde-pieza` es transparente): con relieve, un borde alrededor de la pieza es justo lo que rompe la ilusión de que el material es uno solo. El píxel se conserva para no cambiarle la caja al CSS que ya lo cuenta.

**Ninguna de las dos lleva `backdrop-filter`, y no es un olvido.** El sistema no tiene desenfoque en ninguna parte: ni las tarjetas, ni las barras, ni el velo de una hoja abierta. Dejarlo en `blur(0)` habría sido peor que sacarlo, porque el navegador crea igual la capa de respaldo y paga el costo de GPU para no desenfocar nada. Los bloques `@supports not (backdrop-filter)` se conservan como red y no hacen nada: los tokens de respaldo valen el mismo color sólido.

Una consecuencia que se agradece: las dos reglas que apagaban el desenfoque durante una *view transition* —el círculo del cambio de tema y el deslizo entre vistas, que en el teléfono arrancaban trabados con una pantalla entera de vidrio— ya no hacen falta. El movimiento arranca liso por construcción.

### 13.4 Tipografía

Escala aprobada, ya aumentada respecto del mockup original según tu pedido. Base **16,5 px** con interlineado 1,55.

| Rol | Fuente | Tamaño | Peso |
|---|---|---|---|
| Cifra héroe (ahorro, patrimonio) | Outfit | 35 px | 700 |
| Cifra de KPI | Outfit | 28 px | 700 |
| Cifra de KPI secundario | Outfit | 24 px | 700 |
| Título de panel | Outfit | 20 px | 700 |
| Texto base | Inter | 16,5 px | 400 |
| Nombre en fila de lista | Inter | 15 px | 600 |
| Secundario de fila | Inter | 12,5 px | 400 |
| Etiqueta de KPI | Inter | 11,5 px | 700, mayúsculas, `letter-spacing: .07em` |
| Eje de gráfico | Inter | 10–10,5 px | 600 |

Las cifras usan `font-variant-numeric: tabular-nums` siempre, para que no "bailen" al actualizarse.

### 13.5 Puntos de corte

Mobile-first: el CSS base es el de teléfono y todo lo demás se agrega con `min-width`.

| Corte | Ancho | Qué cambia |
|---|---|---|
| base | < 640 px | Una columna. KPI en 2 columnas. Barra inferior de navegación. Botón `+` flotante. Detalles en hoja inferior. |
| `sm` | ≥ 640 px | KPI en 4 columnas. |
| `md` | ≥ 720 px | Cabeceras de panel en fila. Gráficos sin scroll horizontal. |
| `lg` | ≥ 960 px | Navegación superior en lugar de la inferior. Paneles en dos columnas. |
| `xl` | ≥ 1024 px | KPI en 6 columnas. Panel de detalle como cajón lateral derecho. |

Áreas táctiles de 44 × 44 px como mínimo. Respeto de `env(safe-area-inset-bottom)` en la navegación y el botón flotante.

### 13.6 Movimiento

| Gesto | Duración | Curva |
|---|---|---|
| Entrada de vista | 420 ms | `--ease-glass` |
| Entrada de tarjetas (escalonada) | 500 ms, +60 ms por tarjeta | `--ease-glass` |
| Hoja inferior y cajón | 380 ms | `--ease-glass` |
| Hover de tarjeta y fila | 180–220 ms | `--ease-glass` |
| Crecimiento de barras | 750 ms, +11 ms por barra | `--ease-glass` |
| Trazado de líneas | 1400 ms (`stroke-dashoffset`) | `--ease-glass` |
| Conteo de cifras | 900 ms | cúbica de salida |
| Cambio de tema | View Transitions API si existe | — |

**`@media (prefers-reduced-motion: reduce)` anula todas las animaciones.** Es obligatorio, no opcional.

### 13.7 Accesibilidad

- Contraste mínimo 4,5:1 para texto normal en ambos temas. Se verifica con un script en CI sobre los pares de tokens.
- El color nunca es el único portador de información: ingreso y egreso llevan además signo (`+` / `−`) e icono de flecha.
- Navegación completa por teclado con foco visible (`box-shadow: 0 0 0 4px var(--accent-ring)`).
- `aria-label` en todos los botones de sólo icono; `aria-live="polite"` en el toast; `aria-expanded` en lo que se expande.
- Los gráficos SVG llevan `role="img"` y un `<title>` con el resumen en texto, y debajo están **siempre los números** (requisito de la sección 12.2 del general: el gráfico no reemplaza los números).

---

## 14. Especificación de los gráficos

Cinco gráficos, todos en SVG generado por JavaScript, con `viewBox` para escalar y colores por variable CSS para heredar el tema.

### 14.1 Gráfico diario — barras con línea de ahorro

El principal del dashboard y el único con **doble eje**. Implementa la sección 13 del general más el cambio pedido sobre el mockup.

```text
Eje X        días del mes (1…día actual)
Eje Y izq.   importe diario → barras
             · barra verde  = ingresos del día
             · barra roja   = egresos del día
Eje Y der.   ahorro del mes acumulado → línea (sólo en modo "Ambos")
             · línea azul grafito, 2,7 px
             · punto y etiqueta en el valor de hoy
             · línea de cero punteada si el ahorro se vuelve negativo
Modos        Ambos · Egresos · Ingresos
             (el modo "Acumulado" se probó y se sacó — Gustavo,
             F06-T02 — y la línea de ahorro quedó sólo en "Ambos":
             en los otros dos el eje izquierdo cambia de escala para
             esa serie sola, y la línea dejaba de hablar de lo mismo)
```

Por qué doble eje: el gasto diario se mueve en decenas de miles y el ahorro acumulado en millones. Con un solo eje la línea aplastaría las barras. La etiqueta "AHORRO" sobre el eje derecho y el color compartido con el token `--color-sav` evitan la confusión.

Lectura que habilita: se ve de un golpe el salto del día del sueldo y cómo el ahorro baja a lo largo del mes con cada gasto; exactamente "cómo va bajando o subiendo el ahorro".

**Lectura táctil (F06-T09):** mantener el dedo quieto sobre el gráfico muestra una línea guía más una etiqueta arriba, centrada en el día tocado, con el valor exacto debajo del dedo (día, ingreso, egreso y, en "Ambos", el ahorro acumulado). Centrada en el toque y no en un punto fijo del gráfico (segunda corrección): con el `.chart-wrap` scrolleado hacia el final del mes, una etiqueta pegada al borde izquierdo del `<svg>` entero quedaba fuera de lo que se ve — el dedo, por definición, siempre está sobre algo visible, así que centrar ahí la resuelve sin tener que calcular el scroll del contenedor. Se mide con `getBBox()` y se corrige sólo si se sale por un borde del `viewBox`.

No usa `touch-action` restringido: un primer intento le sacaba al navegador el gesto horizontal entero para que la lectura ganara siempre, y eso tapaba el scroll lateral del `.chart-wrap` en pantallas angostas — Gustavo lo probó y pidió devolverlo (primera corrección). La distinción entre "mantener quieto" y "arrastrar para scrollear" se hace en JavaScript con un pequeño retardo (350 ms) y un umbral de movimiento (10 px): si el dedo se mueve más que eso antes de cumplirse el retardo, se asume scroll y nunca se llama `preventDefault` ni `setPointerCapture`, así que el navegador scrollea como si este código no existiera. `charts/diario.js` expone `geometriaDeDias()`/`contenidoDeLectura()` puras y `conectarLectura()` para el cableado del gesto.

### 14.2 Resto

| Gráfico | Tipo | Series | Modos |
|---|---|---|---|
| Últimos seis meses | Barras agrupadas | Ingresos, egresos, ahorro | Barras · Ahorro · Tasa de ahorro |
| Gastos por categoría | Barras horizontales ordenadas de mayor a menor | Total por categoría | Mayor gasto · A–Z |
| Evolución del ahorro | Área con línea | Saldo acumulado por mes | — |
| Composición patrimonial | Barra apilada horizontal | Ahorro líquido, inversiones | — |
| Evolución salarial | Área con línea | Sueldo por fecha de vigencia | — |

La evolución patrimonial completa queda para una fase posterior, como indica el general.

### 14.3 Reglas comunes

- Ningún gráfico tiene sentido sin su versión numérica al lado: cada panel lleva un pie con las cifras clave.
- Escalas con `niceMax()` para que los ejes caigan en valores redondos.
- Mínimo de 1,5 px de alto en las barras, para que un gasto chico se vea.
- En móvil el `svg` tiene `min-width: 520px` dentro de un contenedor con scroll horizontal; a partir de 720 px se ajusta al ancho.
- Sin librería, sin canvas: SVG en el DOM, accesible e inspeccionable.
- **El cambio de tema ya redibuja solo, sin JavaScript** (verificado F06-T09): todo color de un gráfico sale de `var(--color-*)` puesto directo en `fill`/`stroke`/`stop-color`, y eso reacciona en vivo al cambiar `data-theme` en `<html>` — funciona igual con `document.startViewTransition()` de por medio (`tema.js`), porque el cambio de atributo sigue siendo síncrono dentro de su callback. Nadie tiene que volver a llamar `dibujar()` cuando cambia el tema. Si algún día un gráfico nuevo mostrara un color sin recolorearse solo, la causa casi segura es un color calculado una vez y guardado como string fijo en vez de dejarlo como referencia `var()` viva.

---

## 15. PWA

```jsonc
// web/manifest.json
{
  "name": "Epic Wallet",
  "short_name": "Epic Wallet",
  "description": "Gestión financiera personal",
  "start_url": "/?source=pwa",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "background_color": "#f1f2f3",
  "theme_color": "#f1f2f3",
  "lang": "es-AR",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ],
  "shortcuts": [
    { "name": "Nuevo gasto",  "url": "/#/nuevo?type=expense" },
    { "name": "Nuevo ingreso","url": "/#/nuevo?type=income" }
  ]
}
```

### 15.1 Estrategias del service worker

| Recurso | Estrategia | Motivo |
|---|---|---|
| `index.html` | Network first, cache de respaldo | Que una versión nueva se tome enseguida |
| CSS, JS, iconos, fuentes | Stale while revalidate | Arranque instantáneo |
| `GET /api/dashboard` | Network first con cache de respaldo | Sin conexión se ven los últimos datos, con el aviso de la sección 12.6 |
| Resto de `GET /api/*` | Network only | Datos que no tiene sentido mostrar viejos |
| `POST`, `PUT`, `DELETE` | Network only | **Nunca se encolan escrituras offline en el MVP** |

Decisión explícita: no hay escritura offline. Encolar un gasto cargado sin conexión y sincronizarlo después abre problemas de duplicados y de orden de recálculo que no valen la pena en la primera versión. Si no hay conexión, el formulario avisa y no guarda. Queda anotado como mejora futura.

El `theme_color` del manifest y el `<meta name="theme-color">` se actualizan al cambiar de tema, para que la barra de estado de Android acompañe.

---

## 16. Despliegue

### 16.1 Qué corre en el servidor

Un VPS propio con Docker. Tres piezas, en dos `docker compose` distintos:

```text
/opt/edge/            proxy de borde — ÚNICO dueño del 80 y el 443
    caddy             TLS automático, estáticos, enruta por dominio
    conf.d/           un archivo de sitio por proyecto

/opt/epic-wallet/     esta aplicación
    api               FastAPI sobre uvicorn — sin puerto publicado
    db                Postgres 17 — sin puerto publicado, volumen propio

/opt/jarvis/          el otro proyecto del servidor, independiente
```

**Ni la API ni la base publican puertos al exterior.** Lo único que escucha desde afuera es Caddy. `ss -tlnp` tiene que mostrar 22, 80 y 443, y nada más.

El proxy es compartido porque sólo puede haber un dueño del 443. Cada proyecto tiene su archivo en `conf.d/`, su red y su volumen: reiniciar uno no toca al otro.

```caddyfile
# /opt/edge/conf.d/epicwallet.caddy
13-140-36-93.sslip.io {
    encode gzip zstd
    handle /api/* { reverse_proxy epic-wallet-api:8000 }
    handle        { root * /srv/epic-wallet; try_files {path} /index.html; file_server }
    header { ... }   # las de la tabla de abajo
}
```

Cabeceras que se aplican:

| Ruta | Cabecera | Para qué |
|---|---|---|
| todo | `Content-Security-Policy` | `default-src 'self'`; sin dominios de terceros, porque ya no hay ninguno |
| todo | `X-Content-Type-Options: nosniff` | que el navegador no adivine tipos |
| todo | `X-Frame-Options: DENY` | no embebible en un iframe |
| todo | `Referrer-Policy: strict-origin-when-cross-origin` | no filtrar rutas al salir del sitio |
| todo | `Permissions-Policy` | cámara, micrófono y ubicación denegados: no se usan |
| todo | `Strict-Transport-Security` | HTTPS obligatorio por un año |
| `/api/*` | `Cache-Control: no-store` | los datos financieros no se cachean nunca |
| `/public/*` | `Cache-Control: immutable, 1 año` | el CSS compilado lleva hash |
| `/icons/*` | `Cache-Control: 1 semana` | |
| `/service-worker.js` | `Cache-Control: no-cache` | que una versión nueva se tome enseguida |

La CSP se simplificó al mudarse: antes tenía que permitir el dominio del proveedor de autenticación en `connect-src`. Ahora el navegador sólo habla con su propio origen.

Frontend y API comparten dominio, así que **no hay CORS** en producción. Sólo se configura para desarrollo local.

### 16.2 El esquema `auth` es nuestro

Las políticas RLS se escribieron contra `auth.uid()` y `profiles.id` referencia `auth.users`. Al dejar el proveedor externo, esas dos cosas pasan a ser del proyecto, **sin que las políticas ni el DDL cambien una línea**:

```sql
create schema if not exists auth;

create table auth.users (
  id                 uuid primary key default gen_random_uuid(),
  email              text not null unique,
  encrypted_password text not null,          -- bcrypt
  email_confirmed_at timestamptz,
  created_at         timestamptz not null default now()
);

-- Lee el mismo GUC que la aplicación ya seteaba por transacción.
create or replace function auth.uid() returns uuid
language sql stable as $$
  select nullif(current_setting('request.jwt.claims', true)::json ->> 'sub', '')::uuid
$$;

create role anon          nologin;
create role authenticated nologin;
grant authenticated to epic;   -- sin esto, `set local role` falla
```

**Por qué funciona sin tocar nada más:** `core/db.py` ya hacía `set local role authenticated` y `set_config('request.jwt.claims', …, true)` por transacción (§6.5). Esa pieza fue siempre nuestra; lo único prestado era la función que leía el claim.

### 16.3 Cómo se publica un cambio

```text
rama feat/F15-T03-compose
   │
   ├─ 1. lógica  → funciones puras + tests unitarios (verde en local)
   ├─ 2. backend → endpoint + tests de API
   ├─ 3. frontend→ interfaz conectada
   │
   ├─ push a GitHub
   ├─ en el servidor: git pull && docker compose up -d --build
   ├─ vos lo probás en el celular
   │
   ├─ aprobada  → merge a main → se marca [x] en el roadmap
   └─ rechazada → se corrige en la misma rama
```

El servidor baja el código con una **clave de despliegue de sólo lectura, generada dentro del servidor**: la privada no viaja por ningún lado y no sirve para escribir en el repositorio.

**Hay un solo entorno.** No hay previews por rama: con un servidor propio, montar un entorno efímero por rama es infraestructura que a esta escala no se paga sola. Se prueba en local y después en el servidor.

**Consecuencia a tener presente:** una prueba en el servidor escribe sobre los datos reales. Las tareas que prueban escritura usan una **segunda cuenta de prueba**, no la tuya; RLS garantiza que no se cruzan.

### 16.4 Migraciones

Las migraciones **no** corren automáticamente al desplegar: una migración fallida a mitad de camino deja la base en un estado que nadie pidió. Se ejecutan a mano, a conciencia.

Con un solo esquema (§4.1.1), **una migración toca los datos reales**. El procedimiento no es negociable:

```bash
# 1 · respaldo primero, siempre — y el script verifica el archivo que escribió
./scripts/respaldo.sh && ls -lh respaldos/

# 2 · generar la migración
DB_SCHEMA=public APP_ENV=production alembic revision --autogenerate -m "F03 meses"

# 3 · revisar a mano el archivo generado: que el downgrade esté escrito
#     y que no haya un drop que no esperabas

# 4 · aplicar
DB_SCHEMA=public APP_ENV=production alembic upgrade head

# 5 · verificar con /api/health, y recién entonces publicar el código
```

`DB_SCHEMA` y `APP_ENV` van explícitos en cada comando de Alembic. `migrations/env.py` los exige y no asume un valor por defecto: migrar es la operación destructiva del proyecto, y que pida ser explícita es deliberado.

**Toda migración tiene su `downgrade` escrito y revisado.** El orden es: respaldo, migrar, publicar. Nunca al revés, porque el código nuevo espera tablas que el viejo no usa.

### 16.5 Puesta en marcha inicial

Lo que hay que tener antes de la primera línea de lógica de negocio:

1. Repositorio en GitHub con la estructura de la sección 10.
2. El servidor con Docker, el proxy de borde sirviendo el dominio con certificado válido, y la clave de despliegue cargada.
3. El compose de la aplicación levantado, con el esquema migrado y el shim de `auth` (§16.2).
4. `/api/health` respondiendo a través del proxy.
5. `index.html` sirviéndose, instalable como PWA en el celular.
6. **El respaldo diario corriendo y una restauración ya probada** (§18). Esto va antes de cargar un solo dato real.

---

## 17. Seguridad

Implementa la sección 57 del documento general, **a la escala del proyecto**: pocos usuarios conocidos, cada uno viendo sus propios datos. No es un producto público.

### 17.1 Lo que está y se mantiene

Todo esto ya está implementado o es gratuito, así que no se discute:

| Requisito | Implementación |
|---|---|
| HTTPS en producción | Caddy redirige el 80 al 443 y renueva el certificado solo, más HSTS por cabecera |
| Contraseñas nunca en texto plano | Sólo el hash bcrypt, en `auth.users` |
| **Aislamiento entre cuentas** | `user_id` en toda consulta **y RLS como segunda barrera**. Es la defensa que importa acá |
| Sesiones seguras | JWT de vida corta (1 h) con refresh automático |
| Protección CSRF | No aplica: token en cabecera `Authorization`, no cookie de sesión |
| Validación en servidor | Pydantic en toda entrada, más `CHECK` en la base |
| Consultas parametrizadas | SQLAlchemy siempre; **prohibido** construir SQL por concatenación |
| Protección contra XSS | `esc()` obligatorio en todo dato que venga del servidor |
| Recuperación de contraseña segura | Enlace de un solo uso con vencimiento; nunca se revela si un email tiene cuenta |
| Registro sin enumerar usuarios | El alta y la recuperación responden igual exista o no el email |
| Secretos | `.env` del servidor, fuera del repositorio; la clave privada de firma montada como archivo; `.env.example` sin valores |
| Permisos mínimos en la base | `anon` y `authenticated` con sólo los permisos que la aplicación usa (cerrado en F02-T16) |
| Registro sin datos sensibles | Nunca se loguean tokens, contraseñas ni importes identificables |

La CSP se envía por cabecera desde el Caddyfile y es la razón por la que no hay JavaScript en línea en el HTML: todo va en módulos.

```text
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' https://fonts.googleapis.com;
  font-src https://fonts.gstatic.com;
  img-src 'self' data:;
  connect-src 'self';
  frame-ancestors 'none';
  base-uri 'self'
```

### 17.2 Lo que se decidió no hacer

Recortado en la revisión del 07/10/2026 (roadmap v2.0, F11-T04). No es que sea mala práctica: es trabajo de aplicación bancaria pública, y acá no compra nada.

| Descartado | Por qué |
|---|---|
| Límite general de peticiones (60/min, respuesta 429) | Los usuarios son conocidos y pocos. El login sí tiene su propio límite (§8.10), que es donde importa |
| Auditoría del historial de Git buscando secretos | `.env` estuvo ignorado desde el primer commit. Se verifica el estado actual, no el historial |
| Endurecer la CSP más allá de lo que ya hay | Ya no hay JavaScript en línea; la cabecera actual alcanza |
| Prueba de rendimiento con volumen | El volumen real son unos cientos de movimientos por año y por usuario |
| Auditoría formal de accesibilidad | Se respetan áreas táctiles de 44 px, `aria-label` y contraste al construir cada componente, sin una auditoría aparte |

**Cuándo se revisa esto:** si la aplicación se abre al registro de desconocidos, o si alguna vez guarda credenciales de terceros (el camino A de Mercado Pago, General §27). Hasta entonces, la combinación de RLS, JWT y validación en servidor es proporcionada.

### 17.3 Lo único que no se negocia

**Que una cuenta no pueda ver ni tocar los datos de otra.** Se verifica dos veces: en F02-T14 con los endpoints que existan entonces, y en F11-T04 con todos. RLS está activo en cada tabla de datos de usuario desde su migración, y eso no es opcional ni para una tabla nueva.

---

## 18. Respaldo y exportación

**Es el motivo por el que la aplicación se mudó a un servidor propio.** "La información financiera no debe depender de una única copia" (sección 58), y antes la copia dependía del plan de un tercero.

Tres niveles:

1. **Respaldo diario del servidor** — `scripts/respaldo.sh` hace `pg_dump -Fc` todas las noches, **verifica el archivo que acaba de escribir** (que abra y liste las tablas) y falla ruidosamente si no. Retención de 7 diarios, 4 semanales y 6 mensuales.
2. **Copia fuera del servidor** — el archivo del día se copia a un destino externo. Una copia que vive en el mismo disco que la base no es una copia: un disco que se pierde se lleva las dos.
3. **Exportación desde la aplicación** — `GET /api/export?format=json` devuelve el estado completo del usuario (perfil, meses, categorías, movimientos, totales consolidados, inversiones, historial laboral, preferencias) con versión de esquema. `format=csv` devuelve un ZIP con un archivo por tabla, para abrir en Excel. Es la copia que se lee sin herramientas.

**La restauración está probada, no sólo escrita.** `scripts/restaurar.sh` levanta el dump sobre una base vacía, y el procedimiento se ejecutó de verdad antes de cargar un solo dato real. Un respaldo que nunca se restauró no es un respaldo: es un archivo.

`POST /api/import` valida la versión de esquema, muestra una vista previa de qué se va a escribir y pide confirmación. Sólo escribe sobre una cuenta limpia.

---

## 19. Pruebas

Se testea **lo que da un número o protege un dato**. Nada más.

| Nivel | Herramienta | Qué cubre |
|---|---|---|
| Cálculo | pytest | `services/calc.py` y los servicios con funciones puras, con los casos borde de §7.1 |
| API | pytest + httpx | Cada endpoint: éxito, validación, 401, 404 y **aislamiento entre cuentas** |
| Manual | Vos, en el celular | Los criterios de aceptación de cada tarea del roadmap, en la URL de preview |

Reglas:

1. **Toda función de `calc.py` tiene su test antes del endpoint que la usa.** Es la capa donde un error se traduce directamente en una cifra equivocada en tu pantalla.
2. **Todo bug encontrado deja primero un test que falla**, y después se arregla.
3. **No hay exigencia de porcentaje de cobertura.** Un número de cobertura premia testear lo fácil.

Pruebas que no pueden faltar:

- El mes histórico devuelve `transactions: null` y la interfaz **no** muestra movimientos inventados.
- Alta de movimiento recalcula el mes **y todos los saldos posteriores**.
- Tasa de ahorro con ingresos en 0 devuelve `null`, no un error.
- Un usuario no puede leer ni escribir datos de otro, ni pasando un `id` ajeno.
- Una cuenta recién creada nace con su perfil y sus 21 categorías.
- Comprar una inversión no cambia el patrimonio neto.
- El importe negativo o cero lo rechaza la API, no sólo el formulario.

### 19.1 Lo que no se testea

Decidido en la revisión del 07/10/2026. Estos tests existían y consumían más mantenimiento que el código que vigilaban: cualquier ajuste visual los rompía, y ninguno detectaba un error de cálculo.

- **La estructura del HTML** y la presencia de componentes en la página.
- **Los tokens de CSS**, sus valores y el contraste calculado por expresiones regulares.
- **La configuración del despliegue** (`compose.yml`, el Caddyfile, variables de entorno).
- **El contenido de la documentación**: que un documento mencione lo que menciona.
- **Flujos de interfaz con Playwright en CI.**

Todo eso se verifica **mirando la pantalla en el celular**, que es el paso que ya cierra cada tarea del roadmap. Si una pantalla se ve bien y se usa bien, está bien.

**El criterio para decidir en el futuro:** si el test falla, ¿me enteré de algo que la pantalla no me hubiera mostrado? Si la respuesta es no, el test no se escribe.

---

## 20. Rendimiento

**Un solo objetivo medido:** `/api/dashboard` por debajo de **400 ms** en el percentil 95, medido desde la función desplegada. Se conserva porque es el número que justificó poner la base y la función en São Paulo (§20.1), y porque es el que se nota al abrir la aplicación.

Los presupuestos de KB de JavaScript y CSS y el puntaje de Lighthouse se quitaron como exigencias en la revisión del 07/10/2026: generaban trabajo de medición sin cambiar la experiencia. Las prácticas que los conseguían se mantienen igual, porque no cuestan nada.

Cómo se consigue: una sola llamada para todo el dashboard; caché por mes en memoria; `font-display: swap` con precarga; fondo con `background-attachment: fixed` y una única capa de ruido en SVG embebido en lugar de imágenes; `content-visibility: auto` en los paneles que están fuera de pantalla; estáticos con cache inmutable; pool de conexiones en la API, que ahora tiene sentido porque el proceso vive.

### 20.1 Región: el servidor está en US-east

El VPS está en **US-east**, a unos **130–160 ms** de Buenos Aires. Contabo no tiene región sudamericana, así que no hay alternativa dentro del proveedor. Es una desventaja frente al alojamiento anterior, que estaba en São Paulo, y está asumida a cambio del control sobre los datos y los respaldos.

**Por qué el objetivo de 400 ms se sigue cumpliendo**, y con margen: lo que antes se multiplicaba no era el viaje del teléfono sino el de la aplicación a la base, una vez por consulta. Ahora la API y Postgres están **en el mismo host, en la misma red de Docker**: cada consulta cuesta una fracción de milisegundo en vez de decenas.

```text
Antes (aplicación y base en São Paulo, separadas por la red):
  teléfono → servidor   ~40 ms    (una vez por petición)
  servidor → base       ~5 ms × 6 consultas = 30 ms
  total                 ~70 ms

Ahora (servidor propio en US-east, base en el mismo host):
  teléfono → servidor  ~150 ms    (una vez por petición)
  servidor → base      ~0,3 ms × 6 consultas ≈ 2 ms
  total                ~155 ms
```

Se nota al abrir la aplicación —unos 80 ms más que antes— y **no empeora al agregar consultas**, que es lo que hacía peligrosa la latencia en el modelo anterior.

Qué queda como regla:

1. **Mantener la respuesta única del dashboard** (§9.2): con cualquier latencia, una llamada es mejor que seis. Con un solo viaje caro, esto importa más que antes, no menos.
2. **La base nunca se separa de la API.** Si alguna vez se mueve a otro host, el cálculo de arriba se invierte y el objetivo deja de cumplirse.
3. **Medir el percentil 95 contra el servidor**, no contra la base local.
4. Un dominio propio con CDN delante de los estáticos reduciría la primera carga, pero no la de la API. Está anotado como mejora, no como pendiente.

---

## 21. Convenciones

### Código

- Python: `ruff` para formato y lint; `snake_case`; anotaciones de tipo obligatorias en servicios y repos; `Decimal` para dinero, **nunca `float`**.
- JavaScript: módulos ES; `camelCase`; `const` por defecto; **sin dependencias de terceros**.
- CSS: tokens primero, utilidades de Tailwind después, CSS propio sólo para los componentes de vidrio.
- Textos de interfaz en español rioplatense; identificadores de código en inglés.

### Git

```text
feat(F04-T03): alta de movimiento con recálculo del mes
fix(F06-T02): la línea de ahorro no se dibujaba con ahorro negativo
docs(F03): documentación de la fase 3
```

Una rama por tarea, nombrada `feat/F04-T03-descripcion-corta`. Integración a `main` sólo con la tarea aprobada.

### Documentación

Al cerrar cada fase se escribe `docs/FASE_XX_<nombre>.md` con qué se hizo en lenguaje natural, cuadros, ejemplos de uso y fragmentos del código real. Es una tarea del roadmap, no un extra.

---

## 22. Resumen de decisiones

| Tema | Decisión | Dónde se amplía |
|---|---|---|
| Framework backend | FastAPI sobre uvicorn, en contenedor | 3, 16.1 |
| Base de datos | Postgres 17 propio, un esquema (`public`); SQLite sólo para tests de cálculo | 4.1, 4.1.1, 6 |
| ORM | SQLAlchemy 2.0 + Alembic | 3, 16.4 |
| Autenticación | Propia; bcrypt para las contraseñas y JWT ES256 verificado con la clave pública del proyecto, no con secreto compartido | 8.1, 8.8 |
| Cuentas | Registro abierto, multiusuario desde el MVP. La confirmación por email se activa en F11-T03 | 8.2, 8.3 |
| Perfil y categorías iniciales | Trigger de Postgres sobre `auth.users`, no el backend | 8.4 |
| Envío de mails | No hay. La recuperación de contraseña se hace con un comando en el servidor | 8.5 |
| Aislamiento de datos | `user_id` en consultas + RLS | 6.5 |
| Frontend | Estático, una página, seis vistas, hash routing | 12.1 |
| Estilos | Tailwind v4 con los tokens del mockup | 13 |
| Gráficos | SVG propio, sin Chart.js | 4.3, 14 |
| Gráfico diario | Barras de ingreso y egreso + línea de ahorro acumulado con doble eje | 14.1 |
| Dinero | `numeric(14,2)` en base, `Decimal` en Python, string en JSON | 6.1, 12.5 |
| Dos tipos de mes | `transactions: null` para los consolidados | 6.6 |
| Offline | Diferido a después del MVP; hoy la PWA se instala y se abre, sin caché de lectura | 15.1 |
| Despliegue | Preview por rama, producción en `main` | 16.2, 16.3 |
| Pruebas | Cálculos y endpoints con pytest; la interfaz, a mano en el celular | 19 |
| Seguridad | RLS como defensa central; sin límite de peticiones ni auditorías formales | 17 |

---

## 23. Lo que queda fuera del MVP

Confirmado con la sección 4.2 del documento general. La arquitectura lo deja preparado, pero no se construye:

Presupuestos · gestión detallada de tarjetas · múltiples cuentas bancarias · conciliación bancaria · historial de operaciones de inversión · dólar y multimoneda · deudas, cuotas y préstamos · contabilidad formal · facturación · importación del Excel histórico · integración con Mercado Pago · escritura offline · restauración de respaldo desde la app · inicio de sesión con Google u otros proveedores · verificación en dos pasos · roles y permisos · cuentas compartidas entre usuarios.

**Diferido a «Después del MVP» en la revisión del 07/10/2026** (roadmap v2.0), sin salir del alcance del producto: cotizaciones automáticas de inversiones · alertas analíticas · historial salarial y métricas históricas · caché offline de lectura y atajos de la PWA. Son temas del documento general que la aplicación no necesita para servir todos los días.

**El alta de usuarios sí entra en el MVP** (§8.2): registro abierto, confirmación por email y recuperación de contraseña. Era un punto diferido en la primera versión de este documento y se incorporó por pedido expreso.

Qué queda preparado para que incorporarlos no obligue a rehacer nada: la tabla `liabilities` existe y ya se resta en el cálculo de patrimonio; `transactions` tiene `source` y `external_id` para la anti-duplicación de importaciones; el proveedor de cotizaciones es una interfaz con varias implementaciones; `app_settings` guarda preferencias arbitrarias en JSON; y el esquema es multiusuario desde el primer día.

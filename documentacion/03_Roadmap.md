# Roadmap de implementación — Epic Wallet 3.0

**Versión:** 3.0
**Fecha:** 22/11/2026
**Reemplaza:** el roadmap anterior, del 07/10/2026
**Documentos base:** `01_Documento_General.md` (qué) · `02_Documento_Tecnico.md` (cómo) · `04_Migracion_a_Contabo.md` (el traslado) · `mockups/01_Mockup_V1_Grafito_Clasico.html` (diseño aprobado)

---

## Por qué hay una versión 3.0

La aplicación está terminada y se usa todos los días. Lo que cambia es **dónde vive**.

Hasta ahora corría sobre servicios de terceros: el despliegue en uno, la base y la autenticación en otro. Funcionaba, pero el respaldo de años de contabilidad dependía del plan de otro y la base no era accesible de verdad. La 3.0 es **la misma aplicación en un servidor propio**, donde un respaldo es un archivo que se puede copiar, abrir, verificar y restaurar.

**No cambia nada de lo que ves.** Ni el modelo financiero, ni las seis pantallas, ni los seis indicadores, ni los cinco gráficos, ni el diseño «Vidrio Grafito». Cambia la infraestructura y la autenticación, que pasa a ser propia.

| | Antes | 3.0 |
|---|---|---|
| Servidor | plataforma serverless de terceros | **VPS propio, Docker Compose** |
| Base de datos | Postgres gestionado por un tercero | **Postgres 17 propio, volumen propio** |
| Autenticación | proveedor externo | **propia, en FastAPI, firma ES256** |
| Respaldos | el plan del proveedor | **`pg_dump` nuestro, verificado y restaurado** |
| Correo saliente | pendiente de contratar | **no hay, y no hace falta** |
| Pruebas de API | contra el servidor real del proveedor | **contra la base local** |

### La versión anterior es intocable

La versión anterior sigue encendida y **es el único sistema que hoy funciona**. Hasta que el corte de la Fase 19 esté aprobado, no se le escribe nada: ni un push a su repositorio, ni una migración, ni un cambio de variable. Leer está bien; escribir, no. Está anotado también en `CLAUDE.md`.

---

## Cómo se usa este documento

Es la guía de implementación. Ninguna tarea se ejecuta fuera de acá.

| Marca | Significado |
|---|---|
| `- [ ]` | Pendiente |
| `- [~]` | Implementada, esperando tu prueba |
| `- [x]` | Aprobada por vos |
| `- [!]` | Rechazada; abajo queda la nota de qué falló |

Una tarea pasa a `- [x]` sólo cuando vos lo decís.

### Reglas de ejecución

1. **Una tarea a la vez.** No se adelantan fases.
2. **Dentro de cada tarea: cálculo → backend → frontend.** Primero las funciones puras con sus tests, después el endpoint, después la interfaz.
3. **Se prueba en `https://13-140-36-93.sslip.io`, desde el celular.** Al terminar te digo qué probar y espero.
4. **Las tareas se escriben cortas:** qué hacer y cómo se verifica. Sin ensayos, sin relato de los errores encontrados. Lo que valga la pena recordar va a `docs/COMO_FUNCIONA.md`.
5. **Este documento es editable por vos.** Tu edición manda sobre lo que yo haya planificado.

### Política de pruebas

Se testea **lo que da un número o protege un dato**:

- toda función de `services/calc.py`, antes del endpoint que la usa;
- el recálculo del mes y la propagación a los saldos posteriores;
- los casos borde: ingresos en cero, mes vacío, mes histórico sin movimientos;
- que una cuenta no pueda leer ni escribir datos de otra;
- que el servidor rechace importes negativos o cero, no sólo el formulario.

**No se testea** la estructura del HTML, los tokens de CSS, el contraste calculado, la configuración del despliegue ni el contenido de la documentación. Eso se verifica mirando la pantalla en el celular. No hay exigencia de porcentaje de cobertura.

**Ninguna prueba toca un servidor de verdad.** Corren contra la base local.

### Tipo de tarea

`Infra` · `Cálculo` funciones puras y tests · `Backend` modelos, servicios y endpoints · `Frontend` interfaz · `QA` verificación.

---

## Resumen de fases

| Fase | Nombre | Estado |
|---|---|---|
| **0 – 13** | La aplicación: estilo, cuentas, meses, movimientos, indicadores, gráficos, histórico, patrimonio, inversiones, escritorio, vencimientos | **Construidas.** 9 tareas abiertas, ninguna bloquea el traslado |
| **14** | Repositorio y documentación propios | En curso |
| **15** | El servidor | Pendiente |
| **16** | El esquema sin proveedor externo | Pendiente |
| **17** | Autenticación propia | Pendiente |
| **18** | Respaldos | Pendiente |
| **19** | Los datos reales y el corte | Pendiente |

**El orden tiene un punto no negociable: la Fase 18 va antes que la 19.** No entran datos reales a un servidor que todavía no demostró que los puede devolver.

---

# LA APLICACIÓN QUE YA EXISTE

Fases 0 a 13, construidas entre octubre y noviembre de 2026. **El detalle tarea por tarea está en el historial de Git** (254 commits) y en `docs/COMO_FUNCIONA.md`, `docs/FASE_00_PUESTA_EN_MARCHA.md` y `docs/FASE_01_SISTEMA_DE_ESTILO.md`.

| Fase | Qué dejó funcionando |
|---|---|
| **0** | Repositorio, herramientas, Tailwind, Alembic, `/api/health`, URL pública y PWA instalable |
| **1** | Sistema «Vidrio Grafito»: tokens, las dos capas de vidrio, claro/oscuro, las seis vistas navegables |
| **2** | Cuentas: registro, entrar, salir, cambio de contraseña, y **aislamiento entre cuentas con RLS** |
| **3** | Meses reales y categorías administrables; las dos naturalezas de mes |
| **4** | Movimientos: alta, edición, baja y listado, con recálculo del mes |
| **5** | Los seis indicadores del tablero, con datos reales, en una sola llamada |
| **6** | Los cinco gráficos, en SVG propio |
| **7** | Desglose ordenable y detalle de categoría |
| **8** | Histórico consolidado y carga del Excel |
| **9** | Ahorro acumulado y patrimonio neto |
| **10** | Inversiones: cartera, compra, venta y rendimientos |
| **11** | Cierre del MVP: configuración, exportación y respaldo, revisión de seguridad |
| **12** | Apronte de escritorio y navegación por gestos en el celular |
| **13** | Comparación de un ítem mes a mes, y vencimientos con alertas |

## Lo que quedó abierto de esas fases

Ninguna bloquea el traslado. Se retoman cuando la 3.0 esté en pie.

### Implementadas, esperando que las pruebes

- [ ] **F12-T03 · El resto, guiado por lo que vayas encontrando**
  **Tipo:** Frontend
  **Hacer:** queda abierta a propósito. A medida que uses la aplicación desde la PC y encuentres algo —una tarjeta fuera de lugar, un gráfico pobre, algo demasiado grande o chico—, se agrega acá como entrada concreta, se corrige y se tacha. Sin lista inventada de antemano.
  **Aceptación:** cada entrada se marca `[x]` cuando confirmás que ya se ve bien.

- [ ] **F12-T05 · Cuatro correcciones de uso: scroll, color, orden y conmutadores**
  **Tipo:** Frontend · **Ref:** `.claude/skills/epic-wallet-ui/SKILL.md` §1, §8, §9
  **Hacer:** scroll vertical sobre gráficos y tablas; margen del gráfico contra el borde de la tarjeta; paleta con más saturación en `tokens.css` sin tocar componentes; «Variación» fuera del orden de gastos por categoría; conmutadores con un solo dueño (`components/switch.js`) y pastilla deslizante; el círculo del cambio de tema sin trabarse en el primer cuadro.
  **Aceptación:** · deslizar de arriba abajo sobre el gráfico diario y sobre la tabla de Cartera scrollea la página, y de lado a lado sigue moviendo el gráfico o la tabla · al final del scroll del gráfico queda margen contra el borde · los colores se ven más vivos en los dos temas · en «Gastos por categoría» quedan dos órdenes · ningún conmutador queda con dos marcadas ni con ninguna · el círculo del cambio de tema sale parejo desde el primer cuadro.
  `npm test`: 630/630.

- [ ] **F12-T06 · Dos animaciones: el interruptor y la fila que entra**
  **Tipo:** Frontend · **Ref:** `.claude/skills/epic-wallet-ui/SKILL.md` §8
  **Hacer:** el interruptor se estira mientras se mantiene apretado y el color del surco se funde (el color pasa a una capa `::after`, porque un degradado no se interpola); la fila del movimiento recién cargado entra desde arriba, empuja a la lista y deja un halo que se apaga.
  **Aceptación:** · apretar un interruptor sin soltar estira el pulgar, y al soltarlo el color se funde junto con el movimiento · cargar un movimiento estando en Movimientos lo muestra entrando en la lista · con un filtro que lo deja afuera, no pasa nada raro.
  `npm test`: 633/633.

- [ ] **F13-T01 · El tamaño de la letra de los gráficos, parejo en todos**
  **Tipo:** Frontend · **Ref:** `.claude/skills/epic-wallet-ui/SKILL.md` §9
  **Hacer:** un `font-size` dentro de un `<svg>` está en unidades del `viewBox`, no en píxeles de pantalla. `etiquetaSvg` publica `--escala-grafico` y `.axis-v`/`.axis-t` multiplican su token por esa variable, así el número del token es el tamaño real en el teléfono. Tokens en 10,5 px (valores) y 9,75 px (meses y días).
  **Aceptación:** · la letra de los ejes se lee en el celular en los cuatro gráficos · es del mismo tamaño en todos · no cambia el tamaño del dibujo.

- [ ] **F13-T02 · Comparación por ítem, dentro de Movimientos**
  **Tipo:** Cálculo → Backend → Frontend · **Ref:** General §14 · Técnico §9.1
  **Hacer:** tarjeta **plegada** en Movimientos que al prenderla muestra un ítem mes a mes, con rango de 3, 6, 12 meses o todo. `services/calc.py::resumen_de_comparacion` (pura): promedio, máximo, mínimo, último cerrado, diferencia y variación contra el mes anterior; un mes sin el ítem es `None`, no cero; el mes en curso queda afuera del promedio. `GET /api/categories/{id}/history?months=N` sale de `monthly_category_totals`.
  **Aceptación:** · plegada no pide nada · prendida muestra gráfico, seis cifras y la lista mes a mes · el rango cambia la cantidad de meses · un mes sin el ítem dice «sin dato» · la pantalla dice qué dos meses compara.

- [ ] **F13-T03 · Vencimientos: sección nueva, entre Historial y Cartera**
  **Tipo:** Cálculo → Base → Backend → Frontend · **Ref:** General §29 · Técnico §6.2, §9.1
  **Hacer:** las categorías de egreso activas con un interruptor cada una; prendido, día de vencimiento y cuántos días antes avisar. `services/vencimientos.py` (puro): hasta el aviso **atención**, a un día o menos **crítico**; el 31 en un mes de 30 vence el 30. Tabla `category_dues` con RLS forzado, que guarda la configuración aunque esté apagado. `GET /api/dues` y `PUT /api/dues/{category_id}`. Las alertas viajan dentro de `GET /api/dashboard` (`dues_alerts`): el tablero sigue siendo una sola llamada. Un movimiento del ítem en el mes lo da por pagado y deja de avisar. La barra inferior pasa a seis posiciones.
  **Aceptación:** · la lista trae todos los ítems de egreso, apagados · prender uno y elegir día y aviso sobrevive a recargar · a 3 y 2 días amarilla, a 1 día roja · cargar el movimiento del mes apaga la alerta sola · la campanita cuenta lo mismo que la hoja · ninguna cuenta ve los vencimientos de otra.
  *Pendiente de tu decisión, no bloquea:* cómo se llama la sección y si la barra de seis posiciones se ve bien en tu teléfono.

---

# FASE 14 — Repositorio y documentación propios

**Objetivo:** que el proyecto no nombre ni dependa de ningún proveedor externo, y que el roadmap vuelva a ser una lista de tareas ejecutable.

**Al cerrar esta fase:** la documentación describe el sistema que vamos a construir, no el que dejamos atrás, y las pruebas corren sin una sola credencial de terceros.

> Los dos primeros commits de esta fase se etiquetaron `F00-T01` y `F00-T02` antes de fijar la numeración. Son `109efc7` y `2fede55`; corresponden a F14-T01 y F14-T02.

- [x] **F14-T01 · Plan de traslado**
  **Tipo:** Infra
  **Hacer:** `04_Migracion_a_Contabo.md` con el servidor, las tres decisiones de arquitectura, las fases y qué se baja de la versión anterior.
  **Aceptación:** · el documento existe y está en el repositorio nuevo.

- [x] **F14-T02 · `CLAUDE.md` pasa a la 3.0**
  **Tipo:** Infra
  **Hacer:** stack nuevo, la regla de que la versión anterior es intocable, Jarvis conviviendo en el mismo servidor, comandos del servidor.
  **Aceptación:** · ninguna mención a los proveedores anteriores · la regla de intocable está escrita.

- [x] **F14-T03 · Este roadmap**
  **Tipo:** Infra
  **Hacer:** fases 0 a 13 resumidas, las 9 tareas abiertas preservadas, las fases 14 a 19 detalladas, cero referencias a proveedores externos.
  **Aceptación:** · `./scripts/sin_proveedores.sh --docs` pasa · las 9 tareas abiertas siguen estando con sus criterios de aceptación.

- [x] **F14-T04 · El Documento Técnico**
  **Tipo:** Infra
  **Hacer:** reescribir §4 (base de datos), §8 (autenticación), §11 (variables de entorno), §16 (despliegue), §17 (seguridad) y §18 (respaldo) para el servidor propio. El resto —modelo de datos, API, cálculo, estilo— no se toca.
  **Aceptación:** · `./scripts/sin_proveedores.sh --docs` pasa · un lector que no estuvo en estas conversaciones puede levantar el proyecto siguiéndolo.

- [x] **F14-T05 · El README**
  **Tipo:** Infra
  **Hacer:** puesta en marcha local y en el servidor, sin proveedores externos.
  **Aceptación:** · `./scripts/sin_proveedores.sh --docs` pasa · los comandos del README funcionan tal como están escritos.

- [x] **F14-T06 · Sacar el proveedor externo del frontend y de la configuración**
  **Tipo:** Infra
  **Hacer:** quitar del proyecto todo lo que lista `04_Migracion_a_Contabo.md` en «Lo que se va»: el paquete de autenticación heredado y su copia en `web/src/js/vendor/`, sus variables de entorno en `.env.example` y en `core/config.py`, y su dominio en la CSP. `web/public/config.js` pasa a llevar sólo la URL de la API.
  **Aceptación:** · `npm install` no baja nada del proveedor anterior · ningún archivo versionado lo nombra · la aplicación sigue levantando en local.
  *Va después de F17-T03, que es la que reemplaza `auth.js`. Antes de eso, sacarlo deja la aplicación sin forma de entrar.*
  ***La hizo F17-T06**, que barrió los 84 archivos del repositorio entero. Los tres criterios se comprobaron: la dependencia no está en `package.json` ni en `package-lock.json`, el verificador pasa sobre todo lo versionado, y la aplicación levanta (`/api/health` en `ok`). La CSP que sirve el borde es `connect-src 'self'` y no nombra ningún dominio ajeno.*

---

# FASE 15 — El servidor

**Objetivo:** que exista una dirección con candado, servida desde el VPS propio, con Epic Wallet y Jarvis conviviendo sin pisarse.

**Al cerrar esta fase:** abrís `https://13-140-36-93.sslip.io` desde el celular y responde la aplicación, con certificado válido; Jarvis sigue levantando como antes.

- [x] **F15-T01 · Base del servidor**
  **Tipo:** Infra
  **Hacer:** 2 GB de swap con `vm.swappiness=10`; clave de despliegue **generada dentro del servidor**, para que la privada no viaje, y su pública cargada en el repositorio.
  **Aceptación:** · `swapon --show` muestra 2 GB y sobrevive a un reinicio · el servidor puede clonar el repositorio solo, sin credenciales de nadie.
  *El firewall y las actualizaciones automáticas ya estaban bien configurados: `ufw` declara 22, 80 y 443 en IPv4 e IPv6, con política `deny` de entrada, y `unattended-upgrades` está activo con los orígenes de seguridad. No hizo falta tocarlos.*

- [x] **F15-T02 · Proxy de borde compartido**
  **Tipo:** Infra
  **Hacer:** sacar Caddy del compose de Jarvis y dejarlo en `/opt/edge/` como único dueño de 80 y 443, con un archivo de sitio por proyecto en `conf.d/`. Red externa compartida; Jarvis y Epic Wallet se conectan a ella. El compose anterior de Jarvis se conserva para poder volver atrás.
  **Aceptación:** · Jarvis responde igual que antes · `https://13-140-36-93.sslip.io` da candado válido · reiniciar un proyecto no afecta al otro.
  *Hecho. El certificado lo emitió Let's Encrypt para `13-140-36-93.sslip.io`, vence el 21/02/2027 y lo renueva Caddy solo. Jarvis no tiene dominio: queda como sitio por defecto del puerto 80, así que la IP pelada responde igual que antes y el kiosco de la Raspberry no se entera. En la red compartida la API de Jarvis se alcanza como `jarvis-api`, porque `api` a secas chocaría con la de Epic Wallet.*
  *Corrección sobre el supuesto de partida: Jarvis **no** estaba parado, estaba corriendo. El cambio se hizo igual, con respaldo previo en `/opt/jarvis/docker-compose.yml.antes-del-borde` y unos segundos de corte.*
  *Los archivos de `/opt/edge/` no se versionan acá: son compartidos con Jarvis y este repositorio es sólo de Epic Wallet. **F18 los incluye en el respaldo.***

- [x] **F15-T03 · El compose de Epic Wallet**
  **Tipo:** Infra
  **Hacer:** `/opt/epic-wallet/` con Postgres 17 y la API, red propia, volumen propio, **sin publicar ningún puerto al exterior** —sólo el proxy habla con ellos—. Los estáticos de `web/` los sirve Caddy. Bases separadas de Jarvis, que sigue con su Postgres 16.
  **Aceptación:** · `docker compose ps` muestra los dos contenedores sanos · `/api/health` responde a través del proxy · `ss -tlnp` no muestra Postgres escuchando afuera.
  *Hecho. Son tres servicios, no dos: `db` y `api` quedan corriendo y `web` compila el frontend al volumen que sirve el borde y termina. El `.env` del servidor fija `COMPOSE_FILE`, así que allá también alcanza con `docker compose up -d`. La contraseña de Postgres se generó dentro del servidor.*
  *La base está **vacía**: las tablas las crea F16-T02. Hasta entonces `/api/health` responde pero cualquier endpoint de datos falla.*

- [x] **F15-T04 · Adaptar el backend a un servidor que no es serverless**
  **Tipo:** Backend
  **Hacer:** en `core/db.py`, sacar `NullPool` y `prepare_threshold=None` —existían por un pooler en modo transacción que ya no está— y poner un pool normal; corregir el aviso de `validar_coherencia` que exige el puerto del pooler. Borrar los tres archivos de despliegue heredados que lista `04_Migracion_a_Contabo.md`; el arranque pasa a ser `uvicorn` dentro del contenedor.
  **Aceptación:** · la API levanta en el servidor · `pytest` en verde · ningún archivo de despliegue del proveedor anterior queda en el repositorio.
  *Entra en el mismo commit que F15-T03, para que el proyecto nunca quede sin forma de desplegarse.*
  *Hecho. Dos cosas que no estaban en el enunciado y hacían falta: `uvicorn` pasa a dependencia de producción —lo ponía la plataforma— y la URL del proveedor de autenticación deja de ser una variable obligatoria, para que el servidor arranque sin ella. Las cabeceras y la CSP que vivían en el archivo de despliegue de la plataforma anterior se mudaron al proxy de borde; `connect-src` ya no nombra ningún dominio ajeno.*
  *`pytest` se corrió **sin `tests/api/`**, que todavía pega contra el servidor real: 237 unitarios y 670 de frontend en verde. La suite completa vuelve a ser exigible en F16-T03.*

---

# FASE 16 — El esquema sin proveedor externo

**Objetivo:** que las 12 migraciones y las 9 políticas RLS corran sobre Postgres puro **sin modificarlas**.

**Al cerrar esta fase:** `alembic upgrade head` sobre una base vacía deja el esquema completo, con RLS activo, y las pruebas de aislamiento pasan.

- [x] **F16-T01 · El shim de `auth`**
  **Tipo:** Base · **Ref:** `04_Migracion_a_Contabo.md`
  **Hacer:** migración nueva que crea el esquema `auth`, los roles `anon` y `authenticated`, la función `auth.uid()` —lee el mismo GUC `request.jwt.claims` que ya setea `core/db.py`— y la tabla `auth.users` (`id`, `email`, `encrypted_password`, `email_confirmed_at`, `created_at`). El rol de la aplicación recibe `grant authenticated`, sin lo cual `set local role` falla.
  **Aceptación:** · `select auth.uid()` devuelve el uuid de los claims y `null` sin claims · `profiles.id` sigue con su clave foránea en cascada · el trigger que crea el perfil y las 21 categorías sigue disparando al dar de alta un usuario.
  *Hecho, y verificado en el servidor: sin claims devuelve nulo, con claims devuelve el uuid, y dar de alta dos cuentas creó dos perfiles y 21 categorías cada una. Las cuentas de prueba se borraron.*
  *Va dentro de la revisión inicial, que estaba vacía, y no en una migración nueva: la segunda migración de la cadena ya declara una clave foránea contra `auth.users`, y una migración nueva sólo puede ir al final.*
  *Dos cosas que el enunciado no tenía: `auth.users` necesita además `raw_user_meta_data` —el trigger la lee para el nombre a mostrar, y sin ella la cuenta nace sin perfil— y la tabla queda con RLS activo y forzado, para que una cuenta no pueda leer la fila ni el hash de otra.*

- [x] **F16-T02 · Las 12 migraciones, limpias, sobre Postgres puro**
  **Tipo:** Base
  **Hacer:** correr la cadena completa sobre una base vacía y ajustar lo mínimo que falle. Las políticas RLS **no se tocan**: si alguna hay que cambiarla, es señal de que el shim está mal.
  **Aceptación:** · `alembic upgrade head` y `downgrade base` corren sin error sobre una base vacía · las 9 tablas quedan con RLS activo y forzado · ninguna política fue modificada.
  *Hecho. La cadena completa sube, baja y vuelve a subir. Las 9 tablas quedan con RLS activo y forzado, y hay 9 políticas. Ninguna política se tocó.*
  *Lo único que hubo que ajustar: dos migraciones tenían `postgres` escrito a mano —el nombre del rol del proveedor anterior— y fallaban con «role postgres does not exist». Ahora leen `current_user`, que es exactamente el rol cuyos privilegios por defecto hay que cambiar.*

- [x] **F16-T03 · Las pruebas, contra la base local**
  *Se corre después de F17-T01, y no antes: estas pruebas necesitan firmar sus propios tokens, y hasta esa tarea el backend sólo aceptaba los de un emisor ajeno. La dependencia no estaba vista cuando se escribió el orden.*
  **Tipo:** QA
  **Hacer:** `tests/api/` hoy pega contra el servidor real del proveedor con su clave de servicio. Pasa a levantar su base de prueba local y a firmar sus propios tokens. Se borra `tests/api/ayudas_auth.py`, que existía sólo para confirmar correos por la API de administración ajena.
  **Aceptación:** · `pytest` completo en verde **sin una sola credencial externa en el entorno** · ninguna prueba abre una conexión a internet.
  *Hecho. **491 pruebas de Python en verde** contra una base local, sin una credencial externa en el entorno: `conftest.py` las vacía antes de que se importe la aplicación, así ninguna prueba puede alcanzar nada aunque queden puestas en un `.env`. La única salida HTTP que queda es en proceso, contra la propia aplicación.*
  *Las cuentas se insertan en `auth.users` y el trigger de la base les crea el perfil y las 21 categorías, igual que a una cuenta de verdad. Los tokens los firma la batería con un par ES256 que vive en memoria.*
  *1.100 líneas repetidas en 17 archivos pasan a `tests/api/entorno.py`. Se borró `tests/api/ayudas_auth.py`.*
  *`TEST_DATABASE_URL` no cae por defecto en `DATABASE_URL` a propósito, y las pruebas se niegan a correr si el nombre de la base no dice que es de pruebas.*
  *Y algo que no estaba en el enunciado: **las once pruebas de aislamiento entre cuentas se estaban salteando en silencio.** La corrección de urgencia del accidente del 2026-11-10 las dejó buscando cuentas descartables ya existentes, y casi nunca las encontraba. Ahora las crean ellas: corren siempre.*

---

# FASE 17 — Autenticación propia

**Objetivo:** entrar, salir, renovar la sesión y cambiar la contraseña, sin proveedor y sin correo.

**Al cerrar esta fase:** te registrás y entrás desde el celular, la sesión se renueva sola sin que lo notes, y una segunda cuenta no ve ni un dato de la primera.

- [x] **F17-T01 · Las claves y la verificación**
  **Tipo:** Backend · **Ref:** Técnico §8
  **Hacer:** par de claves ES256 (P-256) del proyecto; la privada firma, la pública verifica. `core/security.py` deja de usar el cliente JWKS y verifica con la pública del entorno: sin viaje de red y sin depender de que un servicio ajeno responda. Los claims no cambian (`sub`, `aud: authenticated`, `exp`, `email`), así que el resto del backend no se toca.
  **Aceptación:** · un token nuestro se verifica · uno firmado con otra clave se rechaza · uno vencido da «la sesión expiró» · ningún endpoint privado quedó accesible sin token.
  *Se conserva la firma asimétrica por el mismo motivo de siempre: con un secreto compartido, quien lo tenga puede fabricar sesiones. Acá sólo se puede verificar.*
  *Hecho, y probado contra el servidor: un token firmado con la clave del proyecto pasa la puerta; uno firmado con otra clave, uno vencido, uno con basura adentro y uno ausente dan 401, y los mensajes distinguen «la sesión expiró» de «la sesión no es válida».*
  *El par se generó **dentro del servidor** y la privada no salió de ahí. `scripts/generar_claves.py` queda para rehacerlo; imprime en pantalla y no escribe archivos, para que nadie termine con una copia olvidada en su disco.*
  *Se adelanta a F16-T03, que no podía terminarse antes: las pruebas de API necesitan firmar sus propios tokens, y hasta acá el backend sólo aceptaba los de un emisor ajeno.*

- [x] **F17-T02 · Los endpoints de sesión**
  **Tipo:** Backend
  **Hacer:** `signup`, `login`, `refresh`, `logout` y `cambiar-clave` bajo `/api/auth`. Contraseñas con bcrypt —el mismo algoritmo que usa el proveedor anterior, que es lo que permite importar los hashes sin que nadie resetee nada—. Token de acceso de una hora; token de renovación rotatorio, guardado hasheado, de 30 días. Los mensajes de error **no distinguen** «no existe el usuario» de «contraseña equivocada», ni acá ni en el registro.
  **Aceptación:** · se crea una cuenta y entra · la cuenta nueva aparece con su tablero vacío y sus 21 categorías · un token de renovación usado dos veces se rechaza · ningún mensaje revela si un email tiene cuenta.
  *`/api/auth/signup`, `/login`, `/refresh`, `/logout` y `PUT /password`. Las cuatro primeras son públicas y están declaradas como tales en `test_api_protegida.py`; la quinta pide sesión.*
  *Tabla `refresh_tokens` con **familia**: todos los tokens que descienden de un login la comparten. Si uno ya usado reaparece se corta la cadena entera —no se puede saber si lo presenta el legítimo o quien lo copió—, y las otras sesiones de la cuenta no se tocan. 29 pruebas nuevas.*
  *Ni el texto ni el reloj delatan qué correos tienen cuenta: contra un email desconocido se verifica igual contra un hash de relleno.*
  *bcrypt a propósito, que es lo que usaba el proveedor anterior: sus hashes entran tal cual en F19 y nadie restablece su contraseña.*
  *Un error que encontró la prueba y no el diseño: el 401 por token repetido revertía la transacción y deshacía la revocación. La respuesta decía 401 y la sesión robada seguía viva.*

- [x] **F17-T03 · `auth.js` nuevo**
  **Tipo:** Frontend · **Ref:** Técnico §8.7
  **Hacer:** reemplazar la librería del proveedor conservando **la misma superficie pública del módulo**, para que las otras 50 pantallas no se enteren. Las tres cosas que daba la librería y hay que sostener: renovación silenciosa antes del vencimiento, **una sola renovación en vuelo** aunque lleguen dos peticiones juntas, y sincronía entre pestañas por el evento `storage`.
  **Aceptación:** · entrar, salir y recargar funcionan en el celular · dejar la aplicación dormida una hora y volver no pide entrar de nuevo · cerrar sesión en una pestaña cierra la otra · dos peticiones simultáneas con el token vencido disparan una sola renovación.
  *Misma superficie pública del módulo: cambiaron **dos** archivos de pantalla, no cincuenta. 35 pruebas, 676 JS en verde.*
  *La renovación única en vuelo dejó de ser una optimización y pasó a ser obligatoria: con tokens rotatorios, dos renovaciones simultáneas hacen que el servidor tome la segunda por robada y corte la sesión. Abrir dos pantallas a la vez cerraría la sesión.*
  *Sin red **no** se borra la sesión: el token de renovación sigue siendo bueno y lo único que pasó es que alguien entró al subte.*
  *El cambio de contraseña pasa a ser una sola petición. Antes la pantalla verificaba la actual con `entrar()` y después cambiaba, con un instante en el medio; ahora las dos van juntas y verifica el servidor.*
  *Se fueron del repositorio la dependencia del proveedor, su copia en `web/src/js/vendor/` y el script que la traía.*
  *Queda para T04 el camino del enlace de recuperación (`verificarEnlace`), y para T06 `scripts/generar-config.mjs`, que todavía escribe un `config.js` con la URL del proveedor aunque nadie lo lea.*

- [x] **F17-T04 · Recuperar la contraseña sin correo**
  **Tipo:** Backend · **Ref:** General §48.1
  **Hacer:** `python -m app.cli recuperar <email>` imprime un link de un solo uso, válido 30 minutos, contra la pantalla `#/nueva-clave` **que ya existe**. El link se entrega a mano. El token se guarda hasheado y se quema al usarse.
  **Aceptación:** · el link abre la pantalla y permite poner una contraseña nueva · usarlo dos veces falla · a los 31 minutos falla · cambiar la contraseña desde Ajustes sigue pidiendo la actual.
  *`api/app/cli.py` + tabla `password_resets` + `POST /api/auth/reset`. El enlace lleva la misma forma que ya leía `enlace-correo.js`, así que esa pantalla no se tocó.*
  ***El enlace no se canjea por una sesión.** El camino obvio —enlace → sesión abierta → cambiar la clave— es peor: quien lo intercepte entra a la cuenta aunque no cambie nada. Acá sirve para una sola cosa y se gasta en esa misma petición.*
  *Se quema **antes** de tocar la contraseña: un enlace que sobrevive a un intento fallido es una llave que se puede volver a probar.*
  *Pedir uno nuevo invalida el anterior. Si no, pedir tres veces porque el primero no llegó dejaría tres llaves vivas en vez de reemplazarlas.*
  *Los tres rechazos —no existe, ya se usó, venció— son indistinguibles.*
  *Probado en el servidor de punta a punta: el comando imprime el enlace, canjearlo cambia la clave y abre sesión, usarlo dos veces da 401, la contraseña vieja deja de servir, y un correo inexistente avisa en la consola (ahí sí: el único que puede correr esto es Gustavo, y necesita saber si se equivocó al escribirlo).*

- [x] **F17-T05 · Aislamiento entre cuentas, de punta a punta**
  **Tipo:** QA · **Ref:** Técnico §6.5
  **Hacer:** rehacer el barrido completo contra la autenticación nueva: con el token de una cuenta, intentar leer y escribir por identificador directo los recursos de la otra, en todos los endpoints.
  **Aceptación:** · ningún recurso ajeno es accesible, ni pasando su `id` a mano · RLS bloquea incluso salteando el filtro del endpoint · la prueba queda automatizada.
  *`tests/api/test_aislamiento_f17.py`, 16 pruebas. Las cuentas se crean con `POST /api/auth/signup` y el token es **el que emitió el servidor**, no uno que la batería se firma a sí misma: eso es lo que F11-T04 no podía probar.*
  *La lista de endpoints con id **se importa** de F11-T04 en vez de copiarse. Allá hay una prueba que la compara contra el esquema OpenAPI; una lista duplicada se queda vieja en silencio.*
  *Lo que no existía antes: renovar, salir, cambiar la contraseña y canjear un enlace, cruzados entre dos cuentas. Cerrar la sesión de una no deja afuera a la otra, y un enlace de recuperación sirve para una sola cuenta.*
  *RLS se comprueba **sin pasar por la API**: con el rol y los claims de B, se intenta leer y escribir las filas de A en las once tablas de datos de usuario, descubiertas de `information_schema` —una tabla nueva entra sola— y exigiendo `enable`, `force` y política en todas.*
  *Se verificó rompiendo a propósito la política de `categories` en la base de pruebas: las tres pruebas de RLS fallaron, y con la política restaurada volvieron al verde. Un aislamiento en verde que no sabe fallar no prueba nada.*
  *Lo encontró esa rotura a propósito: el intento era un `delete` y lo frenaba una clave foránea, no RLS, y el código tomaba cualquier error por «bloqueado». Ahora el intento es un `update` que no cambia nada y sólo «permiso denegado» cuenta como bloqueo.*
  *`scripts/pruebas_en_el_servidor.sh` corre la batería en Contabo contra `epic_wallet_test`, montando una copia del repositorio sin el `.env`: desde esa corrida no hay forma de alcanzar la base real.*

- [x] **F17-T06 · La reja final**
  **Tipo:** QA
  **Hacer:** correr `./scripts/sin_proveedores.sh` **sin argumentos**, sobre todo el repositorio, y limpiar lo que quede: variables, dependencias, comentarios y URLs de prueba. Hasta acá sólo se exigía `--docs`, porque el código todavía dependía del proveedor anterior.
  **Aceptación:** · el verificador pasa sobre todo el repositorio · `pytest` y `npm test` en verde.
  *Pasa. Eran **84 archivos**. La batería del servidor queda en **569 en verde, 3 salteadas y ninguna roja** —el rojo conocido de `git` desapareció—, y 681 en JS.*
  *Se fue el código que ya no hacía nada: los cuatro ajustes del proveedor en `config.py` con su validador, su bloque en el `.env.example`, sus dos variables en el compose, su carpeta en el gitignore, la dependencia que seguía viva en `package-lock.json` y `scripts/verificar_auth.py`, que verificaba la configuración del proveedor contra su proyecto real.*
  *Y el que podía esconder una falla: las tres ramas «rate limit» de `test_alta_de_cuenta.py`. `_registrar` es local y no puede devolver eso, así que lo único que podían hacer era saltearse una prueba que falló de verdad.*
  *`load_history.py` entra por `POST /api/auth/login` en vez del endpoint del proveedor: es lo que va a usar la importación de F19.*
  ***`test_secretos_fuera_del_frontend.py` cuida ahora `JWT_PRIVATE_KEY` y `DATABASE_URL`.*** Cuidaba la clave de servicio del proveedor, que ya no existe. Lo que hay hoy es peor si se escapa: con la privada se fabrica la sesión de cualquier usuario, sin contraseña y sin dejar rastro. Busca por **forma** (el encabezado de un PEM, una cadena de conexión) y por **valor**, porque la forma no cubre una contraseña de base.*
  *Un error real que destapó esa reescritura: `_del_env` buscaba el valor con `\s*` alrededor del `=`, y `\s` incluye el salto de línea. Con la variable vacía leía la línea de abajo, así que la prueba comparaba contra otro secreto.*
  *`test_security.py` exige que la firma siga siendo **asimétrica** —ni `HS256` ni un secreto compartido en `security.py`— en lugar de nombrar una variable borrada. Es la misma protección, dicha de una forma que no caduca.*
  *En las cinco migraciones aplicadas se reescribió **sólo la prosa**: el diff no toca una línea de DDL.*
  *El modelo que declaraba `auth.users` se llamaba por el nombre del proveedor; ahora es `models/auth_users.py`, porque esa tabla es nuestra desde F16-T01.*
  *Queda una cosa a propósito, anotada en `web/src/js/enlace-correo.js`: el camino del enlace con `?code=` está **inerte**, porque la librería que hacía ese canje se fue en F17-T03. No se borró porque no abre nada —sin token no se cambia ninguna contraseña— y borrarlo es una limpieza de pantalla, no de esta tarea.*
  *Cuando esta pasa, el script y `04_Migracion_a_Contabo.md` —las dos únicas excepciones— ya no tienen razón de existir. Se borran en F19.*

---

# FASE 18 — Respaldos y resguardo de los datos

**Objetivo:** el motivo por el que existe la 3.0. Que exista un archivo con tus datos, fuera del servidor, y que **ya se haya probado que se puede restaurar**.

**Al cerrar esta fase:** hay copias diarias verificadas, una copia fuera del servidor, una restauración hecha de verdad, y la base guarda sola la versión anterior de cada fila que se toca.

**T05, T06 y T07 se pospusieron el 2026-11-23** con este motivo: «protegen datos que todavía no están en el servidor».

**Ese motivo se venció el 2026-11-25**, cuando entraron las tres cuentas con sus 405 filas. Ahora hay datos que perder, así que las tres vuelven a la mesa. La más urgente es **T06**: un respaldo que falla en silencio es peor que ninguno, y hoy no hay forma de enterarse.

**Se adelanta sobre F17 por decisión de Gustavo (2026-11-23).** Es independiente del login propio, y así la red existe **antes** de que haya algo que perder y antes de las dos etapas donde se puede romper algo: la autenticación nueva (F17) y la importación (F19).

**El agujero que la justifica:** `scripts/respaldo.sh` y `scripts/restaurar.sh` se citan en `CLAUDE.md` y en el README —incluido el procedimiento de migración, «respaldo primero»— y **nunca se escribieron**. Hoy ese primer paso fallaría.

- [x] **F18-T01 · El respaldo diario, verificado**
  **Tipo:** Infra
  **Hacer:** `scripts/respaldo.sh` con `pg_dump -Fc`, nocturno, retención de 7 diarios, 4 semanales y 6 mensuales. El script **abre el archivo que acaba de escribir y lista sus tablas**, y falla ruidosamente si no abre. Un dump que nadie leyó no es un respaldo.
  **Aceptación:** · a la mañana siguiente hay un archivo nuevo · un dump corrupto a propósito hace fallar el script · la retención borra lo viejo y no lo que hay que guardar.
  *Implementado y probado en el servidor. Seis casos de archivo malo detectados: truncado, basura aleatoria, vacío, inexistente, fuera de la carpeta, y el bueno pasa. Exigiéndole 999 tablas, el script **borra el respaldo que no sirve** y no toca `ultimo.json`. Con 12 archivos en `diario/`, la retención deja 7 y borra los 6 más viejos. El respaldo de tarea (`--etiqueta`) sobrevive a tres corridas diarias.*
  *Corre por `cron` a las 3:15 **hora de Argentina** —declarada con `CRON_TZ`, porque el servidor está en hora europea—, con registro en `/var/log/epic-wallet-respaldo.log`.*
  *Dos errores que encontró la prueba y no el diseño: `--solo-verificar` con una ruta relativa decía que el archivo estaba corrupto cuando lo que estaba mal era la ruta, y `docker compose exec -T` se come la entrada estándar, así que el script invocado por una tubería se comía sus propias líneas sin dar error.*
  *Aprobado por Gustavo el 2026-11-23: corrió el respaldo, vio las 11 tablas verificadas y comprobó que un archivo truncado da FALLA.*
  *Falta la copia fuera del servidor: eso es F18-T02.*

- [x] **F18-T02 · La copia en la PC de Gustavo**
  **Tipo:** Infra
  **Hacer:** una tarea programada de Windows que se trae el respaldo del día. **La PC tira del servidor**, no al revés: así el servidor no necesita ninguna credencial de la PC, y si la PC estuvo apagada, al volver se trae todos los pendientes. Una copia en el mismo disco que la base no es una copia.
  **Aceptación:** · el archivo del día aparece en la PC sin que nadie haga nada · se abre desde la PC · apagar la PC tres días y prenderla trae los tres.
  *`scripts/traer_respaldos.ps1` + `scripts/instalar_tarea_respaldos.ps1`. Destino `D:\Respaldos\Epic_Wallet`, tarea programada a las 8:00 con `StartWhenAvailable`, registro en `traer_respaldos.log`.*
  *Usa el `jarvis-vps` de `~/.ssh/config`: no hay una segunda credencial que mantener.*
  *Probado: 9 archivos bajados, segunda corrida trae 0, borrar una copia y mutilar otra las repone a ambas, y con el servidor inalcanzable sale `FALLA` con código 1. Disparada desde el Programador de tareas da `LastTaskResult 0`.*
  *Baja por un archivo temporal y lo renombra recién al final, así una bajada cortada no deja un archivo con el nombre bueno y el contenido malo. En la PC no hay retención: se acumula todo.*
  *Acá se comprueba el tamaño y la firma `PGDMP`: abrir el dump y contar sus tablas ya lo hizo el servidor, y repetirlo exigiría instalar Postgres en Windows.*

- [x] **F18-T03 · La restauración, probada**
  **Tipo:** QA
  **Hacer:** `scripts/restaurar.sh` de un comando, y **ejecutarlo de verdad** sobre una base vacía a partir del dump de la noche anterior.
  **Aceptación:** · la base restaurada tiene las mismas filas que la original, tabla por tabla · la aplicación levanta contra ella y el tablero muestra los mismos números · **el procedimiento quedó escrito y ejecutado, no sólo escrito**.
  *Esta es la tarea que justifica toda la mudanza. Un respaldo que nunca se restauró no es un respaldo.*
  *`scripts/restaurar.sh`. Restaura en `epic_wallet_restaurado`, una base aparte que crea y pisa; para la base real hace falta `--sobre-la-real` **y** escribir su nombre a mano.*
  *Lo que decide si salió bien no es el código de `pg_restore` —que avisa de cosas que no son errores— sino **contar las filas de cada tabla** contra el origen. Si una sola difiere, falla.*
  *Ejecutada de verdad el 2026-11-23 con una cuenta de QA de 40 movimientos: 11 de 11 tablas iguales, y la aplicación levantó contra la base restaurada (`/api/health` → `connected`). La cuenta y la base de prueba se borraron al terminar.*
  *Tres negativas probadas: apuntar a la base real sin el permiso, un dump truncado —que además **no llega a borrar la base de destino**, porque se verifica antes—, y restaurar un respaldo viejo sobre un origen con 5 filas nuevas, que marca `transactions 45 vs 40 <- DIFIERE` y falla.*

- [x] **F18-T04 · El portón: no se migra sin respaldo fresco**
  **Tipo:** Base
  **Hacer:** que `migrations/env.py` se niegue a correr contra la base real si no hay un respaldo verificado de las últimas horas. Hoy «respaldo primero» es una regla escrita que depende de que alguien se acuerde.
  **Aceptación:** · migrar sin respaldo fresco falla y dice por qué · con respaldo fresco corre normal · se puede saltear sólo con una variable explícita, que queda registrada.
  *Una regla que depende de la memoria de alguien no es una protección.*
  *`migrations/env.py` llama a `exigir_respaldo()` antes de migrar en línea. El modo offline no se toca: sólo imprime SQL.*
  *La decisión vive en `api/app/core/respaldos.py` como funciones puras, con 18 tests. La reusa `/api/health` en F18-T06.*
  *Tres horas, no veinticuatro: con el nocturno de las 3:15 alcanzando, migrar a la noche podría perder el día entero de carga. Lo que se exige es el respaldo del momento.*
  *La api monta `./respaldos` de **sólo lectura**: lee la constancia y no puede escribirla. Si pudiera, un error en la api declararía un respaldo inexistente y el portón dejaría pasar.*
  *Siete casos probados en el servidor contra la base real: sin constancia, de 17 h, fresca pero no verificada → las tres se niegan; `MIGRAR_SIN_RESPALDO=si-entiendo-el-riesgo` pasa avisando por stderr; cualquier otro valor no; con respaldo recién tomado migra; y una base `_test` no pide nada.*

- [ ] **F18-T05 · Registro de cambios: deshacer fila por fila** — *en pausa*
  **Tipo:** Base
  **Hacer:** tabla `audit_log` **sólo-agregar**, llenada por disparadores de Postgres en las 9 tablas de datos: guarda la fila anterior en `jsonb` en cada `update` y cada `delete`, con quién y cuándo. Lo escribe la base, no la aplicación, así que ningún código olvidado lo puede saltear. Más un comando para recuperar una fila concreta.
  **Aceptación:** · borrar un movimiento deja su versión anterior en `audit_log` · el comando lo devuelve sin tocar nada de lo cargado después · RLS activo: una cuenta no ve el registro de otra.
  *Los respaldos cubren «se rompió la base». Esto cubre «se borró algo puntual el martes y me di cuenta el viernes», que restaurando un dump costaría perder miércoles y jueves.*
  ***En pausa por decisión de Gustavo (2026-11-25):** no le encuentra uso hoy. Queda escrita, no se hace. Se retoma si alguna vez borra algo sin querer y restaurar el dump entero resulta demasiado caro — que es exactamente el día en que se va a entender para qué servía.*

- [~] **F18-T06 · Aviso cuando el respaldo no pasó**
  **Tipo:** Infra
  **Hacer:** que `/api/health` informe la fecha del último respaldo verificado, y que haya una señal visible cuando pasaron más de 48 horas sin uno.
  **Aceptación:** · con el respaldo al día, `/api/health` lo muestra · simulando dos días sin respaldo, avisa.
  *Un respaldo que falla en silencio es peor que ninguno: creés que estás cubierto.*
  *Son **dos piezas**, porque el endpoint solo no alcanzaba. Gustavo lo dijo con todas las letras: no entra a mirar la pantalla de salud. Y tiene razón — un aviso que nadie ve no es un aviso.*
  *`/api/health` informa `last_backup` —cuándo, si quedó verificado, hace cuántas horas, si está al día y por qué no— y suma un aviso a `warnings` pasadas 48 horas. **No cambia el estado a `degraded`**: la aplicación funciona perfecto sin respaldo fresco, y confundir las dos cosas haría que un monitor avise de una caída que no pasó.*
  *`scripts/revisar_respaldo.ps1` es la parte que Gustavo sí ve. `traer_respaldos.ps1` ya corre todos los días en su máquina a las 08:00, así que el aviso aparece ahí de **tres formas**, porque cada una falla distinto: notificación de Windows (se ve con la sesión abierta), un archivo `RESPALDO_ATRASADO.txt` en la carpeta de respaldos (se ve siempre) y código de salida 2 (el Programador de tareas lo muestra como «último resultado»). La marca se borra sola cuando el respaldo vuelve.*
  ***48 horas y no 24:*** *el respaldo corre a las 3:15, y con 24 cualquier demora encendería la alarma sin que haya nada roto. A las 48 se perdieron **dos noches seguidas**, y eso no es una demora.*
  *Está en su propio script para poder probarlo **contra una constancia inventada**. Los cinco casos dan lo que tienen que dar —sin constancia, de 72 horas, fresca pero sin verificar, con fecha del futuro, y al día—, y en el quinto la marca se levanta sola. Esperar a que el respaldo falle de verdad para ver si avisa no es una prueba: es enterarse tarde.*
  *Del lado del servidor, 14 pruebas en `test_health.py` y las 18 de `test_respaldos.py`.*

- [x] **F18-T07 · Jarvis también** — *no se hace*
  **Tipo:** Infra
  ***Descartada por Gustavo (2026-11-25):** Jarvis tiene su versión en la máquina local, así que no depende de este servidor para existir. Si alguna vez se vuelve a subir, se decide ahí.*
  *Queda dicho lo que sí sigue sin copia, para que no se pierda el dato: la configuración del proxy de borde (`/opt/edge/`) no vive en ningún repositorio. Si el servidor se pierde, hay que rearmarla de memoria. No es de Epic Wallet, pero es de este servidor.*

---

# FASE 19 — Los datos reales y el corte

**Objetivo:** que tus datos estén en el servidor propio, verificados contra el original, y que la versión anterior se pueda apagar.

**Al cerrar esta fase:** usás la 3.0 todos los días y los números coinciden con los de antes.

- [x] **F19-T01 · Bajar los datos**
  **Tipo:** QA
  **Hacer:** `pg_dump` del esquema de datos y de la tabla de usuarios desde la versión anterior, más el `GET /api/export?format=json` como red de seguridad legible. **Sólo lectura**: no se le escribe nada.
  **Aceptación:** · los dos dumps abren y listan sus tablas · el JSON se puede leer · la versión anterior quedó exactamente como estaba.
  *`scripts/bajar_datos_anteriores.ps1`. **Lo corre Gustavo en su máquina**, no el servidor: las credenciales de la versión anterior viven en `D:\Respaldos\Epic_Wallet\credenciales_2.0.env`, fuera de los dos repositorios, y así no tienen que viajar a ningún lado. `pg_dump` sale de la imagen oficial de Postgres por Docker; no hay nada que instalar.*
  ***Sólo lectura, y la base lo garantiza:*** *la conexión se abre con `default_transaction_read_only=on`, así que un `INSERT`, `UPDATE` o `DELETE` que llegue por ahí lo rechaza el servidor, no el script. Si el host no acepta ese parámetro, avisa fuerte y sigue; lo único que corre son `pg_dump` y un `copy … to`.*
  ***El detalle que haría fallar todo:*** *la `DATABASE_URL` de la aplicación apunta al pooler en modo **transacción** (6543), donde no hay sesión y `pg_dump` falla con un error que no explica por qué. El script detecta el puerto y usa 5432, el de **sesión**, con el mismo usuario y la misma clave.*
  *Baja cuatro cosas: el esquema de datos entero, las filas de `auth.users` tal como están allá, **un CSV con las seis columnas que tiene la `auth.users` de la 3.0** —allá son unas 35, así que un restore directo no encajaría— y **los conteos de filas tabla por tabla**, que son la prueba de aceptación de T02 y hay que tomarlos antes de importar, no después.*
  *El `encrypted_password` viaja tal cual: es un hash bcrypt y la 3.0 usa bcrypt a propósito (F17-T02), así que nadie restablece su contraseña.*
  ***Baja las tres cuentas, no una.*** *No pasa por la aplicación: lee las tablas enteras, así que trae las filas de Gustavo, de Nélida y de Diego juntas. El «Exportar JSON» de Ajustes → Respaldo **no** reemplaza esto: ese pasa por la API y devuelve sólo la cuenta de quien lo toca. Sirve como control aparte, para leer los números con los ojos y compararlos después de importar.*
  ***El corte que evita un archivo hueco.*** *Las once tablas tienen `force row level security`: una fila se ve sólo si la política la deja pasar, y las políticas comparan contra `auth.uid()`, que sale del token. Una conexión de `psql` no tiene token. Si el usuario con el que se entra no puede saltear RLS, el dump **no da error**: abre perfecto, lista las once tablas y no trae una sola fila. Se comprueba antes de empezar —`rolsuper` o `rolbypassrls`— y se corta; y después otra vez contando filas, porque `transactions`, `profiles`, `months` y `categories` no pueden venir en cero en un sistema que se usa todos los días.*
  *Baja también el esquema en texto (`esquema_<fecha>.sql`), para poder poner los dos esquemas uno al lado del otro antes de importar: la 3.0 agregó tablas y pudo cambiar alguna columna, y eso conviene verlo leyendo un archivo y no a mitad de un restore.*

- [x] **F19-T02 · Importar y verificar**
  **Tipo:** QA
  **Hacer:** restaurar los datos y los usuarios en el servidor propio. Los hashes de contraseña viajan tal cual: nadie resetea nada.
  **Aceptación:** · entrás con tu contraseña de siempre · el patrimonio, el ahorro acumulado y los totales de cada mes **coinciden con los de la versión anterior y con el Excel** · la cantidad de filas coincide tabla por tabla.
  *`scripts/importar_datos_anteriores.py` arma el SQL; no se conecta a ninguna base. **Es un script y no un SQL a mano porque esto se corre dos veces**: hoy, y de nuevo el día del corte, porque entre medio se sigue cargando en la 2.0.*
  *Entraron **las tres cuentas reales** —Gustavo, Nélida y Diego— y quedaron afuera diez cuentas `@example.com`, residuos de cuando la batería de pruebas corría contra producción. Se descartan 63 categorías, 2 meses, 1 movimiento y 2 totales que eran de ellas.*
  ***Verificado campo por campo, no por conteo:*** *se volvió a exportar lo que quedó en Contabo y se comparó contra el origen. **Cero diferencias reales** en las 405 filas. Las 807 que aparecían eran la misma fecha en otra zona —el contenedor muestra en hora argentina y el origen en UTC—, y se confirmó comparando instantes.*
  *Los totales guardados de cada mes abierto coinciden con la suma de sus movimientos: los datos no sólo son iguales, son **coherentes**.*
  ***Las tres cosas que hacen fallar una importación, y que el script resuelve:*** *el trigger `al_crear_usuario_public`, que inventaría un perfil y 21 categorías por cada usuario importado; las ocho secuencias, que sin un `setval` harían que el primer movimiento nuevo pida un id que ya existe —y eso no se ve hasta que alguien intenta guardar—; y el orden de las claves foráneas.*
  *Todo en **una sola transacción** con `ON_ERROR_STOP`. Se usó: el primer intento falló en `app_settings.value`, una columna `jsonb` que guarda la cadena `"light"` y que yo escribía sin comillas. Se revirtió entero —0 filas, trigger encendido— y la base quedó como estaba. Las columnas `json` ahora están declaradas en el script, porque mirando el valor no hay forma de distinguir un texto de una cadena JSON: la diferencia la tiene el esquema.*
  *Respaldo previo: `respaldos/tarea/epic_wallet_2026-11-25_0155_antes-de-F19-T02.dump`.*
  *Falta lo único que no puedo hacer yo: que Gustavo entre con su contraseña de siempre y mire si los números son los suyos.*

- [x] **F19-T03 · El corte**
  **Tipo:** QA
  **Hacer:** usar la 3.0 como sistema principal durante una semana con la anterior encendida y de sólo lectura. Recién después, apagarla —decisión tuya, con un respaldo final guardado aparte.
  **Aceptación:** · una semana de uso real sin volver atrás · el respaldo final existe y se probó · lo apagás vos, no yo.
  ***Cerrada por Gustavo el 2026-11-25**, el mismo día de la importación. La semana de espera no se usó: decidió que con los datos adentro y verificados campo por campo, la 3.0 ya es el sistema. Apagar la versión anterior es suyo y se hace desde la otra carpeta.*
  *El respaldo con los datos reales existe y está verificado: `respaldos/tarea/epic_wallet_2026-11-25_0204_con-los-datos-reales.dump`.*

---

# FASE 20 — Interfaz y funciones nuevas

**Objetivo:** el lugar donde van las mejoras de pantalla y las funciones que Gustavo vaya pidiendo, una vez que la 3.0 sea el sistema de verdad.

**No se adelanta nada de acá.** Cada cosa que toque el frontend antes del corte habría que hacerla dos veces: una en la versión que está viva hoy y otra acá. Por eso las nueve tareas que quedaron abiertas de las fases 0 a 13 están congeladas y se retoman desde esta fase.

**Cómo se llena:** cuando Gustavo pide algo o encuentra algo que no le gusta, se anota acá como tarea, con su «qué hacer» y su «cómo se verifica». Nada se ejecuta sin estar escrito primero.

## Lo que ya está anotado

| De dónde viene | Qué |
|---|---|
| F13-T01 | El tamaño de la letra de los gráficos, parejo en todos |
| F13-T02 | Comparación por ítem, dentro de Movimientos |
| F13-T03 | Vencimientos: sección nueva, entre Historial y Cartera |
| F12-T03 | El resto de los ajustes de uso, guiado por lo que vaya apareciendo |
| F12-T05 | Cuatro correcciones de uso: scroll, color, orden y conmutadores |
| F12-T06 | Dos animaciones: el interruptor y la fila que entra |

- [x] **F20-T00 · Sin tareas nuevas todavía**
  Se abren a pedido de Gustavo, de a una.
  *Cerrada el 2026-11-27 al abrirse F20-T01.*

- [~] **F20-T01 · Neumorfismo: el sistema de diseño nuevo**
  **Tipo:** interfaz
  **Hacer:** reemplazar «Vidrio Grafito» por el estilo neumórfico aprobado por Gustavo el 2026-11-27 (mockup de prueba, cuatro pantallas y las piezas). Paleta clara **Ivory Porcelain 60 / Jade Lacquer 30 / Scarlet Signal 10**; paleta oscura **Raven Black 60 / Pewter Grey 30 / Molten Orange 10**. El relieve sale de dos sombras —una abajo-derecha oscura, una arriba-izquierda clara— sobre el mismo material: `.shell` levantado, `.cg` hundido, sin vidrio, sin desenfoque, sin lavados ni ruido. La tarjeta héroe pasa a ser maciza (jade en claro, naranja profundo en oscuro, texto blanco) y las cuatro tarjetas de indicador pasan de color sólido a material teñido con el punto de color en la etiqueta: se invierten entre sí.
  **Cómo se verifica:** `https://13-140-36-93.sslip.io` desde el celular, en los dos temas: las seis vistas, la tarjeta héroe, las cuatro tarjetas, el gráfico diario, los seis meses con la barra de egreso maciza, la lista de movimientos, las hojas, el interruptor y el botón de borrar.
  **Respaldo:** no toca la base ni los datos — frontend y documentación.

- [~] **F20-T02 · El revamp completo, igual al mockup**
  **Tipo:** interfaz
  **Hacer:** llevar la aplicación al detalle del mockup aprobado (`documentacion/mockups/05_Mockup_Neumorfismo.html`), que F20-T01 había dejado a medio camino: la escala tipográfica entera medida sobre el archivo —la cifra héroe pesa el doble que la tarjeta de al lado—, el anillo con la tasa de ahorro dentro de la tarjeta héroe, la cifra de ingreso y egreso en el color pleno de la paleta, la naturaleza del mes en color de acento, las filas de lista sin relieve y separadas por hairlines con su marca hundida, los avisos con el canto de color, las etiquetas de filtro, el botón flotante en el color de la señal, la marca sin el degradado animado y los radios y las piezas planas (sin degradados de vidrio).
  **Arreglado de paso:** `.kpi[style*="--c"]` le pegaba a la héroe y a las cuatro tarjetas teñidas y les ganaba por especificidad — por eso la cifra blanca de la héroe y el jade del ingreso salían casi negros.
  **Cómo se verifica:** `https://13-140-36-93.sslip.io` desde el celular, en los dos temas, mockup al lado: Inicio (héroe con anillo, cuatro tarjetas, gráfico, categorías), Movimientos, Historial, Cartera, Vencimientos y Ajustes.
  **Respaldo:** no toca la base ni los datos — frontend, pruebas y documentación.
  **Segunda vuelta (2026-11-28, con capturas del celular):** el teléfono mostraba el CSS nuevo sobre el HTML viejo —el borde servía `/src/*` sin cabecera de caché y Chrome se quedaba con el JavaScript anterior—. Se agregó `Cache-Control: no-cache` para el HTML y los módulos, y el service worker los pide con `cache: "reload"` para rescatar al que ya tenía la versión vieja guardada. Y los gráficos: entran enteros en la pantalla (se fue el piso de 520 px que los hacía desplazarse de costado), el tamaño de la letra de los ejes se calcula contra el ancho real del dibujo, los márgenes dan lugar a los valores y los meses del eje van abreviados.

- [~] **F20-T03 · La paleta clara nueva y las cuatro tarjetas distintivas**
  **Tipo:** interfaz
  **Hacer:** reemplazar el tema claro. El de F20-T01 no gustó —el marfil se veía apagado y las cuatro tarjetas del tablero no se distinguían entre sí—, así que se probaron seis versiones en `documentacion/mockups/06_Mockup_Claro_Seis_Paletas.html` y Gustavo eligió la **versión 1: Gallery Stone 60 / Jet Black 30 / Rocket Orange 10**, con el 60% aclarado casi a papel. Entra tal cual el mockup. Además, **las cuatro tarjetas del tablero pasan a ser las piezas más distintivas de la pantalla**, con un color propio cada una —verde, naranja, pizarra, azul—, el tinte al 18% y un sello de icono con el color sólido. **El tema oscuro no se toca.**
  **Cómo se verifica:** `https://13-140-36-93.sslip.io` desde el celular, **en tema claro**, con la versión 1 del mockup al lado: Inicio (la héroe azabache con la cifra blanca y su anillo, las cuatro tarjetas con su sello y su color, el gráfico diario, las categorías), Movimientos, Historial, Cartera, Vencimientos y Ajustes. Y después **pasar a oscuro**, que tiene que haber quedado igual que antes salvo el sello de icono nuevo en las cuatro tarjetas.
  **Respaldo:** no toca la base ni los datos — frontend, pruebas y documentación.

- [~] **F20-T04 · El relieve va para afuera**
  **Tipo:** interfaz
  **Hacer:** invertir la gramática del relieve. Todo levantado —el bloque de cada gráfico, las fichas y los ítems de lista (`.cg`), la marca de icono de cada fila y de cada tarjeta—, y hundido **sólo** donde se escribe o se elige: campos, `select`, el surco del conmutador y del interruptor, la pista de una barra de progreso y el botón mientras está apretado. Pedido de Gustavo el 2026-11-28: lo hundido se leía como agujeros.
  **Cómo se verifica:** `https://13-140-36-93.sslip.io` desde el celular, en los dos temas: el gráfico de Inicio y el de los últimos seis meses sobresalen de su tarjeta, los iconos de Gastos por categoría y de Movimientos son pastillas levantadas, las fichas de Mes a mes y los ítems de Vencimientos sobresalen, y el buscador, el combo de categoría y los conmutadores siguen hundidos.
  **Respaldo:** no toca la base ni los datos — frontend y documentación.

- [~] **F20-T05 · Dos macizas y dos de material**
  **Tipo:** interfaz
  **Hacer:** rehacer las tarjetas de indicador. Las de F20-T03 —material teñido al 18%, cada una con su color— no encajaban con la estética del claro: la pantalla no tiene más color que el naranja y quedaban como cuatro manchas pastel. Se probaron tres variantes en `documentacion/mockups/07_Mockup_Cuatro_Tarjetas.html` y Gustavo eligió la B. **La forma sale de la clase de dato, no de la pantalla:** maciza carbón lo que entra, maciza naranja lo que sale, material lo que es un saldo. Vale también para Cartera —Rendimiento macizo, Invertido de material— y para cualquier tarjeta futura. De paso, la etiqueta parte en dos líneas en vez de cortarse y la cifra sube de 17,5 a 20 px.
  **Cómo se verifica:** `https://13-140-36-93.sslip.io` desde el celular, en los dos temas. Inicio: Ingresos carbón y Egresos naranja, macizas; Gasto de hoy y Total de ahorros de material, con la etiqueta entera. Cartera: Rendimiento macizo —carbón en verde, naranja si está en rojo— e Invertido de material.
  **Respaldo:** no toca la base ni los datos — frontend, pruebas y documentación.

---

# Después del traslado

Temas reales del documento general que no entran ahora. No tienen tareas detalladas a propósito: se detallan cuando les llegue el turno.

| Tema | De qué se trata | Por qué puede esperar |
|---|---|---|
| **Cotizaciones automáticas** | Actualizar solo el valor de las inversiones (General §25, §26) | El documento general lo condiciona a «si se encuentra una fuente viable». La actualización manual ya cubre la necesidad |
| **Alertas analíticas** | Gasto muy superior al promedio, categoría disparada, ahorro bajo (General §29). Las de vencimiento ya existen | Nada depende de ellas. Con los datos cargados vas a saber mejor qué umbrales querés |
| **Historial salarial y análisis** | Evolución salarial y métricas históricas (General §28, §53) | Dato interesante, no operativo |
| **PWA offline** | Service worker con caché de lectura y atajos (General §45) | Ya se instala y se abre en modo aplicación. El offline es comodidad |
| **Integraciones futuras** | Importación de Excel y Mercado Pago (General §60, §61) | Fuera del MVP en el documento general. La anti-duplicación ya está en la base |
| **Un dominio propio** | Reemplazar `13-140-36-93.sslip.io` | Funciona y no vence. Cambiarlo después cuesta diez minutos, más reinstalar la aplicación en el celular |
| **Correo saliente** | Recuperación de contraseña por mail | A esta escala es resolver un problema que no existe. El comando de F17-T04 alcanza |

### Lo que se descartó

- **Los dos esquemas de base de datos.** El proyecto trabaja contra **un solo esquema**. A cambio, el procedimiento de migración es: respaldo primero, migrar después. Con los respaldos de la Fase 18 funcionando, el riesgo que esto tenía antes queda cubierto.
- **Las pruebas de interfaz con Playwright en CI.** La interfaz se verifica a mano en el celular, tarea por tarea.
- **Las exigencias numéricas** de cobertura del 90 %, Lighthouse ≥ 90 y presupuesto de KB. El objetivo de 400 ms de `/api/dashboard` se conserva.
- **Autohospedar el stack completo del proveedor anterior.** Ocho contenedores y mucha más superficie para mantener y respaldar, para no reescribir un archivo de autenticación. Va contra «lo simple gana».

### Identificadores

La numeración de las fases es continua: la 3.0 sigue donde quedó la versión anterior, en la Fase 14. Los identificadores de las fases 0 a 13 conservan su significado, y los de la versión 1.0 que desaparecieron están en el historial de Git.

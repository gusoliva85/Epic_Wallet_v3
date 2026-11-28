---
name: epic-wallet-ui
description: Sistema de diseño "Neumorfismo" de Epic Wallet 3.0 — paletas y tokens, las dos capas del material (levantado y hundido), escala tipográfica, componentes y gráficos SVG. Cargar SIEMPRE antes de escribir o modificar cualquier HTML, CSS o JavaScript de interfaz del proyecto, antes de crear un componente o una pantalla nueva, y antes de tocar un gráfico. Es la referencia normativa del frontend aprobado.
---

# Epic Wallet 3.0 · Sistema de diseño "Neumorfismo"

**Aprobado por Gustavo el 2026-11-27 (F20-T01)** sobre un mockup de prueba de cuatro pantallas, y **llevado al detalle del mockup en F20-T02** (2026-11-28): escala tipográfica, filas, anillo de la héroe y color de cada pieza, medidos uno por uno sobre el archivo. Reemplaza al sistema **"Vidrio Grafito"**, que rigió desde la Fase 1; su versión de esta skill y su mockup están en el historial de Git.
**Referencia viva:** `documentacion/mockups/05_Mockup_Neumorfismo.html` — el mockup aprobado, con las cuatro pantallas y las piezas en los dos temas. Ante cualquier duda, ese archivo manda.
**Documento normativo:** `documentacion/02_Documento_Tecnico.md` §13 y §14.

## Reglas que no se negocian

1. **Ningún valor de color, sombra o radio se escribe fuera de los tokens.** Si hace falta uno nuevo, se agrega al bloque `:root` de `tokens.css` **y a los dos bloques oscuros**, nunca suelto en un componente.
2. **Mobile-first de verdad.** Se escribe el CSS de teléfono (390 px) y se agrega lo demás con `min-width`. Nunca al revés.
3. **Sin neón, sin saturaciones altas.** El color significa (ingreso, egreso, ahorro, severidad), no decora.
4. **El gráfico nunca reemplaza los números.** Todo panel con gráfico lleva su pie de cifras.
5. **Todo dato del servidor pasa por `esc()`** antes de entrar en una plantilla.
6. **`prefers-reduced-motion` anula todas las animaciones.** Obligatorio.
7. **Sin framework de UI** y sin librería de gráficos: HTML, CSS (Tailwind + tokens) y JavaScript nativo.
8. Los textos de interfaz van en **español rioplatense** ("cargá", "tocá", "seguís").
9. **La aplicación es multiusuario.** Nunca se escribe un nombre de usuario en el código ni en una plantilla: siempre sale del perfil de la sesión.
10. **Levantado se toca, hundido está elegido.** Es la gramática del sistema y vale para cada pieza nueva (§3).

## Identidad

Una sola pieza de material. El relieve no es un borde ni una capa encima: son **dos sombras del mismo material** —una abajo-derecha oscura y una arriba-izquierda clara— sobre una superficie que es casi el mismo color que el fondo. Si la pieza contrasta con el fondo, deja de leerse como relieve y vuelve a ser una tarjeta pegada encima: ahí está todo el truco.

**El fondo no tiene dibujo propio.** Nada de lavados de color ni de capa de ruido: cualquier textura detrás de las dos sombras se lee como suciedad alrededor del borde.

**Las dos paletas, con su reparto:**

| Tema | 60% material | 30% dato y acción | 10% señal |
|---|---|---|---|
| claro | Ivory Porcelain `#f1ece3` | Jade Lacquer `#1d6b58` | Scarlet Signal `#c62b36` |
| oscuro | Raven Black `#191c21` | Pewter Grey `#8d949d` | Molten Orange `#ff6a1f` |

Dónde va cada uno: el material es todo lo que no es dato (fondos, piezas, relieve). El acento es la tarjeta héroe, el ingreso, la acción principal y las marcas de los gráficos. La señal es el egreso, la alerta, el vencimiento y borrar — y nada más, o deja de ser señal.

## 1 · Tokens

Van en `web/src/styles/tokens.css` y se registran en Tailwind con `@theme`. **Los nombres vienen de Vidrio Grafito y se conservaron a propósito**: `--glass-shell-bg` ahora vale un color sólido y `--sh-md` ahora son dos sombras. Renombrar 4.700 líneas de CSS para cambiar de estilo es de donde salen los `var()` sin definir, que no avisan (§3.2).

```css
:root{
  /* material */
  --color-bg-1:#ebe5db; --color-bg-2:#e7e0d5;
  --surf:#f1ece3;       /* la pieza levantada */
  --surf-2:#e7e0d5;     /* lo hundido */
  --kpi-surf:#e8e1d4;   /* base de la tarjeta de indicador */

  /* las dos sombras: todo lo demás se arma con éstas */
  --sh-lo:rgba(170,158,138,.52); --sh-hi:#fffdf8;

  /* tinta, calibrada sobre la pieza: 12,8 · 7,4 · 4,9 · 3,1 :1 */
  --color-ink:#2a2620; --color-ink-2:#544d44;
  --color-ink-3:#6d665b; --color-ink-4:#8c8373;

  /* acento y señal */
  --color-accent:#1d6b58; --color-accent-2:#14503f; --color-on-accent:#f3efe6;
  --color-inc:#1d6b58; --color-egr:#c62b36; --color-sav:#1d6b58;
  --color-card-inc:#1d6b58; --color-card-egr:#c62b36;
  --color-card-dia:#5f7d72; --color-card-pat:#1d6b58;
  --color-ok:#1d6b58; --color-warn:#9c7400; --color-pend:#b35a16; --color-crit:#c62b36;

  /* levantado, a tres distancias */
  --sh-sm:4px 4px 9px var(--sh-lo),-4px -4px 9px var(--sh-hi);
  --sh-md:6px 6px 14px var(--sh-lo),-6px -6px 14px var(--sh-hi);
  --sh-lg:9px 9px 20px var(--sh-lo),-8px -8px 18px var(--sh-hi);

  /* hundido, a dos profundidades */
  --hundido:inset 5px 5px 11px var(--sh-lo),inset -5px -5px 11px var(--sh-hi);
  --hundido-sm:inset 3px 3px 7px var(--sh-lo),inset -3px -3px 7px var(--sh-hi);

  /* el canto iluminado de una pieza: no es un borde */
  --glass-in:inset 1px 1px 0 rgba(255,253,248,.75);
  --borde-pieza:transparent;

  /* la tarjeta héroe, única superficie maciza */
  --hero:#1d6b58; --on-hero:#fffaf6;
  --hero-sh-lo:rgba(10,55,44,.55); --hero-sh-hi:rgba(118,187,168,.45);
  /* pieza CHICA de acento: tiñe el lado oscuro, no el claro */
  --acc-sh-lo:rgba(12,58,46,.42); --acc-sh-hi:var(--sh-hi);
}
html[data-theme="dark"]{
  --color-bg-1:#13151a; --surf:#191c21; --surf-2:#14171b; --kpi-surf:#23272d;
  --sh-lo:rgba(0,0,0,.70); --sh-hi:rgba(86,94,104,.30);
  --color-ink:#e7e9ec; --color-ink-2:#b9bfc6; --color-ink-3:#9aa1a9; --color-ink-4:#767d85;
  --color-accent:#8d949d; --color-accent-2:#a7aeb6; --color-on-accent:#14171b;
  --color-inc:#a7aeb6; --color-egr:#ff6a1f; --color-sav:#ff8a4c;
  --color-card-inc:#8d949d; --color-card-egr:#ff6a1f;
  --color-card-dia:#7d848c; --color-card-pat:#8d949d;
  --color-ok:#a7aeb6; --color-warn:#e8b454; --color-pend:#ff8a4c; --color-crit:#ff6a1f;
  --hero:#c4511a; --on-hero:#fffaf6;     /* naranja profundo: el texto va en blanco */
  --glass-in:inset 1px 1px 0 rgba(203,209,215,.14);
  --acc-sh-lo:rgba(0,0,0,.6); --acc-sh-hi:rgba(203,209,215,.22);
}
```

**El tema oscuro redefine las mismas variables**, en `html[data-theme="dark"]` y en `@media (prefers-color-scheme: dark)`. Ningún componente conoce el tema; sólo usa tokens.

**Dos pares de sombras de color, no uno.** `--hero-sh-*` tiñe los dos lados y es sólo para la tarjeta héroe. `--acc-sh-*` tiñe el oscuro y deja el claro en la luz del material, y es para toda pieza chica de acento: el sello de la marca, el botón principal, la píldora sólida. En una pieza de 46 px el halo de color se ve como un aura verde —naranja en oscuro— alrededor del botón.

**La severidad dobla la paleta a propósito.** Con tres colores no se pueden representar cuatro severidades: `warn` y `pend` son un ámbar y un naranja quemado dentro de la temperatura cálida del material. Sigue valiendo la regla que importa: el color nunca es el único portador (§8).

`color-mix` con `--mix-tint` (el material, no blanco) y `--mix-ink` es lo que hace que píldoras, iconos y marcas funcionen en ambos temas con una sola regla:

```css
background:color-mix(in srgb,var(--c) 15%,var(--mix-tint));
color:color-mix(in srgb,var(--c) 80%,var(--mix-ink));
```

## 2 · El fondo

Material plano y nada más. Va en una capa fija propia, no en `background-attachment: fixed` (Safari en iOS lo trata como `scroll`).

```css
--ambiente: linear-gradient(170deg,var(--color-bg-1),var(--color-bg-2) 72%);

body::after{
  content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
  background:var(--ambiente);
}
```

Acá vivían tres lavados radiales de color y, encima de toda la aplicación, una capa de ruido en SVG que evitaba que el vidrio se viera plástico. **Las dos se fueron con el vidrio y no vuelven**: el relieve necesita exactamente lo contrario.

## 3 · Las dos capas del material

Toda la profundidad sale de dos clases. **No se inventan variantes.**

| Clase | Forma | Uso |
|---|---|---|
| `.shell` | **levantado** · `--glass-in, --sh-md` | contenedores: topbar, tarjetas, paneles, hojas, navegación |
| `.cg` | **hundido** · `--hundido-sm` | contenido dentro de un `.shell`: filas, fichas, campos |

```css
.shell{position:relative;overflow:hidden;background:var(--glass-shell-bg);
  border:1px solid var(--borde-pieza);box-shadow:var(--glass-in),var(--sh-md)}
.shell::before{content:"";position:absolute;inset:0;background:var(--glass-sheen);pointer-events:none}

.cg{background:var(--glass-content-bg);
  border:1px solid var(--borde-pieza);box-shadow:var(--hundido-sm)}
```

Y la gramática, que vale para cada pieza nueva:

| Forma | Qué significa | Ejemplos |
|---|---|---|
| **Levantado** | esto se toca | botón, píldora, tarjeta, barra, hoja |
| **Hundido** | está elegido, o contiene contenido | surco del conmutador, campo, bloque de gráfico (`--hundido`, la más honda), fila, **botón apretado** |

Tres consecuencias que se verifican mirando:

- **Ninguna pieza lleva borde.** `--borde-pieza` es transparente; el píxel se conserva para no cambiarle la caja a lo que ya lo cuenta. Un borde alrededor de una pieza con relieve es justo lo que rompe la ilusión.
- **Ninguna pieza lleva `backdrop-filter`.** El sistema no desenfoca en ninguna parte: ni tarjetas, ni barras, ni el velo de una hoja. Dejarlo en `blur(0)` es peor que sacarlo — el navegador crea igual la capa y paga el costo para no hacer nada.
- **El radio no es decorativo.** Una esquina casi recta con dos sombras se ve como un error de render: la sombra necesita esquina redonda para girar alrededor de la pieza. Por eso los radios de este sistema son más generosos que los de Vidrio Grafito.

## 3.1 · Las dos barras de navegación

`.topbar` y `.botnav` son `.shell` y nada más: la misma pieza levantada que el resto.

En Vidrio Grafito eran un caso especial y el comentario merece quedar, porque explica un problema que este sistema no tiene: con el vidrio de una tarjeta (52% de opacidad y 22 px de desenfoque), las letras de 9,5 px de la barra inferior se mezclaban con el contenido que pasaba por detrás al hacer scroll y no llegaban al contraste mínimo. Hubo que darles su propio vidrio casi opaco y anularles el brillo diagonal.

**Con material sólido eso no puede pasar**: nada de lo que pasa por detrás se ve a través de una barra. Los tokens `--glass-bar-*` siguen existiendo y valen el mismo color de pieza que `--glass-shell-bg`.

Lo que **sí** se conserva de aquella decisión: la barra necesita separarse del contenido que le pasa por debajo. Eso lo hace su sombra (`--sh-lg`), no la opacidad.

## 3.2 · Un `var()` sin definir no avisa

Si un `var(--x)` no existe, el navegador **descarta la declaración entera en silencio** y el elemento se queda sin ese estilo. No hay error en consola ni nada que se vea al leer el CSS.

Pasó en este proyecto: ocho tokens que se creían agregados nunca entraron a `tokens.css`, y la barra inferior, el botón flotante y la hoja estuvieron en producción con las esquinas cuadradas desde F01-T06. Las pruebas no lo vieron porque comprobaban que el CSS *usara* `var(--radius-*)`, nunca que el token existiera.

**Al agregar un token: comprobar que quedó en el archivo, no que el reemplazo «se ejecutó».** La prueba que cubría esto vivía en `tests/unit/` y se fue con las pruebas de interfaz; la comprobación se hace a mano, recorriendo cada `var()` de los tres CSS y de los `style` en línea del JavaScript contra los tokens definidos.

Así se encontró, en F20-T01, un `var(--color-line-2)` —el token se llama `--line-2`— que dejaba sin fondo el hover de quitar una línea del historial, probablemente desde que se escribió.

## 4 · Tipografía

`Outfit` para cifras y títulos, `Inter` para todo lo demás. Base **15 px / 1,55**. Las cifras llevan `font-variant-numeric:tabular-nums` **siempre**, para que no bailen al actualizarse.

**La escala sale del mockup, medida sobre el archivo** (F20-T02). Lo que importa de ella no es cada valor sino la DISTANCIA entre la cifra héroe y todo lo demás: con la escala de Vidrio Grafito —cifra de indicador a 27,5 px contra una héroe de 35— las dos pesaban casi igual y el tablero quedaba plano. Ahora la héroe pesa el doble que la tarjeta de al lado, y eso es el tablero.

| Rol | Fuente | Tamaño | Peso |
|---|---|---|---|
| Cifra héroe (ahorro del mes, cartera) | Outfit | 32 px | 800 |
| Importe en formulario | Outfit | 33 px | 700 |
| Cifra de indicador | Outfit | 20 px | 700 |
| Cifra de tarjeta teñida | Outfit | 17,5 px | 700 |
| Título de hoja / marca | Outfit | 18 px | 700 |
| Título de panel y de sección | Outfit | 14,5 px | 700 |
| Importe en fila · cifra en ficha `.kv` | Outfit | 14 px | 700 |
| Botón | Inter | 13,5 px | 700 |
| Nombre en fila | Inter | 13 px | 600 |
| Título de aviso | Inter | 12,8 px | 700 |
| Texto base | Inter | 15 px | 400 |
| Píldora de acción `.chip` | Inter | 11,5 px | 600 |
| Secundario de fila · subtítulo de indicador | Inter | 11 px | 400 |
| Etiqueta de indicador · separador de día | Inter | 10,5 px | 700, mayúsculas |
| Píldora de estado | Inter | 10 px | 700, mayúsculas |
| Etiqueta de la barra inferior | Inter | 9,5 px | 600 |
| Eje de gráfico (valores / días) | Inter | 10,5 / 9,75 px | 600 |

## 5 · Puntos de corte

| Corte | Ancho | Qué cambia |
|---|---|---|
| base | < 640 px | Una columna. KPI en 2 columnas. Barra inferior de 5. Botón `+` flotante. Detalle en hoja inferior. |
| `sm` | ≥ 640 px | KPI en 4 columnas. |
| `md` | ≥ 720 px | Cabeceras de panel en fila. Gráficos sin scroll horizontal. |
| `lg` | ≥ 960 px | Navegación superior en lugar de la inferior. Paneles en dos columnas. |
| `xl` | ≥ 1024 px | KPI en 6 columnas. Detalle como cajón lateral derecho. |

Áreas táctiles de **44 × 44 px** mínimo. `env(safe-area-inset-bottom)` respetado en navegación y botón flotante.

## 6 · Movimiento

| Gesto | Duración | Curva |
|---|---|---|
| Entrada de vista | 420 ms | `--ease` |
| Entrada de tarjetas (escalonada) | 500 ms, +60 ms por tarjeta | `--ease` |
| Hoja inferior y cajón | 380 ms | `--ease` |
| Hover de tarjeta y fila | 180–220 ms | `--ease` |
| Crecimiento de barras | 750 ms, +11 ms por barra | `--ease` |
| Trazado de líneas | 1400 ms (`stroke-dashoffset`) | `--ease` |
| Conteo de cifras | 900 ms | cúbica de salida |
| Cambio de tema | View Transitions API si existe | — |

Las dos view transitions —el círculo del cambio de tema y el deslizo entre vistas— **arrancan lisas por construcción**. Hasta F20-T01 había que apagarles el `backdrop-filter` a todas las tarjetas mientras duraban: una view transition saca dos fotos de la pantalla entera, y con una pantalla llena de vidrio el GPU del teléfono recalculaba todos los desenfoques en el primer cuadro y la animación arrancaba trabada. Sin desenfoque en el sistema, esas dos reglas se fueron y no hay nada que apagar.

```css
@media (prefers-reduced-motion:reduce){*{animation-duration:.01ms!important;transition-duration:.01ms!important}}
```

## 7 · Navegación y vistas

Una sola página con siete `<section class="view" data-vista="...">`. **`web/src/js/router.js` es el único que decide cuál está activa.**

```text
#/inicio  #/movimientos  #/historial  #/vencimientos
#/inversiones  #/patrimonio  #/config
```

*(`#/vencimientos` entró en F13-T03, entre Historial y Cartera. Con ella la barra inferior pasó a **seis** posiciones: en 390 px dan 58 px cada una, ajustado pero legible con la etiqueta `corta`. **Es la última que entra**: la próxima sección va a la hoja «Más», o alguna de las seis se muda ahí.)*

*(`#/analisis` existió hasta el 2026-10-21: se sacó —a pedido de Gustavo, era sólo datos de muestra sin ningún endpoint detrás— junto con su posición en `nav.js`.)*

Reglas:

- **Nadie lee la ruta del DOM ni del hash.** Se escucha el evento `epic:ruta` (`import { EVENTO } from "./router.js"`), que llega con `detail.id`. Así las barras no se ponen de acuerdo entre ellas sino cada una con el enrutador, y quedan bien también cuando se llega por «atrás» o por recarga.
- **Para ir a una sección se llama `navegar(id)`**, nunca se toca `location.hash` a mano. `navegar` valida: una ruta que no existe cae en inicio sin dejar entrada en el historial.
- **Las vistas inactivas llevan `hidden`,** que lo pone el enrutador. No alcanza una clase: sin `hidden`, el lector de pantalla lee las seis secciones seguidas y el tabulador recorre los botones de las que no se ven.
- **Hash, no rutas reales.** Con `/movimientos` el servidor tiene que devolver `index.html` en cada ruta o una recarga da 404; el hash ya da historial, «atrás» y enlaces que se pueden guardar.
- **Sólo `hashchange`.** Todas las entradas que crea el enrutador son de hash y el navegador emite `hashchange` tanto al cambiarlo como al recorrer el historial. Agregar `popstate` no cubre ningún caso más: es una línea que nunca se ejecuta sola.
- Al cambiar de vista **se vuelve arriba con `behavior: "instant"`.** Suave, un desplazamiento de miles de píxeles tarda segundos y parece que la aplicación se colgó.
- Una ruta inválida se corrige **reemplazando** la entrada (`replaceState`), no empujando otra: si no, «atrás» vuelve a la ruta mala y de ahí otra vez a inicio, un bucle del que no se sale.

**Las dos barras son navegación, no pestañas.** Marcan con `aria-current="page"`, nunca con `role="tab"` ni `aria-selected`: cambian la URL y el historial, y anunciarlas como un grupo de pestañas le miente a quien usa un lector sobre lo que va a pasar al activarlas.

El comportamiento del enrutador se prueba con jsdom en `tests/js/router.test.mjs` (`npm test`, y también desde `pytest`). Las pruebas que leen el código fuente no sirven acá: recargar en una ruta, volver con «atrás» y caer en inicio son comportamientos, no texto.

## 8 · Componentes

Funciones que reciben datos y devuelven HTML. Sin ciclo de vida, sin estado interno.

### Tarjeta de indicador

```javascript
// héroe: cifra grande + anillo con el porcentaje + barra + pie
`<article class="kpi kpi--hero shell">
  <div class="kpi-label">${esc(label)}</div>
  <div class="kpi-num num">${value}</div>
  <div class="kpi-sub">${sub}</div>
  <div class="kpi-aro" aria-hidden="true">
    <svg class="kpi-anillo" viewBox="0 0 40 40">…<text>24%</text></svg>
    <span class="kpi-aro-g">
      <span class="fin-track"><i class="fin-fill" data-ancho="${pct}"></i></span>
      <span class="fin-pie">Tasa de ahorro 24,4%</span>
    </span>
  </div>
</article>`

// métrica: etiqueta + icono + cifra + subtítulo
`<article class="kpi kpi-metric shell" style="--c:${color}">
  <div class="kpi-top">
    <div class="kpi-label">${esc(label)}</div>
    <span class="kpi-ico"><svg viewBox="0 0 24 24">${icon}</svg></span>
  </div>
  <div class="kpi-num num">${value}</div><div class="kpi-sub">${sub}</div>
</article>`
```

La barra se anima en el siguiente frame: `requestAnimationFrame(()=>el.style.width=el.dataset.w+'%')`.

### Filas de lista

`components/rows.js`. Dos filas y un separador, dentro de un contenedor `.rows`:

```javascript
filaMovimiento({ id, tipo, categoria, importe, fecha, descripcion, origen })
filaCategoria({ id, nombre, total, detalle, participacion, pie, destacada })
separadorDia("04 de octubre 2026")
pintarFilas(contenedor, [ ...filas ])   // escribe y arranca las barras
destacarFilaNueva(contenedor, id)       // hace entrar la fila recién creada
```

Rejilla de `34px 1fr auto`: marca, contenido, valor. **La fila es un `<button>`**, no un `div` con `onclick`: se abre para ver el detalle, así que tiene que alcanzarse con el tabulador y anunciarse.

**La fila NO es una pieza** (F20-T02). No lleva relieve, ni fondo, ni borde: va apoyada sobre el panel y lo único que la separa de la de abajo es una hairline (`.row + .row`). Ocho categorías hechas de ocho piezas hundidas son ocho veces la misma sombra, y el relieve deja de significar algo. Lo que se hunde es el bloque que las contiene, una sola vez. Su marca —la flecha o las iniciales— sí es un hueco: `.row-ico` va hundido, con el color en el trazo y no en el fondo.

**El signo lo decide `tipo`, nunca el valor del importe.** El importe llega ya formateado del backend y sin signo: el frontend sólo formatea y no hace aritmética. Si el signo saliera del texto, un importe que ya trajera un menos saldría con dos.

**Ingreso: `+`, verde y flecha hacia arriba. Egreso: `−`, rojo y flecha hacia abajo.** Los tres a la vez, porque el color no puede ser el único portador. El menos es **U+2212**, no el guión del teclado: el guión es más corto y a otra altura, y al lado de un `+` en una columna de cifras se nota.

**Los importes van en el color pleno de la paleta**, sin mezclar con la tinta: sobre el material —que no es blanco— el jade y el scarlet pasan el contraste mínimo, y mezclados quedaban dos grises con un tinte (F20-T02).

**Un importe sin dirección no lleva color.** El total de una categoría, el valor de una posición: van en tinta. Toda una lista en rojo no avisa de nada — es una lista de gastos, se espera que gasten. En la lista de categorías lo único que va en scarlet es **la que más gastó** (`destacada`), igual que el día más alto del gráfico diario.

La flecha y las iniciales van `aria-hidden`: la flecha repite el signo y las iniciales repiten el nombre de al lado — sin ocultarlas, el lector dice «AL Alquiler». La barra de participación también: el porcentaje ya está en el detalle.

**La fila recién cargada entra, no aparece.** Cae desde arriba empujando al resto, con un halo de acento que se apaga: cargar un movimiento tiene que *verse* en la lista (Gustavo, 2026-10-27). **El alto se mide en JavaScript y viaja a la animación en `--alto-fila`**: `height: auto` no se anima, y dejar la fila con un alto fijo después rompería cualquier descripción larga, así que la clase se saca sola al terminar. El id de la fila nueva llega por el evento `movimiento:creado` que emite `alta-movimiento.js`, nunca por una llamada directa entre pantallas.

**`.row-main` lleva `min-width: 0` y ellipsis.** Sin eso, el nombre largo de una categoría empuja el importe fuera de la fila.

#### El foco tiene que ganarle al hover

`:focus-visible` de `base.css` pone el halo con un selector de **menor especificidad** que `.row:hover`, que reemplaza `box-shadow` entero. Al pasar el dedo por una fila enfocada, el halo desaparecía. Por eso `.row:focus-visible` se declara aparte, con el halo **primero** dentro de su propia `box-shadow` — dibujado después del relieve, queda por debajo.

Esto vale para **cualquier componente que redefina `box-shadow` en `:hover`**: hay que repetir el halo en su propio `:focus-visible`.

#### Panel

`.panel` es la superficie que contiene una lista, y es mínima a propósito: la estructura final de cada vista, con cabeceras, conmutadores y pies de cifras, es de F01-T13.

### Pantallas de cuenta

Cuatro pantallas sin sesión, todas con la misma pieza levantada centrada (`.lock-card.shell`, máximo 372 px) sobre el material del fondo:

| Ruta | Pantalla | Campos |
|---|---|---|
| `#/login` | Iniciar sesión | correo, contraseña, enlaces a registro y recuperación |
| `#/registro` | Crear cuenta | correo, contraseña, repetir |
| `#/recuperar` | Olvidé mi contraseña | correo |
| `#/nueva-clave` | Contraseña nueva | contraseña, repetir |

Reglas de los campos de contraseña:

- **Botón de mostrar y ocultar siempre**, con `aria-label` que cambie entre "Mostrar contraseña" y "Ocultar contraseña". Escribir una contraseña a ciegas en un teléfono es la principal causa de errores de tipeo.
- `autocomplete` correcto para que el gestor del teléfono funcione: `current-password` en login, `new-password` en registro y en contraseña nueva.
- En registro y contraseña nueva se pide **repetir**, con validación en vivo de que coincidan.
- Medidor de fortaleza orientativo, nunca bloqueante más allá del mínimo de 8 caracteres.
- **Los mensajes de error nunca revelan si un correo tiene cuenta.** Ante un correo desconocido, la recuperación responde lo mismo que ante uno válido.

```javascript
// el patrón del campo con ojito
`<div class="field">
  <label for="${id}">${esc(label)}</label>
  <div class="pw-wrap">
    <input class="inp" id="${id}" type="password" autocomplete="${autocomplete}">
    <button class="pw-eye" type="button" aria-label="Mostrar contraseña">
      <svg viewBox="0 0 24 24">${ICO.eye}</svg>
    </button>
  </div>
</div>`
```

### Barra superior

`.topbar` es un `.shell` **pegajoso a 8 px del borde**, no a 0: el hueco deja ver el material por encima de la barra, y con relieve es además lo que deja lugar a su sombra de arriba — pegada al borde, la pieza pierde la mitad del relieve. Lleva `z-index` o el contenido le pasa por arriba al hacer scroll.

```text
.marca-app      sello + nombre · min-width:0 y ellipsis, o desborda en 320 px
.nav-escritorio pestañas, display:none hasta 960 px (abajo manda .botnav)
.acciones       alertas con .contador · [data-tema] · .avatar → configuración
```

El recuadro de `.boton-icono` y `.avatar` mide 37 px para no desarmar la proporción de la barra; el área táctil llega a los 44 px con un `::after` centrado e invisible. **Si se borra ese `::after`, el botón queda en 37 px** y se falla el toque en el teléfono.

El contador de alertas va `aria-hidden`: la cuenta ya está en el `aria-label` del botón ("Alertas: 4 sin leer"), y si no se oculta el lector la dice dos veces. Con cero alertas el globo se esconde con `[hidden]` — un cero rojo alarma sin motivo.

Las pestañas **se generan desde `SECCIONES` de `web/src/js/nav.js`**, nunca a mano en el HTML: la barra superior, la inferior y el enrutador leen de la misma lista y así no pueden discrepar. Son navegación, no un `tablist`: ver §7.0.

### Navegación del teléfono

`.botnav` es un `.shell` **fijo** abajo, con cinco posiciones en rejilla: las seis secciones no entran todas —en 390 px darían 53 px cada una y las etiquetas no se leen—, así que dos se mudan a la hoja de «Más». El reparto lo decide `en_barra_inferior` en `web/src/js/nav.js`, nunca el HTML.

```text
bottom: calc(10px + env(safe-area-inset-bottom))   ← sin el inset, la fila
                                                     queda bajo la barra
                                                     de gestos y no se toca
min-height: 44px en cada posición                  ← skill §5
.botnav button.activa → color Y fondo              ← el color solo no alcanza
aria-current="page", no aria-selected              ← es navegación, no pestañas
```

La etiqueta usa `corta` ("Movim."), no `label`: con el nombre largo se recorta. Y lleva `nowrap`, porque partida en dos líneas desparejaría las cinco alturas.

`.fab` va abajo a la derecha, **encima** de la barra (`bottom: calc(84px + inset)`): es el alcance natural del pulgar. Desde 960 px la barra inferior desaparece —dos navegaciones serían dos posiciones activas que mantener de acuerdo— pero el botón de alta se queda y sólo baja de altura, porque cargar un movimiento es la acción principal en cualquier tamaño.

**El `.app` lleva 104 px de relleno abajo.** La barra es `fixed`: sin ese hueco tapa las últimas filas y nunca se llega al final de una lista.

### Hoja inferior y cajón lateral

`components/sheet.js`. Una hoja es cualquier panel que se abre encima de la aplicación.

```javascript
const hoja = crearHoja(elemento, { disparador, fondo, alAbrir, alCerrar });
hoja.abrir();  hoja.cerrar();  hoja.alternar();  hoja.estaAbierta();
```

En el teléfono sube desde abajo. Desde 900 px, según su variante:

| Clase | Uso | Cómo entra |
|---|---|---|
| `.hoja--cajon` | ver un detalle sin perder de vista la lista | desde la derecha |
| `.hoja--modal` | un formulario, que pide atención completa | centrado, creciendo con fundido |

**380 ms y la curva del sistema**, de la tabla del Técnico §13.6.

#### Las cuatro cosas que hacen que una hoja sea usable

1. **El fondo no hace scroll — y `overflow: hidden` en el body NO alcanza.** iOS lo ignora para el scroller del documento y el fondo se sigue moviendo detrás de la hoja. Hay que usar `position: fixed`, que sí lo frena en todos lados pero salta al principio, así que se guarda `scrollY` y se devuelve al cerrar con `behavior: "instant"` (suave, se ve a la página viajando sola).
2. **El foco queda atrapado adentro**, con el ciclo del tabulador cerrado en los dos sentidos, y vuelve de donde vino al cerrar. Si el foco se fue afuera, el próximo Tab lo trae de vuelta. **Con la hoja cerrada el atrapado no actúa**, o la aplicación se queda sin tabulador.
3. **Lo de atrás queda `inert`.** Es lo que hace que `aria-modal` no sea una promesa vacía: sin eso, el lector de pantalla sigue leyendo la página de atrás aunque no se la vea. El velo NO se vuelve inerte, o deja de recibir el toque que cierra.
4. **Tres formas de cerrar**: toque en el velo, Escape y botón. El oyente de Escape va en `document`, no en la hoja: con el foco devuelto al disparador, una hoja no recibe la tecla.

**El bloqueo del scroll se cuenta, no se alterna.** Se bloquea con la primera hoja y se suelta con la última: si cada una lo manejara por su cuenta, abrir un detalle desde dentro de otra hoja soltaría el scroll al cerrar la de arriba.

Una hoja que puede quedarse sin nada accionable adentro necesita `tabindex="-1"`: si no, el foco no la puede recibir y se queda en el fondo, que está inerte.

### Barra de mes

`.monthbar` es un `.shell` arriba de las vistas: es la cabecera del mes en pantalla y aplica a todas.

```text
‹   Octubre 2026              Hoy  ›
    MES ABIERTO · TRANSACCIONAL
```

Dos reglas de negocio viven acá, no sólo estilo:

- **No hay meses futuros** (General §12.1). En el mes actual la flecha de siguiente va `disabled`, y «Hoy» también, porque no lleva a ninguna parte. Apagado **de verdad**, no mudo: un botón que se ve activo y no responde parece que la aplicación se colgó. Hay además un tope dentro de `mover()`, por si alguien la llama desde otro lado.
- **El subtítulo dice si el mes es transaccional o consolidado** (Regla 4), porque de eso depende lo que se puede hacer en la pantalla.

**El nombre del mes se calcula, nunca se escribe.** Un texto fijo sería mentira el mes que viene. Y se calcula en `America/Argentina/Buenos_Aires`: con la zona del dispositivo, el día 1 o el 31 el título muestra el mes equivocado. Para formatear se pide **sólo el mes** y el año se pega aparte — pidiendo los dos juntos, `es-AR` devuelve «octubre de 2026» y el «de» ocupa lugar en una pantalla angosta.

El título va en una región `aria-live="polite"`: quien no ve la pantalla toca la flecha y, sin eso, no se entera de a qué mes pasó.

### Píldora de acción · `.chip`

Botón chico de acción: las flechas de mes, «Hoy» y, desde F01-T12, los filtros. Variante `.chip.solid` cuando es la acción principal.

El recuadro mide unos 33 px, así que el área táctil llega a 44 con un `::after` centrado. **En `:disabled` ese `::after` se saca** (`content: none`): si se mantuviera, un toque al lado de un botón apagado caería en el apagado y no pasaría nada. El `:hover` y el `:active` llevan `:not(:disabled)`, o un botón apagado se levanta al pasarle el dedo y parece tocable.

### Tarjetas de indicador

`components/kpi.js`. Dos variantes y nada más: **héroe** (cifra grande, anillo, barra y pie) para el ahorro del mes y la cartera, y **métrica** (etiqueta, cifra, subtítulo) para todo lo demás.

```javascript
tarjetaHeroe({ etiqueta, cifra, sub, porcentaje, anillo, pie, pieIzq, pieDer, color })
tarjetaMetrica({ etiqueta, cifra, sub, color, icono, tarjeta })
pintarTarjetas(contenedor, [ ...tarjetas ])   // escribe y arranca las barras
```

- **Todo campo pasa por `esc()`, los seis.** El ejemplo del documento técnico §12.4 escapa `label` y `value` pero no `sub`: un subtítulo puede traer el nombre de una categoría que escribió el usuario, y es una puerta igual que los otros. Lo mismo el pie de la héroe y la cifra.
- **`color` sale de una lista cerrada** (`COLORES_VALIDOS`), no de un string libre: el valor termina dentro de un atributo `style` y la política del sitio admite estilos en línea, así que un color libre sería CSS inyectable. Un nombre inválido cae en el acento.
- **`icono` también es un nombre de `iconos.js`**, no un trazo. Un nombre que no existe devuelve cadena vacía, nunca `undefined` dentro del SVG.
- `porcentaje` se recorta a 0–100: un ahorro negativo daría una barra de ancho negativo y un 140 % desbordaría el surco.
- **`anillo` es `null` cuando no hay porcentaje que mostrar**, y entonces no se dibuja. Un anillo vacío se lee como «cero por ciento», que es justo lo que la regla de la tasa de ahorro con ingresos en cero no quiere decir (General §52). El valor del anillo se redondea al entero —adentro no entran dos cifras y una coma—; el decimal va en el pie.
- **El pie tiene dos formas y son excluyentes**: `pie` es una línea sola bajo la barra; `pieIzq`/`pieDer` son dos datos a los extremos. Sin ninguno, no se renderiza: un pie vacío suma el hueco de su `margin-top`.
- Todo el bloque de abajo (`.kpi-aro`) va `aria-hidden`: la cifra de arriba dice el valor y el pie dice el porcentaje con todas las letras — anunciarlo tres veces no agrega nada.
- **`pintarTarjetas` escribe todas de una vez.** Con siete asignaciones a `innerHTML` el navegador recalcula el layout siete veces y en un teléfono se ve el salto.

**La barra nace en 0 en el CSS y recibe su ancho en `requestAnimationFrame`.** Puesta directo, la transición no tiene de dónde partir y aparece ya llena. Y tiene que ser `requestAnimationFrame`: una microtarea corre antes del pintado, así que el ancho se junta con el primer render y tampoco se ve crecer. Ojo: **esa diferencia no se puede probar en jsdom**, los dos se ven iguales; por eso `tests/unit/test_kpi.py` la verifica leyendo el código y lo dice.

#### Tarjeta teñida

Las cuatro métricas del tablero son **piezas de material teñidas por el color de su dato** (F20-T01).

```javascript
tarjetaMetrica({ etiqueta, cifra, sub, tarjeta: "inc" | "egr" | "dia" | "pat" })
```

```text
inc  jade      (pewter en oscuro)     ingresos
egr  scarlet   (molten orange)        egresos
dia  jade apagado (pewter apagado)    gasto de hoy
pat  jade      (pewter)               total de ahorros
```

El color entra en tres lugares y en ninguno más:

1. **Un 10% mezclado en la superficie**, contra `--kpi-surf` (un escalón del material, no la pieza). Diez por ciento y no más: con el color al 25% dejan de ser material y pasan a ser cuatro rectángulos de color. «Gasto de hoy» va al 5%: es el dato más blando de los cuatro.
2. **La etiqueta y su punto**, con el color casi pleno (82% contra la tinta, para que 10,5 px no queden al límite del contraste). El punto lo pone el CSS con un `::before`: es decoración y no tiene que existir en el DOM ni leerse en voz alta.
3. **La cifra, pero sólo donde el color significa DIRECCIÓN** (F20-T02): el jade del ingreso y el scarlet del egreso, plenos. «Gasto de hoy» y «Total de ahorros» llevan la cifra en tinta — no son una dirección, son un saldo, y pintarlas les daba un peso que no tienen.

**Ningún texto cae encima del color**, así que los cuatro valores no necesitan contraste con blanco: son los de la paleta sin retoques.

> **Qué había antes y por qué se fue.** Hasta el 2026-11-27 eran cuatro tarjetas de **color sólido con texto blanco**, con el signo pesos grande recortado contra el borde y el símbolo arriba a la derecha (diseño de Gustavo, `mockups/tarjetas.png`). Los cuatro fondos estaban calibrados a 5,3–6,0:1 con blanco, y el signo pesos iba más oscuro que la tarjeta porque aclarándolo la cifra blanca caía a 3,3:1. Todo eso se fue con Vidrio Grafito: en el sistema nuevo **la única superficie maciza es la tarjeta héroe**, y cuatro rectángulos de color al lado le competían. Se invirtieron entre sí.

#### La tarjeta héroe

La única superficie maciza de la aplicación: el ahorro del mes y el patrimonio neto.

```text
fondo      --hero      jade en claro · molten orange PROFUNDO en oscuro
texto      --on-hero   blanco, también la cifra y el pie
cifra      32 px / 800 — el doble que la tarjeta de al lado, a propósito
sombra     --hero-sh-* teñida de los dos lados (es grande: acá el halo
                       de color se lee como el canto de la pieza)
anillo     52 px, trazo 5, pathLength="100", el entero adentro
barra      canal negro al 22%, relleno en --on-hero
brillo     .kpi--hero::before { content: none }
```

El naranja del héroe en oscuro es **un paso más profundo que `--color-egr`**, y es a propósito: su texto va en blanco, y sobre el naranja pleno el blanco queda al límite de lo legible. El naranja pleno sigue intacto en todo lo demás.

### Rejilla y entrada escalonada

`.kpi-grid` va **2 → 4 → 6** columnas en los cortes de §5, y `.kpi--hero` ocupa siempre media fila (2 de 2, 2 de 4, 3 de 6) para que la cifra importante conserve su peso.

`.stagger > *` escalona **de a 60 ms, en CSS con `nth-child`**, no con `style` en línea desde JavaScript: el retardo vive con el resto del estilo y un componente no tiene que saber en qué posición lo van a pintar. A partir de la novena el retardo se congela — con 20 filas, la última entraría más de un segundo después y parecería que la pantalla se cuelga por partes.

**El bloque de `prefers-reduced-motion` de `base.css` anula la duración, no el retardo.** Sin anularlo aparte, con movimiento reducido las tarjetas siguen apareciendo de a una, sólo que de golpe.

### Avisos, píldoras y notificaciones

```javascript
aviso({ severidad: "ok"|"warn"|"pend"|"crit"|"info", titulo, texto })
pildora({ texto, tipo })          // las cinco + "neutral"
toast("Movimiento guardado")      // components/toast.js
toast("No se pudo guardar", { severidad: "crit" })
```

**Las mezclas de color NO son las del mockup.** Ahí el texto iba al 80% del color: en tema claro el ámbar daba 3,51:1 y el naranja 4,29:1, los dos por debajo del mínimo. Acá el texto va al **60%** y el fondo al **15%**, con lo que el peor caso de las cinco severidades en los dos temas queda en 4,98:1. El icono del aviso sí conserva el 80%, porque es un gráfico y su mínimo es 3:1.

#### El ámbar y el naranja son parecidos, y no se arregla con CSS

Medido: entre `warn` y `pend`, la distancia de color es **7 sobre 765** en el fondo de la píldora y sólo **31** en el texto. Ninguna proporción los separa, y subirla rompe el contraste.

Por eso la regla no es «que los colores se distingan» sino que **el color no sea el único portador**: cada severidad lleva su icono y su nombre (`aria-label` en el icono, no `aria-hidden`). Dos severidades de color parecido tienen que llevar iconos distintos — `warn` y `crit` comparten el triángulo porque sus colores están lejos (81 contra 31).

#### Notificación breve

Dos cosas la definen y las dos son fáciles de hacer mal:

1. **La región viva tiene que existir ANTES del mensaje.** Un lector anuncia los *cambios* dentro de una región `aria-live`; si la región se crea junto con el texto, no hay cambio que anunciar y el mensaje pasa en silencio. Por eso el `<div id="toast">` está en el HTML, vacío, desde que carga la página — y por eso vacío se achica con `padding: 0` y no con `display: none`, que lo sacaría del árbol y dejaría de observarse.
2. **Dos mensajes seguidos hacen cola, no se pisan.** Reemplazar es más simple, pero acá los mensajes son «movimiento guardado» o «no se pudo guardar»: perder uno es perder información. El siguiente espera a que el anterior **termine de irse** (`SALIDA`), o los dos se cruzan en pantalla durante la transición. **`SALIDA` tiene que ser ≥ la duración del CSS**; hay una prueba que compara los dos números.

2600 ms en pantalla. El toast va arriba de la barra inferior y del botón flotante, y baja desde 960 px cuando esos ya no están.

### Tarjeta plegable con interruptor

El patrón de la comparación por ítem (F13-T02), para lo que es una **consulta puntual** y no algo que tenga que estar abierto todo el tiempo:

```text
.card.shell[data-interruptores-propios]
  .cfg-row.comp-cabeza     título a tamaño de panel + bajada + .toggle
  .comp-cuerpo[hidden]     todo lo demás, con fundido corto al aparecer
```

Tres reglas:

- **Plegada no pide nada.** El módulo no llama a la API hasta que se prende el interruptor: si pidiera igual, la vista costaría una llamada más en cada carga sin que se note en la pantalla.
- **`data-interruptores-propios` en el contenedor.** El delegado genérico de `views/vistas.js` da vuelta cualquier `.toggle` que encuentre; un interruptor con dueño —que llama a la API y pinta la respuesta— tiene que quedar afuera, o el segundo cambio de `aria-checked` lo deja mintiendo sobre el estado real. Es el mismo bug que ya había tenido `#config-categorias`.
- **Los conmutadores de adentro se miden al abrirse.** Un `.view-switch` oculto mide 0, así que la pastilla quedaría apoyada en el borde: hay que llamar a `sincronizar(grupo)` cuando el cuerpo ya es visible.

### Fila de configuración con detalle

La lista de Vencimientos (F13-T03): una `.cfg-row` con el interruptor y, cuando está prendida, un `.venc-detalle` debajo con los dos selectores y el estado de hoy.

```text
.venc-lista            padding 12px 14px 14px  ← 14 px contra la tarjeta y
                                                 12 px contra el conmutador
                                                 de arriba; sin eso los ítems
                                                 quedan pegados a los bordes
.venc-item.cg          radius de tarjeta, overflow hidden
  .cfg-row             nombre + bajada + .toggle
  .venc-detalle        rejilla de 2 columnas; el estado ocupa el ancho
```

El estado va en una `.pill` **con su texto** («Faltan 3 días», «Vencido hace 2 días»), no sólo con el color: ámbar y rojo tienen que distinguirse sin verlos (§8, avisos).

### Otros

- **`.pill`** en cinco variantes: `ok`, `warn`, `pend`, `crit`, `neutral`.
- **`.alert`** con `--c` por severidad, borde y sombra teñidos.
- **`.view-switch`** conmutador de pastillas dentro de un surco hundido. **Su comportamiento es de `components/switch.js` y de nadie más**: la pastilla marcada es UN elemento absoluto (`.vs-ind`) que se desliza hasta la opción elegida, y la clase `activa` la escribe sólo ese módulo (`activar(boton)`, o `sincronizar(grupo)` después de pintar el HTML del grupo). Dos módulos marcando la misma clase es de donde salían los estados raros que se corrigieron el 2026-10-27.
- **`.sheet`** hoja inferior en móvil; desde 900 px pasa a cajón lateral (`.sheet`) o modal centrado (`.sheet.center`). Cierra con toque afuera, Escape y botón.
- **`.toast`** con `aria-live="polite"`, cierre automático a 2,6 s.
- **`.toggle`** interruptor de encendido. Tres cosas lo definen: el pulgar se desliza con una curva con rebote, **se estira mientras se mantiene apretado** (`:active`, como un control físico que cede antes de soltar) y **el color del surco es una capa `::after` con opacidad**, no el `background` del botón — un degradado no se puede interpolar, así que puesto como fondo el color saltaba de golpe mientras el pulgar se deslizaba con todo el cuidado del mundo.
- **`.cfg-row`**, **`.kv`**, **`.mini`**, **`.ghost-note`**.

## 9 · Gráficos

SVG generado por JavaScript, `viewBox` para escalar, colores por **variable CSS** (`fill="var(--inc)"`) para heredar el tema sin redibujar. Ningún gráfico tiene sentido sin su pie de cifras.

### El gráfico diario — el más importante

Barras de ingresos y egresos por día **más la línea del ahorro acumulado del mes**, con **doble eje**:

```text
Eje X        días del mes (1…día actual)
Eje Y izq.   importe diario → barras (verde ingresos, roja egresos)
Eje Y der.   ahorro del mes acumulado → línea azul grafito 2,7 px
             · punto y etiqueta en el valor de hoy
             · línea de cero punteada si el ahorro se vuelve negativo
             · rótulo "AHORRO" sobre el eje
Modos        Ambos · Egresos · Ingresos · Acumulado
             (la línea de ahorro se mantiene visible en los cuatro)
```

**Por qué doble eje:** el gasto diario se mueve en decenas de miles y el ahorro acumulado en millones. Con un solo eje la línea aplastaría las barras. Esto es un pedido explícito de Gustavo: se ve de un golpe el salto del día del sueldo y cómo el ahorro baja con cada gasto.

```javascript
// la serie que alimenta la línea
const sav=[]; let acc=0;
for(let i=0;i<n;i++){ acc+=inc[i]-exp[i]; sav.push(acc) }
```

### Los demás

| Gráfico | Tipo | Modos |
|---|---|---|
| Últimos seis meses | Barras agrupadas (ingresos, egresos, ahorro) | Barras · Ahorro · Tasa |
| Gastos por categoría | Barras horizontales de mayor a menor | Mayor gasto · A–Z |
| Evolución del ahorro | Área con línea del saldo acumulado | — |
| Composición patrimonial | Barra apilada horizontal | — |
| Evolución salarial | Área con línea | — |

### Reglas comunes

- `niceMax()` para que los ejes caigan en valores redondos.
- Mínimo **1,5 px** de alto en las barras, para que un gasto chico se vea.
- Los `<linearGradient>` llevan **id único** por instancia: si dos gráficos coexisten en el DOM, uno toma el color del otro.
- En móvil `min-width:520px` con scroll horizontal; desde 720 px se ajusta al ancho.
- **`touch-action` en un contenedor con scroll propio lleva LOS DOS EJES** (`pan-x pan-y`), nunca `pan-x` solo. `.app` pide `pan-y` para los gestos (§7) y el navegador cruza los dos valores: con `pan-x` a secas, el dedo apoyado sobre un gráfico o una tabla los movía de costado pero ya no scrolleaba la página hacia abajo. Vale igual para `.tbl-wrap` y para `.view-switch`.
- **El respiro contra la tarjeta es MARGEN, no relleno.** El relleno es parte de lo que se desplaza: apenas el dedo mueve el gráfico, el dibujo pasa por debajo y toca el borde igual. Con `margin: 0 14px` el que queda adentro de la tarjeta es el contenedor, y el recorte sucede 14 px antes del borde en cualquier posición del scroll.
- **EL TAMAÑO DEL TEXTO SE COMPENSA POR LA ESCALA DEL GRÁFICO** (F13-T01). Un `font-size` dentro de un `<svg>` está en unidades del `viewBox`, no en píxeles de pantalla: el mismo 10 se ve a 6,8 px en el gráfico de 760 de ancho y a 9,6 px en uno de 540, porque cada uno se escala distinto para entrar en la tarjeta. `etiquetaSvg()` publica `--escala-grafico` (su ancho sobre el ancho de referencia del sistema, **520**) y `.axis-v`/`.axis-t` multiplican su token por esa variable. Consecuencia práctica: **el valor de `--text-axis` y `--text-axis-sm` es el tamaño real en el teléfono**, y es el mismo en los cuatro gráficos. Un `<svg>` armado sin `etiquetaSvg` se queda con la escala 1 y vuelve a depender de su ancho.
- Un gráfico que **entra** en la tarjeta sin scroll (hasta siete barras, como la comparación por ítem) usa un `viewBox` angosto —400— y pide `min-width: 0`; uno que no entra crece y desplaza, pero **a escala 1**, para que las cifras no se achiquen. Las dos formas conviven porque las dos pasan por la misma compensación.
- **El ancho de cada categoría tiene tope, y el grupo va centrado.** Con pocas barras y el ancho repartido a secas, quedan separadas a media pantalla (Gustavo, 2026-11-10). Lo que sobra tiene que ser margen a los costados, nunca distancia entre barras.
- `role="img"` y `<title>` con el resumen en texto.

## 10 · Formato de importes

El backend manda strings decimales. El frontend **sólo formatea, nunca calcula**.

```javascript
fmt(3491280)    // "$3.491.280"
fmtS(-42000)    // "−$42.000"     (signo menos tipográfico U+2212)
fmtK(3491280)   // "$3,5M"   · fmtK(340000) → "$340k" · negativos con −
pct(31.7)       // "+31,7%"  · null → "N/A"
```

Separador de miles con punto y decimal con coma (es-AR). **Tasa de ahorro con ingresos en cero devuelve `N/A`, nunca 0 % ni error.**

## 11 · Estados

Cada vista implementa los cuatro, con `components/estados.js`. **Nunca una pantalla en blanco.**

| Estado | Tratamiento |
|---|---|
| Cargando | Esqueletos con la **forma** del contenido final: mismas alturas. Más bajos, la página salta al llegar los datos y se pierde el lugar. Van con `aria-busy` y un texto para lector: un esqueleto no dice nada, y sin eso parece que la sección está vacía. |
| Error | Qué pasó **y un botón para reintentar**. Nunca un callejón sin salida. |
| Vacío | Texto que explica, no un cero seco. En gris, no en acento: no es un problema. |
| Mes consolidado | Texto propio. **No se reusa el vacío**: decir «no hay movimientos» de un mes consolidado es falso — los movimientos existieron, lo que se guarda son los totales (regla 4). |
| Sin conexión | Banda arriba de todo, fuera de las vistas. Se escuchan `online`/`offline` **y además se consulta `navigator.onLine` al arrancar**: abriendo la aplicación ya sin conexión, el evento `offline` nunca llega porque no hubo transición. |

## 11.1 · Estructura de una vista

```text
.sec-head      cabecera fuera de un panel: título, bajada y acción
.card.shell    panel; su .card-head pasa a una fila desde 720 px
.view-switch   conmutador de modos, píldoras en un surco
.grid-2        dos columnas desde 960 px
.tbl-wrap      tabla
.kv-grid       fichas de dato (la ecuación del patrimonio, las métricas)
.cfg-row       fila de preferencia con su .toggle
.ghost-note    una regla de negocio que conviene que esté a la vista
```

**La tabla es lo ÚNICO con scroll horizontal, y es a propósito.** Seis columnas de números no entran en 390 px, y partirlas en dos líneas hace ilegible la comparación entre meses, que es para lo que está. Lleva `tabindex="0"` y nombre: una región con scroll que no recibe foco no se puede desplazar sin mouse y lo de la derecha queda inalcanzable. En ningún otro lado puede haber `overflow-x` ni un `min-width` grande — es la causa más común de scroll horizontal en el teléfono, y hay una prueba que lo vigila.

**El interruptor de ajustes es un `<button role="switch" aria-checked>`**, no un `div` con clase: un div no se alcanza con teclado ni dice si está activado.

## 11.3 · Dos cosas que no van en el tablero

**Las alertas viven en una hoja que abre la campanita**, no en el tablero. Ahí competían con los indicadores y empujaban el resto de la pantalla hacia abajo. Es `.hoja--modal` y no `.hoja--cajon`: una alerta pide atención, no se mira de reojo mientras se sigue leyendo la lista. **El número del globo sale de la misma lista que llena la hoja** — escrito a mano, el botón diría un número y la hoja mostraría otro.

**Un gráfico que todavía no existe NO se marca con un esqueleto de carga.** Un esqueleto que brilla para siempre dice «esto está cargando», no «esto llega más adelante», y quien abre la aplicación se queda esperando. Va `.grafico-pendiente`: borde punteado, el alto real del gráfico —para revisar la maqueta con las proporciones de verdad— y un texto que dice **qué** gráfico va ahí y **en qué fase** llega. El esqueleto sigue existiendo para su uso real: mientras la API responde.

## 11.2 · Los datos de ejemplo

Todos en `web/src/js/datos-muestra.js`, **ninguna vista inventa un número**. Si una escribiera un importe propio, al conectar la API quedaría un número fijo en medio de los reales y nadie se daría cuenta; hay una prueba que lo impide.

Los importes son **strings ya formateados**, como los va a mandar el backend. Con números, las vistas se acostumbrarían a hacer cuentas y después habría que sacarlas: el frontend sólo formatea, nunca calcula.

Y la pantalla **dice que son de muestra**: una cifra creíble sin aclaración se puede tomar por un dato real.

## 12 · Accesibilidad

- Contraste mínimo 4,5:1 en ambos temas.
- `aria-label` en todo botón de sólo icono; `aria-live="polite"` en el toast; `aria-expanded` en lo que se expande.
- Foco visible: `box-shadow:0 0 0 4px var(--accent-ring)`.
- Navegación completa por teclado; foco atrapado dentro de una hoja abierta.

## 13 · Qué NO hacer

- No agregar librerías de UI ni de gráficos.
- No escribir colores, sombras ni radios fuera de los tokens.
- **No usar `backdrop-filter`.** El sistema no desenfoca en ninguna parte.
- **No poner borde a una pieza con relieve.** Es lo que rompe la ilusión.
- **No levantar lo que está elegido ni hundir lo que se toca.** La gramática de §3 es lo que hace que la interfaz se entienda sin explicarla.
- **No teñir el lado claro de la sombra en una pieza chica de acento.** Queda un aura de color alrededor del botón: para eso están `--acc-sh-*`.
- **No poner relieve a cada fila de una lista.** La lista es un bloque; las filas son hairlines.
- **No usar el color de la señal fuera de egreso, alerta, vencimiento y borrar.** La única excepción del sistema es el botón flotante, que es así en el mockup aprobado: es la acción que se toca cien veces por mes y la única pieza que flota.
- **No escribir un `[style*="--c"]` sin los dos puntos.** `--c-card` también lo cumple, y el selector termina pintando tarjetas que no eran (F20-T02).
- No usar `innerHTML` con datos del servidor sin `esc()`.
- No hacer aritmética con dinero en el frontend.
- No inventar movimientos para un mes consolidado.
- No diseñar en escritorio y reducir.
- No neón, no gradientes estridentes, no sombras de color saturado.
- No JavaScript en línea en el HTML (lo bloquea la política de contenido).

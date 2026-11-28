/* Tarjetas de indicador · F01-T09
   Referencia: 02_Documento_Tecnico.md §12.4 · mockup 01, .kpi

   Funciones que reciben datos y devuelven un string de HTML. Sin ciclo
   de vida ni estado interno, como el resto del catálogo.

   Dos variantes:

     héroe    cifra grande, barra de progreso y pie de dos datos.
              Es el ahorro del mes y el patrimonio.
     métrica  etiqueta, icono, cifra y subtítulo. Todo lo demás.

   TODO dato que entra pasa por `esc()`. El ejemplo del documento
   técnico §12.4 escapa `label` y `value` pero no `sub`: un subtítulo
   es tan del servidor como los otros dos —puede traer el nombre de una
   categoría que escribió el usuario— y acá se escapa también. */

import { esc } from "../format.js";
import { icono } from "../iconos.js";

/* Los colores que puede pedir una tarjeta. Lista cerrada a propósito:
   el valor termina dentro de un atributo `style`, y la política de
   contenido del sitio admite estilos en línea. Con un color libre, un
   dato del servidor podría inyectar CSS. Con esto, lo peor que pasa es
   que una tarjeta salga del color del acento. */
const COLORES = {
  inc: "var(--color-inc)",
  egr: "var(--color-egr)",
  sav: "var(--color-sav)",
  ok: "var(--color-ok)",
  warn: "var(--color-warn)",
  pend: "var(--color-pend)",
  crit: "var(--color-crit)",
  accent: "var(--color-accent)",
};

export const COLORES_VALIDOS = Object.freeze(Object.keys(COLORES));

/* El catálogo de tarjetas del tablero. Cada entrada dice DOS cosas, y
   las dos salen de acá: qué clase de dato es y con qué icono se marca.
   La forma —maciza o de material— la decide la clase de dato, nunca la
   pantalla donde se usa (F20-T05):

     entra   lo que suma      maciza, carbón
     sale    lo que resta     maciza, naranja
     saldo   una posición     material, cifra en tinta

   Por eso Cartera sale bien sin saber nada de esto: pide `inc`/`egr`
   para el rendimiento según el signo y `pat` para lo invertido, y la
   regla hace el resto. Lo mismo va a pasar con la tarjeta que se
   agregue mañana: lo único que hay que contestar es si el dato es una
   dirección de la plata o un saldo.

   EL ICONO VA EN EL CATALOGO Y NO LO ELIGE QUIEN LLAMA. Si fuera un
   parámetro, el mismo dato podría salir con la flecha para arriba en
   una pantalla y con el calendario en otra. El que llama dice qué
   tarjeta es, no cómo se dibuja.

   Es una lista cerrada, y eso vale aunque ya no haya colores en línea:
   son cuatro y son éstas: no es un parámetro libre, es un catálogo. */
const TARJETAS = {
  inc: { tipo: "entra", icono: "sube" },
  egr: { tipo: "sale", icono: "baja" },
  dia: { tipo: "saldo", icono: "calendario" },
  pat: { tipo: "saldo", icono: "caja_fuerte" },
};

/* La clase de la pieza, por tipo de dato. Las dos macizas llevan
   además `.kpi-maciza`, que es donde vive todo lo común: el texto en
   `--on-card-maciza`, el sello calado y el brillo diagonal apagado. */
const FORMA = {
  entra: "kpi-maciza kpi-entra",
  sale: "kpi-maciza kpi-sale",
  saldo: "kpi-saldo",
};

export const TARJETAS_VALIDAS = Object.freeze(Object.keys(TARJETAS));

function color(nombre) {
  return COLORES[nombre] ?? COLORES.accent;
}

/**
 * Tarjeta de métrica: etiqueta, icono, cifra y subtítulo.
 *
 * Con `tarjeta` —uno de `TARJETAS_VALIDAS`— pasa a ser una tarjeta del
 * tablero: maciza si el dato es una dirección de la plata (entra o
 * sale), de material si es un saldo. El icono y la forma los decide el
 * catálogo, no quien llama. Sin `tarjeta`, es la pieza de material de
 * siempre y el icono sale de `icono`.
 *
 * @param {{etiqueta: string, cifra: string, sub?: string,
 *          color?: string, icono?: string, tarjeta?: string}} datos
 */
export function tarjetaMetrica({
  etiqueta,
  cifra,
  sub = "",
  color: c,
  icono: ico,
  tarjeta,
}) {
  const t = TARJETAS[tarjeta];

  if (t) {
    // Tarjeta del tablero (F20-T05). La forma sale del tipo de dato:
    // maciza si es una dirección de la plata, material si es un saldo.
    // El CSS hace todo lo demás; acá no se elige ningún color, y ya no
    // viaja ninguno en un atributo `style`.
    //
    // El sello va `aria-hidden`: el icono repite lo que dice la
    // etiqueta de al lado, y sin ocultarlo el lector lo anuncia dos
    // veces.
    return (
      `<article class="kpi kpi-metric shell ${FORMA[t.tipo]}">` +
      '<div class="kpi-top">' +
      `<div class="kpi-label">${esc(etiqueta)}</div>` +
      '<span class="kpi-ico" aria-hidden="true">' +
      `<svg viewBox="0 0 24 24">${icono(t.icono)}</svg>` +
      "</span>" +
      "</div>" +
      `<div class="kpi-num num">${esc(cifra)}</div>` +
      `<div class="kpi-sub">${esc(sub)}</div>` +
      "</article>"
    );
  }

  return (
    `<article class="kpi kpi-metric shell" style="--c:${color(c)}">` +
    '<div class="kpi-top">' +
    `<div class="kpi-label">${esc(etiqueta)}</div>` +
    (ico
      ? `<span class="kpi-ico" aria-hidden="true"><svg viewBox="0 0 24 24">${icono(ico)}</svg></span>`
      : "") +
    "</div>" +
    `<div class="kpi-num num">${esc(cifra)}</div>` +
    `<div class="kpi-sub">${esc(sub)}</div>` +
    "</article>"
  );
}

/**
 * Tarjeta héroe: cifra grande y, debajo, el anillo con el porcentaje,
 * la barra y su pie.
 *
 * `porcentaje` es cuánto se llena la barra. Se recorta a 0–100: un
 * ahorro negativo daría una barra de ancho negativo, que el navegador
 * ignora, y un 140 % desbordaría el surco.
 *
 * `anillo` dibuja el disco con el porcentaje adentro (F20-T02, el
 * mockup aprobado). Es `null` cuando no hay porcentaje que mostrar
 * —ingresos en cero, por ejemplo— y entonces no se dibuja: un anillo
 * en cero diría que la tasa es cero, que es justo lo que la regla de
 * la tasa de ahorro no quiere decir.
 *
 * El pie admite dos formas, y son excluyentes: `pie` es una línea
 * sola, debajo de la barra (el ahorro del mes, el patrimonio);
 * `pieIzq`/`pieDer` son dos datos a los extremos. Sin ninguno de los
 * tres no se renderiza nada: un pie vacío igual sumaría el hueco de
 * su `margin-top`.
 *
 * @param {{etiqueta: string, cifra: string, sub?: string,
 *          porcentaje?: number, anillo?: number|null, pie?: string,
 *          pieIzq?: string, pieDer?: string, color?: string}} datos
 */
export function tarjetaHeroe({
  etiqueta,
  cifra,
  sub = "",
  porcentaje = 0,
  anillo = null,
  pie = "",
  pieIzq = "",
  pieDer = "",
  color: c,
}) {
  const ancho = Math.min(100, Math.max(0, Number(porcentaje) || 0));

  const pieHtml = pie
    ? `<span class="fin-pie">${esc(pie)}</span>`
    : pieIzq || pieDer
      ? `<span class="fin-foot"><span>${esc(pieIzq)}</span><span>${esc(pieDer)}</span></span>`
      : "";

  return (
    `<article class="kpi kpi--hero shell" style="--c:${color(c)}">` +
    `<div class="kpi-label">${esc(etiqueta)}</div>` +
    `<div class="kpi-num num">${esc(cifra)}</div>` +
    `<div class="kpi-sub">${esc(sub)}</div>` +
    // Todo el bloque de abajo es decoración: el porcentaje que dice el
    // anillo está también en el pie, y la cifra de arriba ya dice el
    // valor. Sin aria-hidden, el lector lee dos veces lo mismo.
    '<div class="kpi-aro" aria-hidden="true">' +
    anilloSvg(anillo) +
    '<span class="kpi-aro-g">' +
    '<span class="fin-track">' +
    `<i class="fin-fill" data-ancho="${ancho}"></i>` +
    "</span>" +
    pieHtml +
    "</span>" +
    "</div>" +
    "</article>"
  );
}

/** El disco de la tarjeta héroe: un anillo de 52 px con el porcentaje
 * entero adentro. `pathLength="100"` es lo que deja escribir el
 * `stroke-dasharray` en por ciento sin calcular la circunferencia.
 *
 * Se recorta a 0–100 por lo mismo que la barra, y se redondea al
 * entero: adentro del anillo no entran dos cifras y una coma. El
 * valor con decimal va en el pie. */
function anilloSvg(valor) {
  if (valor == null || Number.isNaN(Number(valor))) return "";
  const v = Math.min(100, Math.max(0, Number(valor)));
  const entero = Math.round(v);
  return (
    '<svg class="kpi-anillo" viewBox="0 0 40 40">' +
    '<circle cx="20" cy="20" r="15.9" fill="none" stroke="rgba(0,0,0,.25)" stroke-width="5"/>' +
    '<circle cx="20" cy="20" r="15.9" fill="none" stroke="currentColor" stroke-width="5" ' +
    `stroke-linecap="round" stroke-dasharray="${v} ${100 - v}" pathLength="100" ` +
    'transform="rotate(-90 20 20)"/>' +
    `<text x="20" y="22.6" text-anchor="middle">${entero}%</text>` +
    "</svg>"
  );
}

/**
 * Anima las barras de progreso que haya dentro de `raiz`.
 *
 * Se llama DESPUÉS de insertar el HTML. La barra nace en 0 y crece al
 * frame siguiente: puesta directo en su ancho, la transición no tiene
 * de dónde partir y aparece ya llena.
 */
export function animarBarras(raiz = document) {
  const barras = raiz.querySelectorAll(".fin-fill[data-ancho]");
  if (!barras.length) return;

  requestAnimationFrame(() => {
    barras.forEach((b) => {
      b.style.width = `${b.dataset.ancho}%`;
    });
  });
}

/**
 * Pinta una lista de tarjetas en un contenedor y arranca las barras.
 *
 * Las tarjetas se escriben de una sola vez y no una por una: con siete
 * asignaciones a `innerHTML` el navegador recalcula el layout siete
 * veces, y en un teléfono se ve el salto.
 */
export function pintarTarjetas(contenedor, tarjetas) {
  if (!contenedor) return;
  contenedor.innerHTML = tarjetas.join("");
  animarBarras(contenedor);
}

/**
 * Anima la cifra de un elemento desde 0 hasta `destino`, formateada
 * con `formatear` en cada cuadro — así el signo y el símbolo de pesos
 * ya están puestos durante toda la animación, no sólo al final.
 *
 * 900 ms, cúbica de salida (skill §6, "conteo de cifras").
 * `prefers-reduced-motion` la anula: se pinta el valor final directo,
 * sin pasos intermedios (skill, regla 6).
 */
export function animarCifra(el, destino, formatear, duracion = 900) {
  if (!el) return;

  const final = Number(destino) || 0;

  if (
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  ) {
    el.textContent = formatear(final);
    return;
  }

  // `window.performance`, no el global `performance` suelto: en los
  // módulos de prueba (jsdom) `requestAnimationFrame` manda su propio
  // reloj de `window`, y restar contra otro reloj daría un tiempo sin
  // sentido. En un navegador de verdad son el mismo objeto.
  const inicio = window.performance.now();
  (function cuadro(ahora) {
    const t = Math.min(1, (ahora - inicio) / duracion);
    const salida = 1 - (1 - t) ** 3; // cúbica de salida
    el.textContent = formatear(final * salida);
    if (t < 1) requestAnimationFrame(cuadro);
  })(inicio);
}

/**
 * Cuenta las cifras de una tanda de tarjetas ya pintadas, en el mismo
 * orden en que se pasaron a `pintarTarjetas`.
 *
 * Se llama DESPUÉS de `pintarTarjetas`, nunca antes: lee `.kpi-num` del
 * contenedor en orden de documento y empareja cada uno con su entrada
 * de `lista`. Una entrada `null` o `undefined` salta esa tarjeta —por
 * ejemplo, un "—" que no es una cifra para contar.
 *
 * @param {Element} contenedor
 * @param {Array<{valor: number, formatear: (n:number)=>string}|null|undefined>} lista
 */
export function animarCifras(contenedor, lista) {
  if (!contenedor) return;
  const nums = contenedor.querySelectorAll(".kpi-num");
  lista.forEach((item, i) => {
    if (item && nums[i]) animarCifra(nums[i], item.valor, item.formatear);
  });
}

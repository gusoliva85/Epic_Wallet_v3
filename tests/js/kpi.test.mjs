/* Pruebas de las tarjetas de indicador · F01-T09

   El criterio que importa más es de comportamiento y no de texto: «un
   dato con <script> se muestra como texto y no ejecuta nada». Eso sólo
   se verifica insertando el HTML en un documento de verdad y mirando
   si el script corrió. Una prueba que busque `esc(` en el código no
   sirve: `esc` puede estar llamado y mal. */

import { test, beforeEach, describe } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const AQUI = dirname(fileURLToPath(import.meta.url));
const RAIZ = resolve(AQUI, "..", "..");

function modulo(ruta) {
  return (
    "file:///" +
    resolve(RAIZ, "web", "src", "js", ...ruta).replace(/\\/g, "/") +
    `?t=${Math.random()}`
  );
}

async function montar() {
  const dom = new JSDOM(
    `<!doctype html><html><body><div class="kpi-grid stagger" id="rejilla"></div></body></html>`,
    {
      url: "https://epic-wallet.test/",
      // runScripts: para que un <script> inyectado SÍ pueda ejecutarse.
      // Sin esto, la prueba del escape pasaría porque jsdom no corre
      // scripts, no porque el escape funcione.
      runScripts: "dangerously",
      // pretendToBeVisual: trae requestAnimationFrame.
      pretendToBeVisual: true,
    },
  );

  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  // El módulo lo usa sin prefijo, como cualquier código de navegador:
  // ahí `window` y el global son lo mismo, y acá hay que darlo aparte.
  globalThis.requestAnimationFrame = (fn) =>
    dom.window.requestAnimationFrame(fn);

  const kpi = await import(modulo(["components", "kpi.js"]));
  const { esc } = await import(modulo(["format.js"]));
  return {
    dom,
    kpi,
    esc,
    rejilla: dom.window.document.getElementById("rejilla"),
  };
}

function esperar(dom, ms = 40) {
  return new Promise((listo) => dom.window.setTimeout(listo, ms));
}

describe("tarjetas de indicador", () => {
  beforeEach(() => {
    for (const k of ["window", "document", "requestAnimationFrame"])
      delete globalThis[k];
  });

  // ------------------------------------------------------- el escape

  test("un dato con script se muestra como texto y no ejecuta nada", async () => {
    // Criterio de aceptación de la tarea.
    const { dom, kpi, rejilla } = await montar();
    dom.window.ejecuto = false;

    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({
        etiqueta: "<script>window.ejecuto = true</script>",
        cifra: "$1",
        sub: "x",
      }),
    ]);
    await esperar(dom);

    assert.equal(dom.window.ejecuto, false, "el script se ejecutó");
    assert.equal(
      rejilla.querySelectorAll("script").length,
      0,
      "entró una etiqueta script en el documento",
    );
    assert.match(
      rejilla.querySelector(".kpi-label").textContent,
      /<script>/,
      "el dato tiene que verse como texto",
    );
  });

  test("el subtitulo tambien se escapa", async () => {
    // El ejemplo del documento técnico §12.4 escapa `label` y `value`
    // pero NO `sub`. Un subtítulo puede traer el nombre de una
    // categoría que escribió el usuario.
    const { dom, kpi, rejilla } = await montar();
    dom.window.ejecuto = false;
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({
        etiqueta: "Egresos",
        cifra: "$1",
        sub: '<img src=x onerror="window.ejecuto = true">',
      }),
    ]);
    await esperar(dom);
    assert.equal(dom.window.ejecuto, false);
    assert.equal(rejilla.querySelectorAll("img").length, 0);
  });

  test("la cifra tambien se escapa", async () => {
    // La cifra viene formateada del backend. Es un string como
    // cualquier otro: si no se escapa, es una puerta igual que el
    // subtítulo.
    const { dom, kpi, rejilla } = await montar();
    dom.window.ejecuto = false;
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({
        etiqueta: "Egresos",
        cifra: '<img src=x onerror="window.ejecuto = true">',
      }),
    ]);
    await esperar(dom);
    assert.equal(dom.window.ejecuto, false);
    assert.equal(rejilla.querySelectorAll("img").length, 0);
  });

  test("la etiqueta de la tarjeta heroe tambien se escapa", async () => {
    const { dom, kpi, rejilla } = await montar();
    dom.window.ejecuto = false;
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({
        etiqueta: '<img src=x onerror="window.ejecuto = true">',
        cifra: '<img src=y onerror="window.ejecuto = true">',
        sub: '<img src=z onerror="window.ejecuto = true">',
      }),
    ]);
    await esperar(dom);
    assert.equal(dom.window.ejecuto, false);
    assert.equal(rejilla.querySelectorAll("img").length, 0);
  });

  test("el pie de la tarjeta heroe tambien se escapa", async () => {
    const { dom, kpi, rejilla } = await montar();
    dom.window.ejecuto = false;
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({
        etiqueta: "Ahorro",
        cifra: "$1",
        pieIzq: '<img src=x onerror="window.ejecuto = true">',
        pieDer: '<img src=y onerror="window.ejecuto = true">',
      }),
    ]);
    await esperar(dom);
    assert.equal(dom.window.ejecuto, false);
    assert.equal(rejilla.querySelectorAll("img").length, 0);
  });

  test("una comilla no rompe el atributo de al lado", async () => {
    // Escapando sólo &<> el texto entre etiquetas queda bien, pero una
    // comilla dentro de un atributo lo cierra y abre otro.
    const { esc } = await montar();
    assert.equal(esc('a"b'), "a&quot;b");
    assert.equal(esc("a'b"), "a&#39;b");
  });

  test("el cero no desaparece", async () => {
    // Con `|| ""` en lugar de `?? ""`, un importe de 0 se convierte en
    // cadena vacía. En finanzas, un 0 que desaparece es un error
    // difícil de ver.
    const { esc } = await montar();
    assert.equal(esc(0), "0");
    assert.equal(esc(null), "");
    assert.equal(esc(undefined), "");
  });

  // ------------------------------------------------------ las variantes

  test("la tarjeta de metrica trae etiqueta, cifra, subtitulo e icono", async () => {
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({
        etiqueta: "Ingresos",
        cifra: "$2.105.000",
        sub: "4 movimientos",
        color: "inc",
        icono: "sube",
      }),
    ]);
    const t = rejilla.querySelector(".kpi");
    assert.equal(t.querySelector(".kpi-label").textContent, "Ingresos");
    assert.equal(t.querySelector(".kpi-num").textContent, "$2.105.000");
    assert.equal(t.querySelector(".kpi-sub").textContent, "4 movimientos");
    assert.ok(t.querySelector(".kpi-ico svg path"), "falta el icono");
  });

  test("la tarjeta heroe trae barra y pie de dos datos", async () => {
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({
        etiqueta: "Ahorro del mes",
        cifra: "$1.284.300",
        porcentaje: 61,
        pieIzq: "Ingresos",
        pieDer: "Egresos",
      }),
    ]);
    const t = rejilla.querySelector(".kpi--hero");
    assert.ok(t, "falta la variante héroe");
    assert.ok(t.querySelector(".fin-track .fin-fill"), "falta la barra");
    assert.equal(t.querySelectorAll(".fin-foot span").length, 2);
  });

  test("sin pie, no se renderiza el hueco del pie", async () => {
    // La de "Ahorro del mes" no lleva pie: ingreso y egreso ya están
    // en las tarjetas de color de abajo. Sin esto, `.fin-foot` se
    // renderizaría vacío igual, y su `margin-top` dejaría un hueco en
    // blanco debajo de la barra.
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({ etiqueta: "Ahorro del mes", cifra: "$1", porcentaje: 61 }),
    ]);
    const t = rejilla.querySelector(".kpi--hero");
    assert.equal(t.querySelector(".fin-foot"), null);
  });

  test("con un solo lado del pie, igual se muestra", async () => {
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({ etiqueta: "x", cifra: "$1", pieIzq: "Invertido $1" }),
    ]);
    assert.ok(rejilla.querySelector(".fin-foot"));
  });

  test("la cifra lleva ancho fijo", async () => {
    // Sin `num`, al actualizarse un importe las cifras cambian de ancho
    // y la tarjeta entera se mueve.
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({ etiqueta: "x", cifra: "$1" }),
    ]);
    assert.ok(rejilla.querySelector(".kpi-num.num"));
  });

  test("el icono decorativo no lo lee el lector", async () => {
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({ etiqueta: "x", cifra: "$1", icono: "sube" }),
    ]);
    assert.equal(
      rejilla.querySelector(".kpi-ico").getAttribute("aria-hidden"),
      "true",
    );
  });

  test("el anillo y la barra no los lee el lector", async () => {
    // La cifra de arriba ya dice el valor y el pie dice el porcentaje
    // con todas las letras: un anillo y un progreso anunciados aparte
    // repiten lo mismo tres veces.
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({ etiqueta: "x", cifra: "$1", porcentaje: 50, anillo: 50 }),
    ]);
    assert.equal(
      rejilla.querySelector(".kpi-aro").getAttribute("aria-hidden"),
      "true",
    );
  });

  test("sin porcentaje no se dibuja el anillo", async () => {
    // Un anillo vacío se lee como "cero por ciento". Cuando no hay
    // tasa —ingresos en cero—, no hay anillo.
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({ etiqueta: "x", cifra: "$1", anillo: null }),
    ]);
    assert.equal(rejilla.querySelector(".kpi-anillo"), null);
  });

  test("el anillo redondea al entero y se recorta a 0–100", async () => {
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({ etiqueta: "x", cifra: "$1", anillo: 24.4 }),
      kpi.tarjetaHeroe({ etiqueta: "y", cifra: "$1", anillo: 180 }),
    ]);
    const anillos = rejilla.querySelectorAll(".kpi-anillo");
    assert.equal(anillos[0].querySelector("text").textContent, "24%");
    assert.equal(anillos[1].querySelector("text").textContent, "100%");
  });

  test("una tarjeta sin icono no deja el hueco", async () => {
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({ etiqueta: "x", cifra: "$1" }),
    ]);
    assert.equal(rejilla.querySelector(".kpi-ico"), null);
  });

  test("un icono que no existe no escribe undefined", async () => {
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({ etiqueta: "x", cifra: "$1", icono: "no-existe" }),
    ]);
    assert.ok(!rejilla.innerHTML.includes("undefined"));
  });

  // --------------------------------------------------------- el color

  test("el color sale de una lista cerrada", async () => {
    // El valor termina dentro de un atributo `style` y la política de
    // contenido admite estilos en línea: con un color libre, un dato
    // del servidor podría inyectar CSS.
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({
        etiqueta: "x",
        cifra: "$1",
        color: "red; background:url(http://malo/)",
      }),
    ]);
    const estilo = rejilla.querySelector(".kpi").getAttribute("style");
    assert.ok(!estilo.includes("malo"), `entró CSS ajeno: ${estilo}`);
    assert.match(
      estilo,
      /var\(--color-accent\)/,
      "un color inválido cae en el acento",
    );
  });

  test("los colores validos se resuelven a un token", async () => {
    const { kpi, rejilla } = await montar();
    for (const c of kpi.COLORES_VALIDOS) {
      kpi.pintarTarjetas(rejilla, [
        kpi.tarjetaMetrica({ etiqueta: "x", cifra: "$1", color: c }),
      ]);
      const estilo = rejilla.querySelector(".kpi").getAttribute("style");
      assert.match(
        estilo,
        /^--c: ?var\(--color-[\w-]+\)$/,
        `color ${c}: ${estilo}`,
      );
    }
  });

  // ------------------------------------------------------- la barra crece

  test("la barra nace en cero y crece al frame siguiente", async () => {
    // Puesta directo en su ancho, la transición no tiene de dónde
    // partir y la barra aparece ya llena.
    const { dom, kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({ etiqueta: "x", cifra: "$1", porcentaje: 61 }),
    ]);
    const barra = rejilla.querySelector(".fin-fill");
    assert.equal(
      barra.style.width,
      "",
      "la barra no tiene que nacer con ancho",
    );
    await esperar(dom);
    assert.equal(barra.style.width, "61%");
  });

  test("un porcentaje fuera de rango se recorta", async () => {
    // Un ahorro negativo daría una barra de ancho negativo y un 140 %
    // desbordaría el surco.
    const { dom, kpi, rejilla } = await montar();
    for (const [pedido, esperado] of [
      [-30, "0%"],
      [140, "100%"],
      [61.5, "61.5%"],
    ]) {
      kpi.pintarTarjetas(rejilla, [
        kpi.tarjetaHeroe({ etiqueta: "x", cifra: "$1", porcentaje: pedido }),
      ]);
      await esperar(dom);
      assert.equal(rejilla.querySelector(".fin-fill").style.width, esperado);
    }
  });

  test("un porcentaje que no es numero no rompe la barra", async () => {
    const { dom, kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({ etiqueta: "x", cifra: "$1", porcentaje: "no" }),
    ]);
    await esperar(dom);
    assert.equal(rejilla.querySelector(".fin-fill").style.width, "0%");
  });

  // ---------------------------------------------------- el conteo de cifras

  describe("animarCifra / animarCifras · F05-T07", () => {
    test("nace en cero y termina exactamente en el valor final, formateado", async () => {
      const { dom, kpi, rejilla } = await montar();
      rejilla.innerHTML = '<div class="kpi-num"></div>';
      const el = rejilla.querySelector(".kpi-num");

      kpi.animarCifra(el, 1234, (n) => `$${Math.round(n)}`);
      // Recién llamada: el primer cuadro todavía no corrió.
      assert.notEqual(el.textContent, "$1234");

      await esperar(dom, 1000);
      assert.equal(el.textContent, "$1234");
    });

    test("un destino negativo mantiene el signo durante toda la animación", async () => {
      const { dom, kpi, rejilla } = await montar();
      rejilla.innerHTML = '<div class="kpi-num"></div>';
      const el = rejilla.querySelector(".kpi-num");

      kpi.animarCifra(el, -500, (n) => (n < 0 ? "−" : "") + `$${Math.round(Math.abs(n))}`);
      await esperar(dom, 1000);
      assert.equal(el.textContent, "−$500");
    });

    test("con movimiento reducido pinta el valor final directo, sin pasos", async () => {
      const { kpi, rejilla } = await montar();
      // `window` es el mismo objeto que `dom.window`: mutar uno alcanza.
      window.matchMedia = () => ({ matches: true });
      rejilla.innerHTML = '<div class="kpi-num"></div>';
      const el = rejilla.querySelector(".kpi-num");

      kpi.animarCifra(el, 500, (n) => `$${Math.round(n)}`);
      // Sin esperar ningún cuadro: con movimiento reducido no hay RAF de por medio.
      assert.equal(el.textContent, "$500");
    });

    test("animarCifras empareja cada .kpi-num con su entrada, en el mismo orden", async () => {
      const { kpi, rejilla } = await montar();
      window.matchMedia = () => ({ matches: true }); // sin esperar 900ms
      kpi.pintarTarjetas(rejilla, [
        kpi.tarjetaMetrica({ etiqueta: "a", cifra: "$0" }),
        kpi.tarjetaMetrica({ etiqueta: "b", cifra: "$0" }),
      ]);
      kpi.animarCifras(rejilla, [
        { valor: 10, formatear: (n) => `$${Math.round(n)}` },
        { valor: 20, formatear: (n) => `$${Math.round(n)}` },
      ]);
      const nums = [...rejilla.querySelectorAll(".kpi-num")];
      assert.equal(nums[0].textContent, "$10");
      assert.equal(nums[1].textContent, "$20");
    });

    test("una entrada null o undefined salta esa tarjeta, sin tocarla", async () => {
      // El "—" de una tarjeta que no tiene nada que contar (por ejemplo,
      // "Gasto de hoy" mirando un mes que no es el actual) no es un
      // número: contarlo escribiría encima el "—" con basura.
      const { kpi, rejilla } = await montar();
      window.matchMedia = () => ({ matches: true });
      kpi.pintarTarjetas(rejilla, [
        kpi.tarjetaMetrica({ etiqueta: "a", cifra: "—" }),
        kpi.tarjetaMetrica({ etiqueta: "b", cifra: "$0" }),
      ]);
      kpi.animarCifras(rejilla, [
        null,
        { valor: 20, formatear: (n) => `$${Math.round(n)}` },
      ]);
      const nums = [...rejilla.querySelectorAll(".kpi-num")];
      assert.equal(nums[0].textContent, "—", "no tenía que tocar la que es null");
      assert.equal(nums[1].textContent, "$20");
    });

    test("sin contenedor o sin elemento, no rompe", async () => {
      const { kpi } = await montar();
      assert.doesNotThrow(() => kpi.animarCifra(null, 10, (n) => `${n}`));
      assert.doesNotThrow(() => kpi.animarCifras(null, [{ valor: 1, formatear: (n) => `${n}` }]));
    });
  });

  // ------------------------------------------------------- la muestra

  test("vistas.js ya no escribe tarjetas de muestra en #kpis-inicio", async () => {
    // F05-T07 le dio ese contenedor a dashboard.js, con datos reales de
    // GET /api/dashboard. Guarda de regresión: si alguien reintroduce
    // el bloque de muestra acá, las dos fuentes de datos competirían
    // por el mismo contenedor.
    const { rejilla } = await inicio();
    assert.equal(rejilla.innerHTML, "");
  });

  /** Monta la vista de inicio: las vistas pintan en varios
      contenedores, así que hay que darle todos los que toca. */
  async function inicio() {
    const b = await montar();
    b.rejilla.id = "kpis-inicio";
    for (const id of [
      "pie-diario",
      "pie-seis",
      "categorias-inicio",
      "avisos-inicio",
    ]) {
      const d = b.dom.window.document.createElement("div");
      d.id = id;
      b.dom.window.document.body.append(d);
    }
    const vistas = await import(modulo(["views", "vistas.js"]));
    vistas.pintarVistas();
    await esperar(b.dom);
    return b;
  }

  // ------------------------------- las cuatro tarjetas teñidas del catálogo
  //
  // F20-T01: eran tarjetas de color sólido con el signo pesos de fondo
  // y el símbolo de la esquina. Pasaron a ser material teñido: el color
  // entra por `--c-card` y el CSS lo usa en la superficie y en el punto
  // de la etiqueta. Las pruebas del signo y del símbolo se fueron con
  // ellos — fijaban un diseño que ya no es el del sistema.

  test("las tarjetas teñidas del catalogo son identificables", async () => {
    const { kpi, rejilla } = await montar();
    for (const nombre of kpi.TARJETAS_VALIDAS) {
      kpi.pintarTarjetas(rejilla, [
        kpi.tarjetaMetrica({ etiqueta: nombre, cifra: "$1", tarjeta: nombre }),
      ]);
      const t = rejilla.querySelector(".kpi");
      assert.ok(t.classList.contains("kpi-color"), `${nombre}: no es tarjeta teñida`);
      assert.match(
        t.getAttribute("style") ?? "",
        /--c-card/,
        `${nombre}: falta el color del dato`,
      );
    }
  });

  test("ninguna tarjeta del catalogo repite el color del dato", async () => {
    // Con el mismo color dejarían de identificar nada, que es para lo
    // que están. Cada una nombra su propio token.
    const { kpi, rejilla } = await montar();
    const fondos = [];
    for (const nombre of kpi.TARJETAS_VALIDAS) {
      kpi.pintarTarjetas(rejilla, [
        kpi.tarjetaMetrica({ etiqueta: nombre, cifra: "$1", tarjeta: nombre }),
      ]);
      fondos.push(rejilla.querySelector(".kpi").getAttribute("style"));
    }
    assert.equal(new Set(fondos).size, kpi.TARJETAS_VALIDAS.length, "hay colores repetidos");
  });

  test("el fondo sale del catalogo, no de un valor libre", async () => {
    // Termina dentro de un atributo `style` y la política del sitio
    // admite estilos en línea: un valor libre sería CSS inyectable.
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({
        etiqueta: "x",
        cifra: "$1",
        tarjeta: "red; background:url(http://malo/)",
      }),
    ]);
    const t = rejilla.querySelector(".kpi");
    assert.ok(
      !t.classList.contains("kpi-color"),
      "aceptó una tarjeta inventada",
    );
    assert.ok(!rejilla.innerHTML.includes("malo"));
  });

  test("los cuatro nombres del catalogo se resuelven a un token", async () => {
    const { kpi, rejilla } = await montar();
    for (const nombre of kpi.TARJETAS_VALIDAS) {
      kpi.pintarTarjetas(rejilla, [
        kpi.tarjetaMetrica({ etiqueta: "x", cifra: "$1", tarjeta: nombre }),
      ]);
      const estilo = rejilla.querySelector(".kpi").getAttribute("style");
      assert.match(
        estilo,
        /^--c-card: ?var\(--color-card-\w+\)$/,
        `${nombre}: ${estilo}`,
      );
    }
  });

  test("la tarjeta teñida no deja nada decorativo en el DOM", async () => {
    // El punto de la etiqueta lo pone el CSS con un ::before: es
    // decoración y no tiene que existir como nodo ni leerse en voz
    // alta. El signo pesos y el símbolo de la esquina, que sí eran
    // nodos, se fueron en F20-T01.
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({ etiqueta: "Ingresos", cifra: "$1", tarjeta: "inc" }),
    ]);
    const t = rejilla.querySelector(".kpi");
    assert.equal(t.querySelector(".kpi-peso"), null);
    assert.equal(t.querySelector(".kpi-glifo"), null);
    assert.equal(t.querySelector("[aria-hidden]"), null);
  });

  test("la tarjeta teñida no lleva ademas el cuadradito de icono", async () => {
    // El tinte y el punto ya identifican la tarjeta.
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({
        etiqueta: "x",
        cifra: "$1",
        tarjeta: "inc",
        icono: "sube",
      }),
    ]);
    assert.equal(rejilla.querySelector(".kpi-ico"), null);
  });

  test("sin tarjeta sigue siendo la pieza de material de siempre", async () => {
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaMetrica({
        etiqueta: "x",
        cifra: "$1",
        color: "inc",
        icono: "sube",
      }),
    ]);
    const t = rejilla.querySelector(".kpi");
    assert.ok(!t.classList.contains("kpi-color"));
    assert.ok(
      t.querySelector(".kpi-ico"),
      "la pieza sin teñir sí lleva el cuadradito",
    );
  });

  test("la heroe no se vuelve tarjeta teñida", async () => {
    // La héroe es la única superficie MACIZA del sistema (F20-T01) y
    // las cuatro métricas son material teñido: el contraste entre ellas
    // es parte del diseño, así que la héroe no puede entrar en el
    // catálogo. `tarjetaHeroe` no tiene parámetro `tarjeta`; esto es
    // una guarda de regresión por si alguna vez lo gana.
    const { kpi, rejilla } = await montar();
    kpi.pintarTarjetas(rejilla, [
      kpi.tarjetaHeroe({ etiqueta: "Ahorro del mes", cifra: "$1" }),
    ]);
    const heroe = rejilla.querySelector(".kpi--hero");
    assert.ok(!heroe.classList.contains("kpi-color"));
    assert.equal(heroe.getAttribute("style")?.includes("--c-card"), false);
  });
});

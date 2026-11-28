/* ============================================================
   Service worker de Epic Wallet
   Referencia: 02_Documento_Tecnico.md §15.1

   ESTADO: F00-T11 · mínimo a propósito, con un agregado de F20-T02.
   TODAVÍA NO CACHEA NADA: las estrategias de caché (red primero para
   el HTML, revalidación en segundo plano para los estáticos, y nunca
   encolar escrituras) se implementan en F15-T01. Lo único que hace
   además de instalarse es FORZAR la red para el HTML y los módulos,
   que es lo contrario de cachear — ver el manejador de 'fetch'.

   Que no cachee es deliberado: un service worker a medias que
   guarde respuestas sin una estrategia de invalidación deja
   versiones viejas pegadas y es más difícil de depurar que no
   tener ninguno.
   ============================================================ */

const VERSION = "0.2.0";

self.addEventListener("install", () => {
  // Tomar el control sin esperar a que se cierren las pestañas viejas.
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    (async () => {
      // Limpieza preventiva: si una versión futura dejó cachés y se
      // vuelve atrás, no quedan colgados.
      const nombres = await caches.keys();
      await Promise.all(
        nombres.filter((n) => !n.endsWith(VERSION)).map((n) => caches.delete(n)),
      );
      await self.clients.claim();
    })(),
  );
});

/* ------------------------------------------------------------------
   El único manejador de 'fetch' que hay, y NO es una caché.

   Sigue sin cachear nada (eso es F15-T01). Lo que hace es lo
   contrario: obliga a que el HTML y los módulos de JavaScript se
   pidan a la red, sin pasar por la caché HTTP del navegador.

   Por qué existe. Esos archivos se publican siempre con el mismo
   nombre y, hasta el 2026-11-28, el borde los servía sin ninguna
   cabecera de caché; Chrome entonces aplica su caching heurístico y
   se queda con la versión vieja el tiempo que quiere. El resultado
   fue un teléfono con el CSS nuevo y el JavaScript de la versión
   anterior: tarjetas rotas, bloques negros y la tarjeta héroe sin su
   anillo. El arreglo de fondo es la cabecera `Cache-Control` del
   Caddyfile, que ya está puesta. Esto es lo que rescata a un cliente
   que YA tiene la versión vieja guardada: la cabecera nueva no sirve
   de nada si el navegador no vuelve a preguntar.

   Sólo GET, sólo del mismo origen, sólo el HTML y `/src/`. La API no
   pasa por acá —se sirve con `no-store` desde el borde— y las fuentes
   y los iconos se siguen cacheando como corresponde.

   Si la red falla, se reintenta la petición normal: sin conexión, una
   respuesta vieja es mejor que una pantalla en blanco.
   ------------------------------------------------------------------ */
self.addEventListener("fetch", (evento) => {
  const pedido = evento.request;
  if (pedido.method !== "GET") return;

  const url = new URL(pedido.url);
  if (url.origin !== self.location.origin) return;

  const esDelShell =
    pedido.mode === "navigate" ||
    url.pathname === "/" ||
    url.pathname === "/index.html" ||
    url.pathname.startsWith("/src/");
  if (!esDelShell) return;

  evento.respondWith(
    fetch(url.href, { cache: "reload", credentials: "same-origin" }).catch(() =>
      fetch(pedido),
    ),
  );
});

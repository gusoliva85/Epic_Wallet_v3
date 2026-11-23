/* Pruebas de autenticación · F17-T03 (reemplazan las de F02-T08)
   Se corren con `npm test` y también desde pytest, que las invoca en
   tests/unit/test_auth_js.py para que `pytest` siga siendo el único
   comando que hay que recordar.

   QUÉ SE PRUEBA ACÁ Y POR QUÉ

   Hasta F17-T02 esto envolvía `@supabase/auth-js` y las pruebas
   usaban la librería de verdad con la red falseada: lo que podía
   fallar era nuestra configuración, no la librería.

   Ahora el comportamiento es nuestro, así que lo que se prueba es el
   comportamiento. Son cuatro cosas, y ninguna se ve mirando la
   pantalla hasta el día que falla:

   1. La sesión sobrevive a recargar y a cerrar la aplicación.
   2. El token se renueva solo antes de vencer.
   3. **Una sola renovación en vuelo** aunque salgan dos peticiones
      juntas. Con tokens rotatorios, dos renovaciones simultáneas no
      son un desperdicio: la segunda llega con un token ya quemado, el
      servidor lo toma por robado y corta la sesión. Abrir dos
      pantallas a la vez cerraría la sesión.
   4. Cerrar sesión en una pestaña cierra la otra.

   La red se falsea; `localStorage` es el de jsdom, real. */

import { test, describe, after } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const AQUI = dirname(fileURLToPath(import.meta.url));
const RAIZ = resolve(AQUI, "..", "..");
const CLAVE_DE_SESION = "epic-wallet-auth";

const USUARIO = { id: "11111111-2222-3333-4444-555555555555", email: "gustavo@example.com" };

// ===================================================================
//  Un /api/auth de mentira
// ===================================================================

/** La respuesta con la forma exacta de `RespuestaDeSesion`. */
function respuestaDeSesion({ token = "acceso-1", refresh = "renov-1", vence_en = 3600 } = {}) {
  return {
    access_token: token,
    refresh_token: refresh,
    expires_in: vence_en,
    token_type: "bearer",
    user: USUARIO,
  };
}

/** Lo que guarda el módulo. `expires_at` en SEGUNDOS, como lo escribe
 * `aGuardado()`: con milisegundos la cuenta da setenta mil años de
 * validez y la prueba de renovación pasaría sin renovar nada. */
function guardado({ token = "acceso-1", refresh = "renov-1", dentroDe = 3600 } = {}) {
  return {
    access_token: token,
    refresh_token: refresh,
    expires_at: Math.floor(Date.now() / 1000) + dentroDe,
    user: USUARIO,
  };
}

/** El servidor de mentira. Guarda qué le pidieron, que es la mitad de
 * lo que las pruebas necesitan comprobar. */
function servidor() {
  const estado = {
    llamadas: [],
    /** patrón de ruta → (cuerpo) => [codigo, json] */
    respuestas: new Map(),
    contadorDeRefresh: 0,
    /** Demora artificial, para provocar dos peticiones en vuelo. */
    demora: 0,
  };

  estado.fetch = async (entrada, opciones = {}) => {
    const url = String(entrada?.url ?? entrada);
    const metodo = (opciones.method ?? "GET").toUpperCase();
    let cuerpo = null;
    try {
      cuerpo = opciones.body ? JSON.parse(opciones.body) : null;
    } catch {
      cuerpo = opciones.body ?? null;
    }
    estado.llamadas.push({ url, metodo, cuerpo, cabeceras: opciones.headers ?? {} });

    if (estado.demora) await new Promise((r) => setTimeout(r, estado.demora));

    const responder = (codigo, datos) =>
      new Response(codigo === 204 ? null : JSON.stringify(datos), {
        status: codigo,
        headers: { "Content-Type": "application/json" },
      });

    for (const [patron, manejar] of estado.respuestas) {
      if (url.includes(patron)) {
        const [codigo, datos] = manejar(cuerpo, url);
        return responder(codigo, datos);
      }
    }

    if (url.includes("/api/auth/refresh")) {
      estado.contadorDeRefresh += 1;
      return responder(
        200,
        respuestaDeSesion({
          token: `acceso-renovado-${estado.contadorDeRefresh}`,
          refresh: `renov-${estado.contadorDeRefresh + 1}`,
        }),
      );
    }
    if (url.includes("/api/auth/login")) return responder(200, respuestaDeSesion());
    if (url.includes("/api/auth/signup")) return responder(201, respuestaDeSesion());
    if (url.includes("/api/auth/logout")) return responder(204, null);
    if (url.includes("/api/auth/password")) return responder(200, respuestaDeSesion());
    return responder(404, { error: { code: "NOT_FOUND", message: "no configurado" } });
  };

  return estado;
}

/** Un error con la forma del §9.3. */
function errorDeApi(code, message) {
  return { error: { code, message } };
}

// ===================================================================
//  Montaje
// ===================================================================

const aLimpiar = [];

async function montar({ almacenado = null, red = servidor() } = {}) {
  const dom = new JSDOM("<!doctype html><html><body></body></html>", {
    url: "https://13-140-36-93.sslip.io/",
  });

  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.location = dom.window.location;
  globalThis.localStorage = dom.window.localStorage;
  globalThis.sessionStorage = dom.window.sessionStorage;
  globalThis.addEventListener = dom.window.addEventListener.bind(dom.window);
  globalThis.fetch = red.fetch;
  globalThis.EPIC_WALLET = undefined;

  // Una sesión ya guardada: es lo que hay después de recargar.
  if (almacenado) {
    dom.window.localStorage.setItem(CLAVE_DE_SESION, JSON.stringify(almacenado));
  }

  // Instancia nueva del módulo en cada prueba: tiene estado propio
  // —la renovación en vuelo, los oyentes— y guardaría el de la
  // anterior.
  const url =
    "file:///" +
    resolve(RAIZ, "web", "src", "js", "auth.js").replace(/\\/g, "/") +
    `?t=${Math.random()}`;
  const auth = await import(url);

  aLimpiar.push(dom.window);
  return { auth, dom, red };
}

after(() => {
  // jsdom deja temporizadores propios; sin esto `node --test` no
  // termina nunca y desde afuera parece una prueba lenta.
  for (const v of aLimpiar) {
    try {
      v.close();
    } catch {
      /* Ya cerrada. */
    }
  }
});

// ===================================================================

describe("la sesión sobrevive", () => {
  test("entrar la deja guardada en localStorage", async () => {
    const { auth, dom } = await montar();

    const r = await auth.entrar("gustavo@example.com", "una-clave-larga");
    assert.equal(r.ok, true);
    assert.deepEqual(r.usuario, USUARIO);

    const crudo = dom.window.localStorage.getItem(CLAVE_DE_SESION);
    assert.ok(crudo, "no quedó nada guardado: recargar cerraría la sesión");
    assert.equal(JSON.parse(crudo).refresh_token, "renov-1");
  });

  test("al arrancar con una sesión guardada, ya hay sesión", async () => {
    // Es el caso de recargar la página o volver a abrir la aplicación
    // instalada: no se llama a nada, se lee lo que quedó.
    const { auth, red } = await montar({ almacenado: guardado() });

    assert.equal(await auth.haySesion(), true);
    assert.deepEqual(await auth.usuarioActual(), USUARIO);
    assert.equal(red.llamadas.length, 0, "leer la sesión guardada no sale a la red");
  });

  test("sin nada guardado no hay sesión ni token", async () => {
    const { auth } = await montar();
    assert.equal(await auth.haySesion(), false);
    assert.equal(await auth.token(), null);
    assert.equal(await auth.cabeceras(), null);
  });

  test("una entrada corrupta se trata como «no hay sesión»", async () => {
    // Una versión vieja del formato, o algo que alguien tocó a mano.
    // Lo que no puede pasar es que la aplicación no arranque.
    const { auth, dom } = await montar();
    dom.window.localStorage.setItem(CLAVE_DE_SESION, "{ esto no es json");
    assert.equal(await auth.haySesion(), false);

    dom.window.localStorage.setItem(CLAVE_DE_SESION, JSON.stringify({ user: USUARIO }));
    assert.equal(await auth.haySesion(), false);
  });
});

describe("el token se renueva solo", () => {
  test("un token con vida por delante se devuelve tal cual", async () => {
    const { auth, red } = await montar({ almacenado: guardado({ dentroDe: 3600 }) });

    assert.equal(await auth.token(), "acceso-1");
    assert.equal(red.contadorDeRefresh, 0, "renovó sin necesidad");
  });

  test("un token a punto de vencer se renueva antes de devolverlo", async () => {
    // 30 segundos es menos que el margen de 60: una petición que
    // saliera con ese token podría llegar vencida.
    const { auth, red } = await montar({ almacenado: guardado({ dentroDe: 30 }) });

    assert.equal(await auth.token(), "acceso-renovado-1");
    assert.equal(red.contadorDeRefresh, 1);
  });

  test("un token ya vencido se renueva", async () => {
    const { auth } = await montar({ almacenado: guardado({ dentroDe: -100 }) });
    assert.equal(await auth.token(), "acceso-renovado-1");
  });

  test("la renovación guarda el par nuevo, no el viejo", async () => {
    const { auth, dom } = await montar({ almacenado: guardado({ dentroDe: -1 }) });
    await auth.token();

    const s = JSON.parse(dom.window.localStorage.getItem(CLAVE_DE_SESION));
    assert.equal(s.access_token, "acceso-renovado-1");
    assert.equal(s.refresh_token, "renov-2", "no rotó el token de renovación");
  });

  test("DOS peticiones juntas disparan UNA sola renovación", async () => {
    /* El criterio de aceptación, y la pieza que no se puede sacar.

       Con tokens rotatorios, dos renovaciones simultáneas no son un
       desperdicio: la primera quema el token, la segunda llega con uno
       ya usado, el servidor lo toma por robado y corta la familia
       entera. O sea, abrir dos pantallas a la vez cerraría la sesión. */
    const red = servidor();
    red.demora = 20; // para que las dos estén en vuelo de verdad
    const { auth } = await montar({ almacenado: guardado({ dentroDe: -1 }), red });

    const [a, b] = await Promise.all([auth.token(), auth.token()]);

    assert.equal(red.contadorDeRefresh, 1, "pidió renovar dos veces: cortaría la sesión");
    assert.equal(a, b);
    assert.equal(a, "acceso-renovado-1");
  });

  test("después de renovar, la siguiente vez no vuelve a renovar", async () => {
    const { auth, red } = await montar({ almacenado: guardado({ dentroDe: -1 }) });
    await auth.token();
    await auth.token();
    assert.equal(red.contadorDeRefresh, 1);
  });

  test("si el servidor rechaza la renovación, la sesión se borra", async () => {
    const red = servidor();
    red.respuestas.set("/api/auth/refresh", () => [
      401,
      errorDeApi("UNAUTHENTICATED", "La sesión no es válida."),
    ]);
    const { auth, dom } = await montar({ almacenado: guardado({ dentroDe: -1 }), red });

    assert.equal(await auth.token(), null);
    assert.equal(dom.window.localStorage.getItem(CLAVE_DE_SESION), null);
  });

  test("sin red NO se borra la sesión", async () => {
    /* El token de renovación sigue siendo bueno y lo único que pasó es
       que no hay internet. Borrarla mandaría a la pantalla de ingreso a
       alguien que simplemente entró al subte. */
    const red = servidor();
    red.fetch = async () => {
      throw new TypeError("Failed to fetch");
    };
    const { auth, dom } = await montar({ almacenado: guardado({ dentroDe: -1 }), red });

    assert.equal(await auth.token(), null);
    assert.ok(
      dom.window.localStorage.getItem(CLAVE_DE_SESION),
      "borró la sesión por un corte de red",
    );
  });

  test("cabeceras() arma el Bearer", async () => {
    const { auth } = await montar({ almacenado: guardado() });
    assert.deepEqual(await auth.cabeceras(), { Authorization: "Bearer acceso-1" });
  });
});

describe("salir", () => {
  test("borra lo guardado y avisa al servidor con el token de renovación", async () => {
    const { auth, dom, red } = await montar({ almacenado: guardado() });

    await auth.salir();

    assert.equal(dom.window.localStorage.getItem(CLAVE_DE_SESION), null);
    const logout = red.llamadas.find((l) => l.url.includes("/logout"));
    assert.ok(logout, "no avisó al servidor: la sesión seguiría viva allá");
    assert.equal(logout.cuerpo.refresh_token, "renov-1");
  });

  test("si el servidor no contesta, la sesión local se borra igual", async () => {
    /* Un «cerrar sesión» que falla y deja al usuario adentro es peor
       que uno que cierra de más. */
    const red = servidor();
    red.fetch = async () => {
      throw new TypeError("Failed to fetch");
    };
    const { auth, dom } = await montar({ almacenado: guardado(), red });

    await auth.salir();
    assert.equal(dom.window.localStorage.getItem(CLAVE_DE_SESION), null);
  });
});

describe("las pestañas no se pisan", () => {
  test("cerrar sesión en otra pestaña avisa en esta", async () => {
    const { auth, dom } = await montar({ almacenado: guardado() });

    const avisos = [];
    auth.alCambiarLaSesion((estado) => avisos.push(estado));

    // Así se ve desde esta pestaña lo que hizo la otra: el navegador
    // manda `storage` SÓLO a las demás, nunca a la que escribió.
    dom.window.localStorage.removeItem(CLAVE_DE_SESION);
    const evento = new dom.window.StorageEvent("storage", {
      key: CLAVE_DE_SESION,
      newValue: null,
    });
    dom.window.dispatchEvent(evento);

    assert.equal(avisos.length, 1);
    assert.equal(avisos[0].hay, false);
    assert.equal(avisos[0].usuario, null);
  });

  test("un cambio de OTRA clave del almacenamiento no molesta", async () => {
    const { auth, dom } = await montar({ almacenado: guardado() });
    const avisos = [];
    auth.alCambiarLaSesion((estado) => avisos.push(estado));

    dom.window.dispatchEvent(
      new dom.window.StorageEvent("storage", { key: "epic-wallet-tema", newValue: "oscuro" }),
    );

    assert.equal(avisos.length, 0);
  });

  test("entrar y salir avisan en esta misma pestaña", async () => {
    const { auth } = await montar();
    const avisos = [];
    auth.alCambiarLaSesion((estado) => avisos.push(estado.hay));

    await auth.entrar("gustavo@example.com", "una-clave-larga");
    await auth.salir();

    assert.deepEqual(avisos, [true, false]);
  });

  test("dejar de escuchar funciona", async () => {
    const { auth } = await montar();
    const avisos = [];
    const dejar = auth.alCambiarLaSesion(() => avisos.push(1));
    dejar();
    await auth.entrar("gustavo@example.com", "una-clave-larga");
    assert.equal(avisos.length, 0);
  });

  test("un oyente que explota no rompe a los demás", async () => {
    const { auth } = await montar();
    const avisos = [];
    auth.alCambiarLaSesion(() => {
      throw new Error("este oyente está roto");
    });
    auth.alCambiarLaSesion(() => avisos.push(1));

    await auth.entrar("gustavo@example.com", "una-clave-larga");
    assert.equal(avisos.length, 1);
  });
});

describe("los errores no cuentan quién tiene cuenta", () => {
  test("el mensaje del backend se muestra tal cual", async () => {
    const red = servidor();
    red.respuestas.set("/api/auth/login", () => [
      401,
      errorDeApi("UNAUTHENTICATED", "El email o la contraseña no son correctos."),
    ]);
    const { auth } = await montar({ red });

    const r = await auth.entrar("alguien@example.com", "lo-que-sea");
    assert.equal(r.ok, false);
    assert.equal(r.mensaje, "El email o la contraseña no son correctos.");
  });

  test("el alta de un correo que ya existe no lo confirma", async () => {
    const red = servidor();
    red.respuestas.set("/api/auth/signup", () => [
      409,
      errorDeApi("CONFLICT", "No se pudo crear la cuenta con esos datos."),
    ]);
    const { auth } = await montar({ red });

    const r = await auth.registrarse("gustavo@example.com", "una-clave-larga");
    assert.equal(r.ok, false);
    assert.ok(!/existe|registrad/i.test(r.mensaje), `el mensaje delata: ${r.mensaje}`);
  });

  test("sin red se dice que es la red, no que las credenciales están mal", async () => {
    const red = servidor();
    red.fetch = async () => {
      throw new TypeError("Failed to fetch");
    };
    const { auth } = await montar({ red });

    const r = await auth.entrar("gustavo@example.com", "una-clave-larga");
    assert.equal(r.ok, false);
    assert.match(r.mensaje, /conect/i);
  });

  test("un 429 pide esperar", async () => {
    const red = servidor();
    red.respuestas.set("/api/auth/login", () => [429, {}]);
    const { auth } = await montar({ red });

    const r = await auth.entrar("gustavo@example.com", "una-clave-larga");
    assert.match(r.mensaje, /Esperá/);
  });

  test("una respuesta sin cuerpo no deja a la pantalla sin qué decir", async () => {
    const red = servidor();
    red.fetch = async () => new Response("no es json", { status: 500 });
    const { auth } = await montar({ red });

    const r = await auth.entrar("gustavo@example.com", "una-clave-larga");
    assert.equal(r.ok, false);
    assert.ok(r.mensaje.length > 0);
  });
});

describe("registrarse", () => {
  test("deja la sesión abierta", async () => {
    const { auth, dom } = await montar();
    const r = await auth.registrarse("nuevo@example.com", "una-clave-larga");
    assert.equal(r.ok, true);
    assert.ok(dom.window.localStorage.getItem(CLAVE_DE_SESION));
  });

  test("el correo se manda sin espacios alrededor", async () => {
    const { auth, red } = await montar();
    await auth.registrarse("  nuevo@example.com  ", "una-clave-larga");
    const alta = red.llamadas.find((l) => l.url.includes("/signup"));
    assert.equal(alta.cuerpo.email, "nuevo@example.com");
  });
});

describe("cambiar la contraseña", () => {
  test("manda la actual y la nueva juntas", async () => {
    const { auth, red } = await montar({ almacenado: guardado() });

    const r = await auth.actualizarUsuario({ password: "nueva-clave-123", actual: "la-vieja" });
    assert.equal(r.ok, true);

    const llamada = red.llamadas.find((l) => l.url.includes("/password"));
    assert.equal(llamada.metodo, "PUT");
    assert.equal(llamada.cuerpo.current_password, "la-vieja");
    assert.equal(llamada.cuerpo.new_password, "nueva-clave-123");
    assert.match(llamada.cabeceras.Authorization, /^Bearer /);
  });

  test("la sesión nueva que devuelve el servidor queda guardada", async () => {
    // El servidor corta todas las demás sesiones al cambiar la clave,
    // así que si no se guardara la que devuelve, cambiar la contraseña
    // echaría también a quien la cambió.
    const { auth, dom } = await montar({ almacenado: guardado({ token: "viejo" }) });
    await auth.actualizarUsuario({ password: "nueva-clave-123", actual: "la-vieja" });

    const s = JSON.parse(dom.window.localStorage.getItem(CLAVE_DE_SESION));
    assert.equal(s.access_token, "acceso-1");
  });

  test("sin la actual no se intenta nada", async () => {
    const { auth, red } = await montar({ almacenado: guardado() });
    const r = await auth.actualizarUsuario({ password: "nueva-clave-123" });
    assert.equal(r.ok, false);
    assert.equal(
      red.llamadas.filter((l) => l.url.includes("/password")).length,
      0,
      "salió a la red sabiendo que iba a fallar",
    );
  });

  test("el error del backend llega a la pantalla", async () => {
    const red = servidor();
    red.respuestas.set("/api/auth/password", () => [
      400,
      errorDeApi("VALIDATION_ERROR", "La contraseña actual no es correcta."),
    ]);
    const { auth } = await montar({ almacenado: guardado(), red });

    const r = await auth.actualizarUsuario({ password: "nueva-clave-123", actual: "mal" });
    assert.equal(r.ok, false);
    assert.equal(r.mensaje, "La contraseña actual no es correcta.");
  });
});

describe("la marca de recuperación", () => {
  test("se pone, se lee y se borra", async () => {
    const { auth } = await montar();
    assert.equal(auth.recuperacionEnCurso(), false);
    auth.marcarRecuperacion();
    assert.equal(auth.recuperacionEnCurso(), true);
    auth.olvidarRecuperacion();
    assert.equal(auth.recuperacionEnCurso(), false);
  });

  test("vive en sessionStorage, no en localStorage", async () => {
    // Tiene que morir con la pestaña, no quedar esperando semanas en
    // el dispositivo.
    const { auth, dom } = await montar();
    auth.marcarRecuperacion();
    assert.ok(dom.window.sessionStorage.getItem("epic-wallet-recuperacion"));
    assert.equal(dom.window.localStorage.getItem("epic-wallet-recuperacion"), null);
  });
});

describe("lo que el resto de la aplicación no tiene que saber", () => {
  test("no queda ni una mención al proveedor anterior", async () => {
    const { readFile } = await import("node:fs/promises");
    const fuente = await readFile(resolve(RAIZ, "web", "src", "js", "auth.js"), "utf8");
    // Salvo en el comentario que explica qué se reemplazó, que es
    // justamente lo que no hay que borrar.
    const sinComentarios = fuente.replace(/\/\*[\s\S]*?\*\//g, "");
    assert.ok(
      !/supabase/i.test(sinComentarios),
      "quedó código del proveedor anterior en auth.js",
    );
  });

  test("todas las peticiones van a nuestro /api/auth", async () => {
    const { auth, red } = await montar({ almacenado: guardado({ dentroDe: -1 }) });
    await auth.token();
    await auth.salir();

    assert.ok(red.llamadas.length >= 2);
    for (const l of red.llamadas) {
      assert.match(l.url, /\/api\/auth\//, `salió a otro lado: ${l.url}`);
    }
  });
});

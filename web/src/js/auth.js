/* Autenticación · F17-T03 (reemplaza la de F02-T08)
   Referencia: 02_Documento_Tecnico.md §8.7 y §8.11

   Este archivo es el único lugar del frontend que sabe cómo se guarda
   y se renueva una sesión. Todo lo demás le pide un token o le
   pregunta si hay sesión; nadie más toca `localStorage`, ni arma
   cabeceras, ni sabe cómo se renueva nada.

   QUÉ CAMBIÓ EN F17-T03

   Antes esto envolvía `@supabase/auth-js`, que hablaba con un servidor
   del proveedor. Ahora habla con `/api/auth`, que es nuestro, y la
   librería se fue del proyecto.

   **La superficie pública del módulo no cambió.** Las mismas funciones
   con los mismos nombres y las mismas formas de respuesta, para que
   las otras pantallas no se enteren de nada. Fue la condición de la
   tarea y es lo que hizo que el cambio tocara dos archivos y no
   cincuenta.

   LAS TRES COSAS QUE DABA LA LIBRERÍA Y HAY QUE SOSTENER

   Eran la razón por la que en F02-T08 se eligió una librería en vez de
   escribir seis `fetch`. Ninguna es difícil por separado; lo que las
   hace difíciles es que fallan en silencio.

   1. **Renovar antes de que venza**, para que nadie vea un error. Lo
      hace `token()`: si lo que tiene en mano vence dentro de menos de
      un minuto, renueva antes de devolverlo.

   2. **Una sola renovación en vuelo.** Si dos peticiones salen juntas
      con el token vencido, las dos piden renovar. Con tokens
      rotatorios eso es fatal: la primera quema el token, la segunda
      llega con uno ya usado, el servidor lo toma por robado y **corta
      la sesión**. `renovacionEnVuelo` hace que la segunda espere a la
      primera en lugar de pedir lo suyo.

   3. **Sincronía entre pestañas.** El evento `storage` del navegador
      avisa cuando otra pestaña tocó `localStorage`. Sin eso, cerrar
      sesión en una pestaña deja a la otra creyendo que sigue adentro
      hasta que algo falle.

   DÓNDE VIVE LA SESIÓN

   En `localStorage`, que sobrevive a recargar y a cerrar la aplicación
   instalada —`sessionStorage` no sobreviviría a lo segundo—. Guarda el
   token de acceso, el de renovación, cuándo vence y quién es.

   Que el token de renovación esté en `localStorage` es una decisión y
   no un descuido: la alternativa es una cookie `HttpOnly`, que lo
   escondería de JavaScript. No se tomó ese camino porque la aplicación
   es una sola página servida por el mismo dominio que la API, sin
   formularios hacia afuera, y porque una cookie traería CSRF, que hay
   que defender aparte. Lo que sí protege contra un token robado es la
   rotación del servidor: en cuanto el legítimo renueva, el robado deja
   de servir y la cadena entera se cae. */

/* Nombre de la entrada en `localStorage`. Lleva el proyecto adentro
   para que dos aplicaciones en el mismo dominio no se pisen, y para
   que cambiarlo invalide las sesiones viejas si alguna vez hace
   falta. */
const CLAVE_DE_SESION = "epic-wallet-auth";

/* Margen con el que se pide el token nuevo antes de que venza. Una
   petición que sale con un token que vence en dos segundos puede
   llegar vencida. */
const MARGEN_DE_RENOVACION = 60; // segundos

/** La base de la API. Vacía quiere decir «el mismo origen», que es lo
 * normal: el proxy de borde manda `/api/*` al backend. Se puede pisar
 * con `window.EPIC_WALLET.apiUrl`, y eso lo usan las pruebas. */
function baseDeApi() {
  const c = /** @type {any} */ (globalThis).EPIC_WALLET ?? {};
  return String(c.apiUrl ?? "").replace(/\/+$/, "");
}

/** Mensajes para el usuario.
 *
 * Están acá y no en la pantalla por una razón concreta: **ninguno
 * revela si el email existe.** El backend ya contesta lo mismo para
 * «no hay cuenta» y «contraseña equivocada» —y tarda lo mismo—; acá se
 * sostiene esa decisión del lado del navegador, para que no dependa de
 * una sola de las dos puntas.
 */
const MENSAJES = {
  credenciales: "El email o la contraseña no son correctos.",
  sin_confirmar: "Falta confirmar la cuenta. Revisá tu correo.",
  demasiados: "Demasiados intentos. Esperá un momento y volvé a probar.",
  red: "No se pudo conectar. Revisá tu conexión e intentá de nuevo.",
  debil: "La contraseña tiene que tener al menos 8 caracteres.",
  ya_existe: "No se pudo crear la cuenta con esos datos.",
  enlace: "El enlace no sirve o ya venció. Pedí uno nuevo.",
  generico: "Algo no funcionó. Intentá de nuevo en un momento.",
};

/** Traduce un error del backend a algo que se le pueda mostrar a una
 * persona, sin filtrar qué cuentas existen.
 *
 * @param {unknown} error
 * @returns {string}
 */
export function mensajeDeError(error) {
  if (!error) return MENSAJES.generico;

  const e = /** @type {any} */ (error);

  // Si ya viene un mensaje del backend, ese gana: lo escribe
  // `services/sesiones.py` en español y pensado para mostrarse tal
  // cual. Los de abajo son el resguardo para lo que no llegó a pasar
  // por ahí —una respuesta sin cuerpo, un corte de red—.
  const codigo = String(e.code ?? "");
  const estado = Number(e.status ?? 0);
  const texto = String(e.message ?? "").trim();

  if (codigo === "SIN_RED" || estado === 0) return MENSAJES.red;
  if (estado === 429) return MENSAJES.demasiados;
  if (texto) return texto;

  if (estado === 401) return MENSAJES.credenciales;
  if (estado === 409) return MENSAJES.ya_existe;
  return MENSAJES.generico;
}

// ===================================================================
//  Lo guardado
// ===================================================================

/**
 * @typedef {{
 *   access_token: string,
 *   refresh_token: string,
 *   expires_at: number,
 *   user: {id: string, email: string | null}
 * }} Guardado
 */

/** @returns {Guardado | null} */
function leerGuardado() {
  try {
    const crudo = globalThis.localStorage?.getItem(CLAVE_DE_SESION);
    if (!crudo) return null;
    const s = JSON.parse(crudo);
    // Una entrada a medias —una versión vieja del formato, o algo que
    // alguien tocó a mano— se trata como «no hay sesión» en vez de
    // romper la aplicación al arrancar.
    if (!s?.access_token || !s?.refresh_token || !s?.user?.id) return null;
    return s;
  } catch {
    return null;
  }
}

/** @param {Guardado | null} sesion */
function escribirGuardado(sesion) {
  try {
    if (sesion) {
      globalThis.localStorage?.setItem(CLAVE_DE_SESION, JSON.stringify(sesion));
    } else {
      globalThis.localStorage?.removeItem(CLAVE_DE_SESION);
    }
  } catch {
    // `localStorage` puede no estar (modo privado, almacenamiento
    // bloqueado). La sesión vive igual en memoria mientras la pestaña
    // esté abierta; lo que se pierde es sobrevivir a una recarga.
  }
  avisar(sesion);
}

/** Convierte la respuesta de `/api/auth` en lo que se guarda.
 *
 * `expires_at` se calcula acá, desde `expires_in` y el reloj local. Es
 * a propósito: lo que importa es cuándo vence **para este navegador**,
 * y si el reloj del dispositivo está corrido, un instante absoluto del
 * servidor haría renovar siempre o nunca.
 *
 * @param {any} datos
 * @returns {Guardado}
 */
function aGuardado(datos) {
  return {
    access_token: String(datos.access_token),
    refresh_token: String(datos.refresh_token),
    expires_at: Math.floor(Date.now() / 1000) + Number(datos.expires_in ?? 3600),
    user: {
      id: String(datos.user?.id ?? ""),
      email: datos.user?.email ?? null,
    },
  };
}

// ===================================================================
//  Hablar con /api/auth
// ===================================================================

/** Un error de la API con su código y su estado. */
class ErrorDeAuth extends Error {
  /** @param {{code?: string, message?: string, status?: number}} datos */
  constructor({ code, message, status } = {}) {
    super(message ?? "");
    this.name = "ErrorDeAuth";
    this.code = code ?? "";
    this.status = status ?? 0;
  }
}

/**
 * Llama a un endpoint de sesión.
 *
 * No pasa por `api.js` a propósito, aunque se le parezca: `api.js`
 * pide el token llamando a `cabeceras()` de este archivo, y renueva
 * cuando ve un 401. Si la renovación saliera por ahí, renovar
 * necesitaría una sesión para renovar la sesión.
 *
 * @param {string} ruta
 * @param {object} cuerpo
 * @param {{metodo?: string, token?: string | null}} [opciones]
 * @returns {Promise<any>}
 */
async function pedir(ruta, cuerpo, { metodo = "POST", token = null } = {}) {
  /** @type {Record<string, string>} */
  const cabecerasDeLaPeticion = { "Content-Type": "application/json" };
  if (token) cabecerasDeLaPeticion.Authorization = `Bearer ${token}`;

  let respuesta;
  try {
    respuesta = await fetch(`${baseDeApi()}/api/auth${ruta}`, {
      method: metodo,
      headers: cabecerasDeLaPeticion,
      body: JSON.stringify(cuerpo),
    });
  } catch {
    // Sin red no hay estado HTTP. Se marca con un código propio para
    // que `mensajeDeError` no lo confunda con un rechazo del servidor.
    throw new ErrorDeAuth({ code: "SIN_RED", status: 0 });
  }

  if (respuesta.status === 204) return null;

  let datos = null;
  try {
    datos = await respuesta.json();
  } catch {
    datos = null;
  }

  if (!respuesta.ok) {
    const error = datos?.error ?? {};
    throw new ErrorDeAuth({
      code: error.code,
      message: error.message,
      status: respuesta.status,
    });
  }
  return datos;
}

// ===================================================================
//  Entrar, salir, registrarse
// ===================================================================

/**
 * @typedef {{ok: true, usuario: {id: string, email: string | null}}} Exito
 * @typedef {{ok: false, mensaje: string, codigo?: string}} Falla
 */

/** @param {unknown} error @returns {Falla} */
function falla(error) {
  const codigo = String(/** @type {any} */ (error)?.code ?? "");
  return { ok: false, mensaje: mensajeDeError(error), codigo: codigo || undefined };
}

/** Guarda la sesión que vino y devuelve el éxito.
 * @param {any} datos @returns {Exito} */
function abrir(datos) {
  const sesion = aGuardado(datos);
  escribirGuardado(sesion);
  return { ok: true, usuario: sesion.user };
}

/**
 * Crea una cuenta y deja la sesión abierta.
 *
 * Entra directo al tablero: no hay confirmación por correo porque el
 * servidor no manda correos (General §48.1). La forma de la respuesta
 * mantiene la variante `falta_confirmar` que esperaba `registro.js`,
 * aunque hoy no se produzca nunca.
 *
 * @param {string} email
 * @param {string} clave
 * @returns {Promise<Exito | Falla | {ok: true, falta_confirmar: true}>}
 */
export async function registrarse(email, clave) {
  try {
    return abrir(await pedir("/signup", { email: email.trim(), password: clave }));
  } catch (e) {
    return falla(e);
  }
}

/**
 * @param {string} email
 * @param {string} clave
 * @returns {Promise<Exito | Falla>}
 */
export async function entrar(email, clave) {
  try {
    return abrir(await pedir("/login", { email: email.trim(), password: clave }));
  } catch (e) {
    return falla(e);
  }
}

/**
 * Cierra la sesión y borra lo guardado.
 *
 * No devuelve el error al que llama: si el servidor no contesta, la
 * sesión local se borra igual. Un «cerrar sesión» que falla y deja al
 * usuario adentro es peor que uno que cierra de más.
 *
 * @returns {Promise<void>}
 */
export async function salir() {
  const guardado = leerGuardado();
  try {
    await pedir("/logout", { refresh_token: guardado?.refresh_token ?? null });
  } catch {
    // Ignorado a propósito, ver arriba.
  }
  renovacionEnVuelo = null;
  escribirGuardado(null);
}

/**
 * Pide restablecer la contraseña.
 *
 * Hoy no hay correo saliente: el enlace lo genera Gustavo a mano con
 * `python -m app.cli recuperar <email>` y lo entrega por donde pueda
 * (General §48.1). Esta función devuelve `ok` sin hacer nada y la
 * pantalla explica el procedimiento. Que devuelva `ok` también evita
 * que la respuesta diga si ese correo tiene cuenta.
 *
 * F17-T04 le da el endpoint que le falta.
 *
 * @param {string} _email
 * @param {string} [_volverA]
 * @returns {Promise<{ok: true}>}
 */
export async function recuperarClave(_email, _volverA) {
  return { ok: true };
}

/**
 * Cambia la contraseña de la sesión abierta.
 *
 * Pide la actual. Antes no hacía falta pasarla —la pantalla la
 * verificaba llamando a `entrar()` primero—, y ahora va acá porque el
 * backend la exige en la misma petición: así no hay un instante entre
 * «verifiqué» y «cambié» en el que alguien pueda meterse.
 *
 * Al cambiarla, el servidor corta todas las demás sesiones de la
 * cuenta y devuelve una nueva, que es la que queda guardada.
 *
 * @param {{password?: string, actual?: string}} cambios
 * @returns {Promise<Exito | Falla>}
 */
export async function actualizarUsuario(cambios) {
  if (!cambios?.password) {
    return { ok: false, mensaje: MENSAJES.generico };
  }
  if (!cambios.actual) {
    // Es el camino del enlace de recuperación, que todavía no existe.
    // Decirlo así —y no «algo no funcionó»— es lo que evita que alguien
    // pierda media hora buscando una falla que es una tarea pendiente.
    return {
      ok: false,
      mensaje: "Para cambiar la contraseña hace falta la actual.",
    };
  }
  try {
    const datos = await pedir(
      "/password",
      { current_password: cambios.actual, new_password: cambios.password },
      { metodo: "PUT", token: await token() },
    );
    return abrir(datos);
  } catch (e) {
    return falla(e);
  }
}

// ===================================================================
//  Los enlaces de recuperación · F17-T04
// ===================================================================

/* Marca de «hay una recuperación en curso», en `sessionStorage`.

   Existe por una razón de seguridad concreta, no de comodidad: la
   pantalla de contraseña nueva es la única que cambia la clave **sin
   pedir la anterior**, y eso está bien sólo porque para llegar hay que
   haber abierto un enlace de un solo uso. Si fuera alcanzable con
   cualquier sesión abierta, dejar el teléfono desbloqueado un minuto
   alcanzaría para que otro cambie la contraseña sin saber la vieja.

   `sessionStorage` y no una variable del módulo: recargar la página a
   mitad del flujo no tiene que dejar al usuario con una sesión nueva y
   sin pantalla donde poner la contraseña. Y no `localStorage`: la
   marca muere con la pestaña, no queda esperando semanas. */
const CLAVE_DE_RECUPERACION = "epic-wallet-recuperacion";

/** Avisa que se entró por un enlace de recuperación. */
export function marcarRecuperacion() {
  try {
    globalThis.sessionStorage?.setItem(CLAVE_DE_RECUPERACION, "1");
  } catch {
    // Modo privado o almacenamiento bloqueado. El flujo recién empezado
    // sigue funcionando; lo que se pierde es recargar a mitad de camino.
  }
}

/** @returns {boolean} */
export function recuperacionEnCurso() {
  try {
    return globalThis.sessionStorage?.getItem(CLAVE_DE_RECUPERACION) === "1";
  } catch {
    return false;
  }
}

/** Se llama en cuanto la contraseña quedó cambiada, o al abandonar. */
export function olvidarRecuperacion() {
  try {
    globalThis.sessionStorage?.removeItem(CLAVE_DE_RECUPERACION);
  } catch {
    // Nada que limpiar si no hay almacenamiento.
  }
}

/**
 * Canjea el token de un enlace de recuperación por una sesión.
 *
 * El endpoint lo trae F17-T04. Hasta entonces devuelve el mismo error
 * que un enlace vencido, que es lo que corresponde: no hay enlace
 * válido posible todavía.
 *
 * @param {string} _token
 * @param {string} [_tipo]
 * @returns {Promise<Exito | Falla>}
 */
export async function verificarEnlace(_token, _tipo) {
  return { ok: false, mensaje: MENSAJES.enlace };
}

/**
 * Reenviar la confirmación de una cuenta nueva.
 *
 * No existe: no hay confirmación por correo porque no hay correo. Se
 * mantiene exportada porque `registro.js` la importa, y devuelve `ok`
 * para que esa pantalla no muestre un error por algo que no hace falta.
 *
 * @param {string} _email
 * @returns {Promise<{ok: true}>}
 */
export async function reenviarConfirmacion(_email) {
  return { ok: true };
}

// ===================================================================
//  El token
// ===================================================================

/* La renovación en curso, si hay una.
 *
 * Es LA pieza que no se puede sacar. Con tokens rotatorios, dos
 * renovaciones simultáneas no son un desperdicio: la primera quema el
 * token, la segunda llega con uno ya usado, el servidor lo toma por
 * robado y corta la familia entera. O sea, abrir dos pantallas a la
 * vez cerraría la sesión. */
let renovacionEnVuelo = /** @type {Promise<string | null> | null} */ (null);

/** Renueva de verdad. No llamar directo: usar `renovar()`.
 * @returns {Promise<string | null>} */
async function renovarAhora() {
  const guardado = leerGuardado();
  if (!guardado) return null;
  try {
    const datos = await pedir("/refresh", { refresh_token: guardado.refresh_token });
    const sesion = aGuardado(datos);
    escribirGuardado(sesion);
    return sesion.access_token;
  } catch (e) {
    // Sin red no se borra la sesión: el token de renovación sigue
    // siendo bueno y lo único que pasó es que no hay internet. Borrarla
    // mandaría a la pantalla de ingreso a alguien que simplemente entró
    // al subte.
    if (String(/** @type {any} */ (e)?.code ?? "") === "SIN_RED") return null;
    escribirGuardado(null);
    return null;
  }
}

/** @returns {Promise<string | null>} */
function renovar() {
  if (!renovacionEnVuelo) {
    renovacionEnVuelo = renovarAhora().finally(() => {
      renovacionEnVuelo = null;
    });
  }
  return renovacionEnVuelo;
}

/**
 * El token con el que hablarle a nuestra API, renovado si hace falta.
 *
 * Devuelve `null` cuando no hay sesión, y el que llama decide qué
 * hacer con eso. No redirige ni lanza: esta función no sabe si quien
 * la llama está pintando una pantalla o haciendo una petición de
 * fondo.
 *
 * Por qué revisa el vencimiento en vez de confiar en un temporizador:
 * un temporizador no corre mientras la pestaña está dormida, y al
 * volver puede haber un token vencido o a punto. Con un margen de un
 * minuto, lo que sale a la red siempre tiene vida por delante.
 *
 * @returns {Promise<string | null>}
 */
export async function token() {
  const guardado = leerGuardado();
  if (!guardado) return null;

  const ahora = Math.floor(Date.now() / 1000);
  if (guardado.expires_at - ahora > MARGEN_DE_RENOVACION) {
    return guardado.access_token;
  }
  return renovar();
}

/**
 * Las cabeceras para una petición a nuestra API, o `null` sin sesión.
 *
 * Está acá para que ningún otro archivo tenga que saber que el token
 * va en `Authorization: Bearer`.
 *
 * @returns {Promise<{Authorization: string} | null>}
 */
export async function cabeceras() {
  const t = await token();
  return t ? { Authorization: `Bearer ${t}` } : null;
}

/**
 * El usuario de la sesión guardada, sin ir a la red.
 *
 * Sirve para decidir qué pantalla mostrar al arrancar sin esperar una
 * petición. Que haya sesión guardada no garantiza que siga siendo
 * válida; de eso se encarga el 401 de la API.
 *
 * @returns {Promise<{id: string, email: string | null} | null>}
 */
export async function usuarioActual() {
  return leerGuardado()?.user ?? null;
}

/** @returns {Promise<boolean>} */
export async function haySesion() {
  return (await usuarioActual()) !== null;
}

// ===================================================================
//  Avisar cuando la sesión cambia
// ===================================================================

const oyentes = new Set();

/** @param {Guardado | null} sesion */
function avisar(sesion) {
  const estado = { hay: Boolean(sesion), usuario: sesion?.user ?? null };
  for (const oyente of [...oyentes]) {
    try {
      oyente(estado);
    } catch {
      // Un oyente que explota no puede impedir que los demás se
      // enteren, ni romper el `salir()` que disparó el aviso.
    }
  }
}

let escuchandoOtrasPestanias = false;

/* El evento `storage` del navegador llega SÓLO a las otras pestañas,
   nunca a la que escribió. Es justo lo que hace falta: la que escribió
   ya avisó por `escribirGuardado`. */
function escucharOtrasPestanias() {
  if (escuchandoOtrasPestanias) return;
  const ventana = /** @type {any} */ (globalThis);
  if (typeof ventana.addEventListener !== "function") return;
  ventana.addEventListener("storage", (/** @type {any} */ evento) => {
    if (evento?.key !== CLAVE_DE_SESION) return;
    // Una renovación que haya empezado en esta pestaña ya no vale: el
    // token que iba a usar lo cambió la otra.
    renovacionEnVuelo = null;
    avisar(leerGuardado());
  });
  escuchandoOtrasPestanias = true;
}

/**
 * Avisa cuando la sesión cambia: entrar, salir, token renovado.
 *
 * Incluye los cambios hechos en **otra pestaña**. Es lo que evita que
 * cerrar sesión en una deje la otra creyendo que sigue adentro.
 *
 * @param {(estado: {hay: boolean, usuario: {id: string, email: string | null} | null}) => void} alCambiar
 * @returns {() => void} para dejar de escuchar
 */
export function alCambiarLaSesion(alCambiar) {
  escucharOtrasPestanias();
  oyentes.add(alCambiar);
  return () => oyentes.delete(alCambiar);
}

/** Sólo para las pruebas: olvida todo el estado del módulo.
 *
 * No lo usa nada de la aplicación.
 */
export function _reiniciar() {
  renovacionEnVuelo = null;
  oyentes.clear();
}

export const _interno = {
  CLAVE_DE_SESION,
  CLAVE_DE_RECUPERACION,
  MARGEN_DE_RENOVACION,
  MENSAJES,
};

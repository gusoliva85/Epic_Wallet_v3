"""Verificación del token de sesión. Corresponde a F02-T01.

`current_user_id` es la única puerta de todo lo privado: si acá entra
algo que no debería, entra en toda la aplicación. Por eso las pruebas
**fabrican tokens de verdad** —con una clave EC propia, firmados y
decodificados como los reales— en lugar de simular la biblioteca. Un
doble de `jwt.decode` probaría el doble, no la verificación.

Los cinco casos que pide la tarea: válido, vencido, firma incorrecta,
audiencia incorrecta y sin el claim `sub`.
"""

from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
from api.app.core import security
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

AUDIENCIA = "authenticated"
UUID_DE_PRUEBA = "6f1d2b40-0000-4000-8000-000000000001"


# --------------------------------------------------------------- claves


@pytest.fixture(scope="module")
def par_de_claves() -> tuple[Any, Any]:
    """Una clave EC P-256, la misma curva que firma las sesiones."""
    privada = ec.generate_private_key(ec.SECP256R1())
    return privada, privada.public_key()


@pytest.fixture(scope="module")
def otra_clave() -> Any:
    """Una segunda clave, para firmar con la que no corresponde."""
    return ec.generate_private_key(ec.SECP256R1())


def _pem_publica(publica: Any) -> str:
    return publica.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


@pytest.fixture
def clave_del_proyecto(monkeypatch: pytest.MonkeyPatch, par_de_claves: tuple[Any, Any]) -> None:
    """Pone nuestra clave pública donde el verificador la busca.

    Se toca la configuración, no `jwt.decode`: así la firma se
    comprueba de verdad contra una clave que controlamos, que es
    exactamente lo que pasa en el servidor.

    Hasta F17-T01 esta fixture simulaba un endpoint JWKS del proveedor
    anterior. Ahora la clave está en el proceso y no hay nada que
    simular.
    """
    _, publica = par_de_claves
    monkeypatch.setattr(security, "clave_de_verificacion", lambda: _pem_publica(publica))


def token(
    privada: Any,
    *,
    sub: str | None = UUID_DE_PRUEBA,
    aud: str | None = AUDIENCIA,
    exp: int | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Fabrica un token como los que emite el proyecto."""
    ahora = int(time.time())
    carga: dict[str, Any] = {"iat": ahora, "exp": exp if exp is not None else ahora + 3600}
    if sub is not None:
        carga["sub"] = sub
    if aud is not None:
        carga["aud"] = aud
    carga.update(extra or {})
    return jwt.encode(carga, privada, algorithm="ES256", headers={"kid": "prueba"})


# ------------------------------------------------- los cinco casos pedidos


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_un_token_valido_devuelve_el_usuario(par_de_claves: tuple[Any, Any]) -> None:
    privada, _ = par_de_claves
    payload = security.verificar(token(privada))
    assert payload["sub"] == UUID_DE_PRUEBA


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_un_token_vencido_se_rechaza(par_de_claves: tuple[Any, Any]) -> None:
    """Y con mensaje propio: el frontend puede renovar la sesión sin
    molestar al usuario, cosa que no haría con una inválida."""
    privada, _ = par_de_claves
    vencido = token(privada, exp=int(time.time()) - security.TOLERANCIA_DE_RELOJ - 60)

    with pytest.raises(security.ErrorDeApi) as caso:
        security.verificar(vencido)

    assert caso.value.status_code == 401
    assert "expir" in caso.value.message.lower()


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_un_token_firmado_con_otra_clave_se_rechaza(otra_clave: Any) -> None:
    """Criterio de aceptación: un token manipulado se rechaza por la
    firma. Es el caso que importa: alguien que fabrica un token con el
    uuid de otra persona."""
    ajeno = token(otra_clave, sub="00000000-0000-4000-8000-000000000999")

    with pytest.raises(security.ErrorDeApi) as caso:
        security.verificar(ajeno)

    assert caso.value.status_code == 401


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_un_token_con_otra_audiencia_se_rechaza(par_de_claves: tuple[Any, Any]) -> None:
    """Supabase emite tokens para varias audiencias. Uno de otro uso,
    aunque esté bien firmado por el mismo proyecto, no sirve acá."""
    privada, _ = par_de_claves

    with pytest.raises(security.ErrorDeApi):
        security.verificar(token(privada, aud="otra-cosa"))


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_un_token_sin_sub_se_rechaza(par_de_claves: tuple[Any, Any]) -> None:
    """Sin `sub` no hay a quién atribuirle los datos. Dejarlo pasar
    sería trabajar con un usuario vacío."""
    privada, _ = par_de_claves

    with pytest.raises(security.ErrorDeApi):
        security.verificar(token(privada, sub=None))


# ------------------------------------------- lo que la tarea no pedía y falta


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
@pytest.mark.parametrize("vacio", ["", "   "])
def test_un_sub_vacio_tambien_se_rechaza(par_de_claves: tuple[Any, Any], vacio: str) -> None:
    """`require: ["sub"]` exige que el claim ESTÉ, no que valga algo.

    Un token con `"sub": ""` pasa la verificación de PyJWT y deja al
    backend consultando por un usuario vacío, que es peor que rechazar.
    """
    privada, _ = par_de_claves

    with pytest.raises(security.ErrorDeApi):
        security.verificar(token(privada, sub=vacio))


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_un_token_sin_vencimiento_se_rechaza(par_de_claves: tuple[Any, Any]) -> None:
    """Sin `exp`, el token vale para siempre. PyJWT lo acepta si no se
    lo exige explícitamente."""
    privada, _ = par_de_claves
    ahora = int(time.time())
    sin_exp = jwt.encode(
        {"iat": ahora, "sub": UUID_DE_PRUEBA, "aud": AUDIENCIA},
        privada,
        algorithm="ES256",
        headers={"kid": "prueba"},
    )

    with pytest.raises(security.ErrorDeApi):
        security.verificar(sin_exp)


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_un_token_sin_firma_se_rechaza(par_de_claves: tuple[Any, Any]) -> None:
    """El ataque clásico: cambiar el algoritmo a `none` y sacar la
    firma. Se rechaza porque sólo se admite ES256."""
    privada, _ = par_de_claves
    bueno = token(privada)
    cabecera, carga, _firma = bueno.split(".")

    sin_firma = jwt.encode(
        jwt.decode(bueno, options={"verify_signature": False}, audience=AUDIENCIA),
        key="",
        algorithm="none",
    )

    with pytest.raises(security.ErrorDeApi):
        security.verificar(sin_firma)
    # Y el payload manipulado tampoco pasa con la firma vieja.
    with pytest.raises(security.ErrorDeApi):
        security.verificar(f"{cabecera}.{carga}x.{_firma}")


# ------------------------------------------------ el error no cuenta de más


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
@pytest.mark.parametrize(
    "caso",
    ["otra_clave", "otra_audiencia", "sin_sub", "basura"],
)
def test_el_mensaje_no_filtra_por_que_fallo(
    par_de_claves: tuple[Any, Any], otra_clave: Any, caso: str
) -> None:
    """Criterio de aceptación: el mensaje no filtra detalles internos.

    «Firma incorrecta» o «audiencia equivocada» le dicen a quien está
    probando exactamente qué ajustar. Todos los inválidos dicen lo
    mismo; el detalle va al registro, que sí lo necesita.
    """
    privada, _ = par_de_claves
    malos = {
        "otra_clave": token(otra_clave),
        "otra_audiencia": token(privada, aud="otra"),
        "sin_sub": token(privada, sub=None),
        "basura": "esto.no.es-un-token",
    }

    with pytest.raises(security.ErrorDeApi) as resultado:
        security.verificar(malos[caso])

    mensaje = resultado.value.message.lower()
    assert mensaje == "la sesión no es válida."
    for filtracion in ("signature", "firma", "audience", "audiencia", "sub", "jwks", "es256"):
        assert filtracion not in mensaje, f"el mensaje cuenta de más: {mensaje}"


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_los_tres_casos_se_distinguen(par_de_claves: tuple[Any, Any]) -> None:
    """Sin sesión, vencida e inválida tienen que ser distinguibles: el
    frontend renueva una y manda a entrar en las otras dos."""
    privada, _ = par_de_claves
    ahora = int(time.time())

    with pytest.raises(security.ErrorDeApi) as vencida:
        # Vencido más allá de la tolerancia de reloj, o sigue valiendo.
        security.verificar(token(privada, exp=ahora - security.TOLERANCIA_DE_RELOJ - 60))
    with pytest.raises(security.ErrorDeApi) as invalida:
        security.verificar("basura")

    assert vencida.value.message != invalida.value.message
    # Y el de «no hay sesión» es el tercero, que pone current_user_id.
    assert "iniciar sesión" not in vencida.value.message


# ------------------------------------------------- las claves, una sola vez


@pytest.mark.unit
def test_verificar_no_sale_a_internet(
    monkeypatch: pytest.MonkeyPatch, par_de_claves: tuple[Any, Any]
) -> None:
    """Criterio de F17-T01.

    Hasta esta tarea, verificar un token significaba pedirle las claves
    a un servicio ajeno: un viaje de red por proceso y, peor, que entrar
    a la aplicación dependiera de que ese servicio respondiera.

    Se revienta `socket.socket` para que cualquier intento de abrir una
    conexión falle de forma ruidosa. Si la verificación sigue andando,
    es porque no sale a ningún lado.
    """
    import socket

    def prohibido(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("verificar() intentó abrir una conexión de red")

    monkeypatch.setattr(socket, "socket", prohibido)

    privada, publica = par_de_claves
    monkeypatch.setattr(security, "clave_de_verificacion", lambda: _pem_publica(publica))

    carga = security.verificar(token(privada))
    assert carga["sub"] == UUID_DE_PRUEBA


@pytest.mark.unit
def test_la_clave_sale_de_la_configuracion(monkeypatch: pytest.MonkeyPatch) -> None:
    """`clave_de_verificacion` lee `JWT_PUBLIC_KEY`, y acepta el PEM con
    los saltos escapados: así es como sobrevive a un archivo .env."""
    from api.app.core.config import Settings

    privada = ec.generate_private_key(ec.SECP256R1())
    pem = _pem_publica(privada.public_key())

    config = Settings(  # type: ignore[call-arg]
        DATABASE_URL="postgresql+psycopg://u:p@db:5432/x",
        JWT_PUBLIC_KEY=pem.replace("\n", "\\n"),
    )
    assert config.clave_publica == pem.strip()

    monkeypatch.setattr(security, "get_settings", lambda: config)
    assert security.clave_de_verificacion() == pem.strip()


@pytest.mark.unit
def test_sin_clave_configurada_se_rechaza_y_se_avisa(
    monkeypatch: pytest.MonkeyPatch, caplog: Any, par_de_claves: tuple[Any, Any]
) -> None:
    """Sin clave no se puede verificar nada, así que ningún endpoint
    privado responde. Hacia afuera es «sesión inválida» como siempre;
    hacia el registro tiene que decir que falta configuración, porque
    si no parece que el token está mal cuando lo que está mal es el
    despliegue."""
    import logging

    class ConfigSinClave:
        clave_publica = ""

    monkeypatch.setattr(security, "get_settings", lambda: ConfigSinClave())

    privada, _ = par_de_claves
    with (
        caplog.at_level(logging.ERROR, logger="epic_wallet"),
        pytest.raises(security.ErrorDeApi) as excepcion,
    ):
        security.verificar(token(privada))

    assert excepcion.value.status_code == 401
    assert "JWT_PUBLIC_KEY" in caplog.text


# ------------------------------------------------ la configuración del algoritmo


@pytest.mark.unit
def test_solo_se_admite_es256() -> None:
    """Admitir más de un algoritmo abre la puerta a que un token venga
    firmado con HMAC usando la clave pública como secreto."""
    assert security.ALGORITMO == "ES256"


@pytest.mark.unit
def test_el_secreto_compartido_no_se_usa_para_verificar() -> None:
    """`SUPABASE_JWT_SECRET` quedó en la configuración como resto de la
    documentación vieja. Si alguien lo usara, bastaría tenerlo para
    fabricar sesiones."""
    fuente = __import__("pathlib").Path(security.__file__).read_text(encoding="utf-8")
    import re

    sin_comentarios = re.sub(r'""".*?"""', "", fuente, flags=re.S)
    sin_comentarios = re.sub(r"^\s*#.*$", "", sin_comentarios, flags=re.M)
    assert "SUPABASE_JWT_SECRET" not in sin_comentarios


# -------------------------------- la dependencia, dentro de una aplicación


def _app_de_prueba() -> Any:
    """Una aplicación mínima con un endpoint privado.

    Se arma acá y no se usa la real para que la prueba falle por la
    autenticación y no por cualquier otra cosa que la aplicación
    necesite para arrancar.
    """
    from api.app.core.errors import registrar_manejadores
    from fastapi import FastAPI

    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/privado")
    async def privado(uid: security.UsuarioActual) -> dict[str, str]:
        return {"uid": uid}

    return app


@pytest.fixture
def cliente() -> Any:
    from fastapi.testclient import TestClient

    return TestClient(_app_de_prueba(), raise_server_exceptions=False)


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_con_token_valido_el_endpoint_responde(
    cliente: Any, par_de_claves: tuple[Any, Any]
) -> None:
    privada, _ = par_de_claves
    r = cliente.get("/privado", headers={"Authorization": f"Bearer {token(privada)}"})
    assert r.status_code == 200
    assert r.json() == {"uid": UUID_DE_PRUEBA}


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
@pytest.mark.parametrize(
    "cabeceras",
    [
        pytest.param({}, id="sin cabecera"),
        pytest.param({"Authorization": "Bearer "}, id="bearer vacío"),
        pytest.param({"Authorization": "Bearer    "}, id="sólo espacios"),
        pytest.param({"Authorization": "Basic abc"}, id="otro esquema"),
    ],
)
def test_sin_sesion_responde_401(cliente: Any, cabeceras: dict[str, str]) -> None:
    r = cliente.get("/privado", headers=cabeceras)
    assert r.status_code == 401


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_el_401_sale_con_la_forma_de_error_de_la_api(cliente: Any) -> None:
    """Por esto `HTTPBearer` va con `auto_error=False`: con `True`,
    FastAPI devuelve su propio 401 sin pasar por los manejadores y la
    respuesta sale con otra forma que todas las demás de la API.
    """
    r = cliente.get("/privado")
    cuerpo = r.json()
    assert "error" in cuerpo, f"el 401 no tiene la forma de la API: {cuerpo}"
    assert cuerpo["error"]["code"] == "UNAUTHENTICATED"
    assert cuerpo["error"]["message"]


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_un_token_de_otra_persona_no_deja_entrar(cliente: Any, otra_clave: Any) -> None:
    """El caso que de verdad importa: alguien fabrica un token con el
    uuid de otro usuario y lo firma con una clave suya."""
    falso = token(otra_clave, sub="00000000-0000-4000-8000-00000000dead")
    r = cliente.get("/privado", headers={"Authorization": f"Bearer {falso}"})
    assert r.status_code == 401
    assert "dead" not in r.text


# ------------------------------------------------- tolerancia de reloj


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_un_token_recien_emitido_se_acepta_con_el_reloj_corrido(
    par_de_claves: tuple[Any, Any],
) -> None:
    """La razón de ser de `TOLERANCIA_DE_RELOJ`.

    Sin ella, un token emitido por Supabase se rechaza si el reloj del
    servidor está aunque sea una fracción de segundo atrasado. Medido
    contra el proyecto real: **0,2 segundos bastaban** para que la
    verificación fallara con «The token is not yet valid (iat)».

    En producción se habría visto como un 401 intermitente justo
    después de entrar: imposible de reproducir a voluntad.
    """
    privada, _ = par_de_claves
    ahora = int(time.time())
    # Como si el reloj de este servidor estuviera 5 segundos atrasado.
    del_futuro = jwt.encode(
        {
            "iat": ahora + 5,
            "nbf": ahora + 5,
            "exp": ahora + 3600,
            "sub": UUID_DE_PRUEBA,
            "aud": AUDIENCIA,
        },
        privada,
        algorithm="ES256",
        headers={"kid": "prueba"},
    )

    assert security.verificar(del_futuro)["sub"] == UUID_DE_PRUEBA


@pytest.mark.unit
@pytest.mark.usefixtures("clave_del_proyecto")
def test_la_tolerancia_no_acepta_un_token_del_futuro_lejano(
    par_de_claves: tuple[Any, Any],
) -> None:
    """La tolerancia es para el desfase de reloj, no una puerta abierta:
    un token fechado mucho más adelante sigue siendo inválido."""
    privada, _ = par_de_claves
    ahora = int(time.time())
    lejano = jwt.encode(
        {
            "iat": ahora + security.TOLERANCIA_DE_RELOJ + 600,
            "nbf": ahora + security.TOLERANCIA_DE_RELOJ + 600,
            "exp": ahora + 7200,
            "sub": UUID_DE_PRUEBA,
            "aud": AUDIENCIA,
        },
        privada,
        algorithm="ES256",
        headers={"kid": "prueba"},
    )

    with pytest.raises(security.ErrorDeApi):
        security.verificar(lejano)


@pytest.mark.unit
def test_la_tolerancia_es_chica() -> None:
    """Treinta segundos cubren el desfase de reloj. Mucho más sería
    alargar la vida de un token vencido sin motivo."""
    assert 0 < security.TOLERANCIA_DE_RELOJ <= 120

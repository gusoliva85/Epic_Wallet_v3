# ============================================================
#  F19-T01 - Bajar los datos de la version anterior
#
#      .\scripts\bajar_datos_anteriores.ps1
#
#  SOLO LECTURA. No escribe una sola fila alla, y no puede:
#  la conexion se abre con `default_transaction_read_only=on`,
#  asi que la propia base rechaza cualquier escritura aunque
#  alguien se equivoque. Lo unico que corre son `pg_dump` y un
#  `copy ... to`, que leen.
#
#  CORRE EN LA MAQUINA DE GUSTAVO, NO EN EL SERVIDOR
#  Las credenciales de la version anterior viven en
#  D:\Respaldos\Epic_Wallet\credenciales_2.0.env, fuera de los
#  dos repositorios, y de ahi no se mueven: haciendolo aca no
#  tienen que viajar a ningun lado. `pg_dump` sale de la imagen
#  oficial de Postgres por Docker, asi que no hay nada que
#  instalar.
#
#  BAJA LAS TRES CUENTAS, NO UNA
#  No pasa por la aplicacion: lee las tablas enteras, asi que trae las
#  filas de Gustavo, de Nelida y de Diego juntas. El "Exportar JSON" de
#  Ajustes -> Respaldo es otra cosa: ese pasa por la API y devuelve solo
#  la cuenta de quien lo toca.
#
#  EL CORTE QUE EVITA UN ARCHIVO HUECO
#  Las once tablas tienen `force row level security`: una fila se ve
#  solo si la politica la deja pasar, y las politicas comparan contra
#  `auth.uid()`, que sale del token. Una conexion de psql no tiene
#  token. Si el usuario con el que entramos no puede saltear RLS, el
#  dump NO da error: abre perfecto, lista las once tablas y no trae una
#  sola fila. El script lo comprueba antes de empezar y corta, y despues
#  vuelve a comprobarlo contando filas.
#
#  QUE DEJA, en D:\Respaldos\Epic_Wallet\anterior\
#    datos_<fecha>.dump      el esquema de datos entero, con las filas
#    usuarios_<fecha>.dump   las filas de auth.users, tal como estan alla
#    usuarios_<fecha>.csv    las 6 columnas que tiene NUESTRA auth.users
#    esquema_<fecha>.sql     el esquema en texto, para comparar
#    conteos_<fecha>.txt     cuantas filas tiene cada tabla
#
#  Los dos .dump son la materia prima. El .csv es lo que entra
#  derecho en F19-T02, porque alla `auth.users` tiene unas 35
#  columnas y la nuestra 6: un restore directo del dump no
#  encajaria. Y `conteos` es la prueba de aceptacion de T02
#  --"la cantidad de filas coincide tabla por tabla"--: hay que
#  tenerla tomada ANTES de importar, no despues.
#
#  Este archivo se borra cuando termine el traslado, igual que
#  `sin_proveedores.sh`.
# ============================================================

[CmdletBinding()]
param(
    [string]$Credenciales = "D:\Respaldos\Epic_Wallet\credenciales_2.0.env",
    [string]$Destino      = "D:\Respaldos\Epic_Wallet\anterior",
    [string]$Imagen       = "postgres:17-alpine"
)

$ErrorActionPreference = "Stop"

function Decir($texto)  { Write-Host "  $texto" }
function Bien($texto)   { Write-Host "  OK - $texto"    -ForegroundColor Green }
function Mal($texto)    { Write-Host "  FALLA - $texto" -ForegroundColor Red }
function Aviso($texto)  { Write-Host "  ! $texto"       -ForegroundColor Yellow }

# Corre un programa sin que PowerShell convierta su stderr en una
# excepcion. Es el mismo ayudante que `traer_respaldos.ps1`, y existe
# por lo mismo: con $ErrorActionPreference = "Stop", una linea en
# stderr de un .exe aborta el script antes de que podamos explicar que
# paso.
function Correr {
    param([string]$programa, [string[]]$argumentos)
    $previo = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try   { return (& $programa @argumentos 2>&1 | ForEach-Object { "$_" }) }
    finally { $ErrorActionPreference = $previo }
}

Write-Host ""
Write-Host "==============================================================="
Write-Host "  EPIC WALLET - bajar los datos de la version anterior"
Write-Host "  SOLO LECTURA"
Write-Host "==============================================================="
Write-Host ""

# ------------------------------------------------ 1 - Docker
Decir "Buscando Docker..."
$version = Correr "docker" @("version", "--format", "{{.Server.Version}}")
if ($LASTEXITCODE -ne 0 -or -not $version) {
    Mal "Docker no responde."
    Decir "Abri Docker Desktop, espera a que diga 'Engine running' y volve a correr esto."
    exit 1
}
Bien "Docker $version"

# ------------------------------------------------ 2 - credenciales
if (-not (Test-Path $Credenciales)) {
    Mal "no existe $Credenciales"
    exit 1
}

$urlCruda = $null
foreach ($linea in Get-Content $Credenciales -Encoding UTF8) {
    $limpia = $linea.Trim()
    if ($limpia -match '^DATABASE_URL\s*=\s*(.+)$') {
        $urlCruda = $Matches[1].Trim().Trim('"').Trim("'")
    }
}
if (-not $urlCruda) {
    Mal "no hay DATABASE_URL en $Credenciales"
    exit 1
}

# El driver de SQLAlchemy no lo entiende `pg_dump`.
$urlCruda = $urlCruda -replace '^postgresql\+psycopg://', 'postgresql://'

try {
    $u = [System.Uri]$urlCruda
} catch {
    Mal "la DATABASE_URL no se puede interpretar"
    exit 1
}

if ($u.UserInfo -notmatch ':') {
    Mal "la DATABASE_URL no trae usuario y clave"
    exit 1
}
$usuario = [System.Uri]::UnescapeDataString($u.UserInfo.Split(':')[0])
$clave   = [System.Uri]::UnescapeDataString($u.UserInfo.Split(':', 2)[1])
$maquina = $u.Host
$base    = $u.AbsolutePath.TrimStart('/')
$puerto  = $u.Port

if (-not $usuario -or -not $clave -or -not $maquina -or -not $base) {
    Mal "la DATABASE_URL quedo incompleta al interpretarla"
    Decir "Si la clave tiene un '@' o un '/' adentro, tiene que estar escrita con %40 o %2F."
    exit 1
}

# EL DETALLE QUE HACE FALLAR TODO SI NO SE MIRA
#
# La URL de la aplicacion apunta al pooler en modo TRANSACCION
# (puerto 6543). Ahi cada consulta puede caer en una conexion distinta,
# asi que no hay sesion: `pg_dump` necesita una --abre una transaccion
# con snapshot consistente y fija parametros de sesion-- y falla con un
# error que no dice esto.
#
# El mismo host en el puerto 5432 es el pooler en modo SESION, con el
# mismo usuario y la misma clave. Ahi `pg_dump` anda.
if ($puerto -eq 6543) {
    Aviso "la URL apunta al pooler de transacciones (6543), donde pg_dump no funciona"
    Decir "Se usa el mismo host en 5432, que es el de sesion."
    $puerto = 5432
}

Bien "destino de lectura: $maquina`:$puerto/$base"

# ------------------------------------------------ 3 - carpeta
New-Item -ItemType Directory -Force -Path $Destino | Out-Null
$fecha = Get-Date -Format "yyyy-MM-dd_HHmm"
Bien "los archivos van a $Destino"
Write-Host ""

# `sslmode=require` porque la conexion sale a internet.
# `default_transaction_read_only=on` es el cinturon: con esto puesto,
# la base rechaza cualquier INSERT, UPDATE o DELETE que llegue por esta
# conexion, venga de donde venga.
$conexion = "postgresql://${usuario}@${maquina}:${puerto}/${base}?sslmode=require"

function ArmarComunes([bool]$conCinturon) {
    $a = @("run", "--rm", "-e", "PGPASSWORD=$clave")
    if ($conCinturon) { $a += @("-e", "PGOPTIONS=-c default_transaction_read_only=on") }
    return $a + @("-v", "${Destino}:/salida", $Imagen)
}

# El cinturon se pide al abrir la conexion, y no todos los poolers
# dejan pasar parametros de arranque. Si este no los deja, la conexion
# falla y TODOS los pasos de abajo fallarian con un error que no dice
# por que. Asi que se prueba primero, una vez.
Decir "Probando la conexion de solo lectura..."
$comunes = ArmarComunes $true
$prueba = Correr "docker" ($comunes + @(
    "psql", $conexion, "--no-psqlrc", "-At", "-c", "show transaction_read_only"
))
if ($LASTEXITCODE -ne 0) {
    Aviso "el servidor no acepta que la conexion se abra en solo lectura"
    $comunes = ArmarComunes $false
    $prueba = Correr "docker" ($comunes + @(
        "psql", $conexion, "--no-psqlrc", "-At", "-c", "select 1"
    ))
    if ($LASTEXITCODE -ne 0) {
        Mal "no se pudo conectar"
        $prueba | Select-Object -Last 10 | ForEach-Object { Write-Host "      $_" }
        Decir ""
        Decir "Lo mas probable: el host no acepta conexiones de sesion en 5432."
        Decir "Fijate en el panel del proveedor cual es la cadena de conexion"
        Decir "directa (la que NO dice pooler) y pasamela sin la clave."
        exit 1
    }
    Aviso "se sigue sin el cinturon. Lo que corre son pg_dump y un 'copy ... to',"
    Aviso "que leen y nada mas, pero la base ya no lo garantiza por si sola."
} elseif (($prueba | Select-Object -First 1) -eq "on") {
    Bien "la conexion esta en solo lectura: la base rechaza cualquier escritura"
} else {
    Aviso "la conexion no quedo en solo lectura (dijo '$prueba')"
}
Write-Host ""

# ------------------------------------------------ el corte que importa
#
# LAS ONCE TABLAS TIENEN `force row level security`.
#
# Eso significa que cada fila solo se ve si la politica la deja pasar, y
# las politicas comparan contra `auth.uid()`, que sale del token. Una
# conexion de `psql` no tiene token: `auth.uid()` es NULL y NINGUNA
# politica da verdadero.
#
# Si el usuario con el que entramos no puede saltear RLS, el resultado
# no es un error: es un dump que abre perfecto, lista las once tablas
# y NO TRAE UNA SOLA FILA. Se descubriria al importar, o peor, mas
# tarde. Por eso esto corta y no avisa.
Decir "Comprobando que este usuario vea las filas de las tres cuentas..."
$quien = Correr "docker" ($comunes + @(
    "psql", $conexion, "--no-psqlrc", "-At", "-F", "|", "-c",
    "select current_user, rolsuper, rolbypassrls from pg_roles where rolname = current_user"
))
if ($LASTEXITCODE -ne 0) {
    Mal "no se pudo averiguar con que permisos entramos"
    $quien | Select-Object -Last 6 | ForEach-Object { Write-Host "      $_" }
    exit 1
}
$partes = ($quien | Select-Object -First 1).Split('|')
$soy      = $partes[0]
$esSuper  = $partes[1] -eq 't'
$salteaRls = $partes[2] -eq 't'

if ($esSuper -or $salteaRls) {
    Bien "entramos como '$soy', que ve todas las filas de todas las cuentas"
} else {
    Mal "el usuario '$soy' NO puede saltear RLS"
    Decir ""
    Decir "Con este usuario el dump saldria VACIO y sin dar ningun error:"
    Decir "las tablas tienen RLS forzado y sin token ninguna fila pasa."
    Decir ""
    Decir "Hace falta la cadena de conexion del usuario administrador"
    Decir "(el del panel, el mismo que usa su editor de SQL). Pasamela"
    Decir "sin la clave y la vemos."
    exit 1
}
Write-Host ""

$problemas = 0

function Paso {
    param([string]$titulo, [string[]]$argumentos, [string]$archivo)
    Decir $titulo
    $salida = Correr "docker" ($script:comunes + $argumentos)
    if ($LASTEXITCODE -ne 0) {
        Mal "no se pudo: $titulo"
        $salida | Select-Object -Last 8 | ForEach-Object { Write-Host "      $_" }
        $script:problemas++
        return $false
    }
    $ruta = Join-Path $Destino $archivo
    if (-not (Test-Path $ruta) -or (Get-Item $ruta).Length -eq 0) {
        Mal "$archivo quedo vacio"
        $script:problemas++
        return $false
    }
    $kb = [math]::Round((Get-Item $ruta).Length / 1KB, 1)
    Bien "$archivo - $kb KB"
    return $true
}

# -------------------------- 4 - el esquema de datos, entero
$nombreDatos = "datos_$fecha.dump"
$okDatos = Paso "1 - el esquema de datos (schema + filas)..." @(
    "pg_dump", $conexion,
    "--format=custom", "--no-owner", "--no-privileges",
    "--schema=public",
    "--file=/salida/$nombreDatos"
) $nombreDatos

# -------------------------- 5 - los usuarios, tal como estan alla
$nombreUsuarios = "usuarios_$fecha.dump"
Paso "2 - las filas de auth.users (solo datos)..." @(
    "pg_dump", $conexion,
    "--format=custom", "--no-owner", "--no-privileges",
    "--data-only", "--table=auth.users",
    "--file=/salida/$nombreUsuarios"
) $nombreUsuarios | Out-Null

# -------------------------- 6 - los usuarios, con NUESTRAS columnas
#
# Las seis que tiene `auth.users` de la 3.0, en su orden. `coalesce`
# en los metadatos porque alla la columna admite nulos y aca no.
# `encrypted_password` viaja tal cual: es un hash bcrypt y la 3.0 usa
# bcrypt a proposito, asi que nadie restablece su contrasenia.
$sqlUsuarios = "copy (select id, email, encrypted_password, email_confirmed_at, " +
    "coalesce(raw_user_meta_data, '{}'::jsonb) as raw_user_meta_data, created_at " +
    "from auth.users order by created_at) to stdout with (format csv, header)"

$nombreCsv = "usuarios_$fecha.csv"
Decir "3 - los usuarios con las columnas de la 3.0..."
$csv = Correr "docker" ($comunes + @("psql", $conexion, "--no-psqlrc", "-At", "-c", $sqlUsuarios))
if ($LASTEXITCODE -ne 0) {
    Mal "no se pudo leer auth.users"
    $csv | Select-Object -Last 8 | ForEach-Object { Write-Host "      $_" }
    $problemas++
} else {
    $csv | Set-Content -Path (Join-Path $Destino $nombreCsv) -Encoding UTF8
    $cuantas = [math]::Max(0, ($csv | Measure-Object).Count - 1)
    if ($cuantas -eq 0) {
        Mal "$nombreCsv salio sin ninguna cuenta"
        Decir "Eso no puede ser: la version anterior tiene cuentas en uso."
        $problemas++
    } else {
        Bien "$nombreCsv - $cuantas cuenta(s)"
        # Los correos, para que se vea con los ojos que estan las tres.
        # El hash de la contrasenia es la segunda columna y NO se imprime.
        $csv | Select-Object -Skip 1 | ForEach-Object {
            $correo = ($_ -split ',')[1]
            Write-Host "        - $correo"
        }
    }
}

# -------------------------- 6b - el esquema en texto, para comparar
#
# No es para restaurar: es para poder poner los dos esquemas uno al
# lado del otro antes de importar. La 3.0 agrego tablas y pudo cambiar
# alguna columna; si algo no encaja, conviene verlo leyendo un archivo
# y no a mitad de un restore.
$nombreEsquema = "esquema_$fecha.sql"
Paso "4 - el esquema en texto (para comparar, no para restaurar)..." @(
    "pg_dump", $conexion,
    "--schema-only", "--no-owner", "--no-privileges",
    "--schema=public",
    "--file=/salida/$nombreEsquema"
) $nombreEsquema | Out-Null

# -------------------------- 7 - los conteos, ANTES de importar
#
# `query_to_xml` arma el count de cada tabla sin que haya que escribir
# la lista a mano: una tabla que exista alla y no sepamos que existe
# aparece igual.
$sqlConteos = @"
select table_name as tabla,
       (xpath('/row/c/text()',
              query_to_xml(format('select count(*) as c from %I.%I', table_schema, table_name),
                           false, true, '')))[1]::text::bigint as filas
from information_schema.tables
where table_schema = 'public' and table_type = 'BASE TABLE'
union all
select 'auth.users', count(*) from auth.users
order by tabla
"@

$nombreConteos = "conteos_$fecha.txt"
Decir "5 - cuantas filas tiene cada tabla..."
$conteos = Correr "docker" ($comunes + @("psql", $conexion, "--no-psqlrc", "-c", $sqlConteos))
if ($LASTEXITCODE -ne 0) {
    Mal "no se pudieron contar las filas"
    $conteos | Select-Object -Last 8 | ForEach-Object { Write-Host "      $_" }
    $problemas++
} else {
    $conteos | Set-Content -Path (Join-Path $Destino $nombreConteos) -Encoding UTF8
    Bien $nombreConteos
    Write-Host ""
    $conteos | ForEach-Object { Write-Host "      $_" }

    # El control que detecta el dump vacio sin tener que abrirlo.
    #
    # `transactions` y `profiles` son las dos tablas que NO pueden estar
    # en cero en un sistema que se usa todos los dias. Si vienen en cero,
    # lo que paso es que las filas no se estan viendo --no que no existan--,
    # y seguir seria llevarse un archivo que parece bien y esta hueco.
    $enCero = @()
    foreach ($linea in $conteos) {
        if ($linea -match '^\s*(transactions|profiles|months|categories)\s*\|\s*(\d+)\s*$') {
            if ([int]$Matches[2] -eq 0) { $enCero += $Matches[1] }
        }
    }
    Write-Host ""
    if ($enCero.Count -gt 0) {
        Mal "estas tablas vinieron en CERO: $($enCero -join ', ')"
        Decir "En un sistema que se usa todos los dias eso no puede pasar."
        Decir "Lo mas probable es que las filas no se esten viendo, no que"
        Decir "no existan. El dump que quedo no sirve: no lo importes."
        $problemas++
    } else {
        Bien "las tablas principales traen filas: el dump no esta hueco"
    }
}

# -------------------------- 8 - que los dumps de verdad abran
Write-Host ""
Decir "Verificando que los archivos abran..."
foreach ($archivo in @($nombreDatos, $nombreUsuarios)) {
    if (-not (Test-Path (Join-Path $Destino $archivo))) { continue }
    $lista = Correr "docker" @(
        "run", "--rm", "-v", "${Destino}:/salida", $Imagen,
        "pg_restore", "--list", "/salida/$archivo"
    )
    if ($LASTEXITCODE -ne 0) {
        Mal "$archivo no se puede abrir: el archivo no sirve"
        $problemas++
    } else {
        $tablas = ($lista | Where-Object { $_ -match "TABLE DATA" } | Measure-Object).Count
        Bien "$archivo abre y trae $tablas tabla(s) con datos"
    }
}

Write-Host ""
Write-Host "==============================================================="
if ($problemas -eq 0) {
    Write-Host "  LISTO - los datos estan en $Destino" -ForegroundColor Green
    Write-Host ""
    Write-Host "  No se escribio nada en la version anterior."
    Write-Host ""
    Write-Host "  Esto trae LAS TRES CUENTAS. El 'Exportar JSON' de"
    Write-Host "  Ajustes -> Respaldo no reemplaza a esto: ese pasa por la"
    Write-Host "  API y devuelve solo la cuenta de quien lo toca. Sirve"
    Write-Host "  como control aparte, para leer tus numeros con los ojos"
    Write-Host "  y compararlos despues de importar."
} else {
    Write-Host "  FALLA - $problemas paso(s) no salieron" -ForegroundColor Red
    Write-Host "  No se escribio nada en la version anterior."
}
Write-Host "==============================================================="
Write-Host ""
exit $(if ($problemas -eq 0) { 0 } else { 1 })

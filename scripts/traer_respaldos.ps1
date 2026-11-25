<#
============================================================
  Trae los respaldos del servidor a esta PC · F18-T02

  Uso:
      powershell -ExecutionPolicy Bypass -File scripts\traer_respaldos.ps1

  POR QUE LA PC TIRA Y EL SERVIDOR NO EMPUJA

  Lo natural seria que el servidor, despues de respaldar, mande el
  archivo a esta PC. No se hace asi a proposito: para empujar, el
  servidor necesitaria una credencial de esta maquina guardada en el
  disco. Y entonces quien entre al servidor entra tambien aca.

  Tirando, la credencial vive en esta PC y el servidor no sabe que
  esta PC existe. Ademas, si la PC estuvo apagada tres dias, al
  prenderse se trae los tres: no hay nada que "se perdio porque nadie
  estaba escuchando".

  ACA NO SE BORRA NADA

  El servidor guarda 7 diarios, 4 semanales y 6 mensuales. Esta copia
  no aplica ninguna retencion: se queda con todo lo que bajo, incluso
  lo que el servidor ya tiro. Es la ultima linea, y 40 MB por dia son
  15 GB al ano. Si alguna vez molesta, se borran a mano los diarios
  viejos y se dejan los mensuales.

  QUE SE VERIFICA ACA

  Que el archivo bajado pese lo mismo que el del servidor y que
  empiece con `PGDMP`, la firma de un dump de Postgres. No se puede
  hacer mas sin instalar Postgres en Windows, y la verificacion de
  verdad —abrirlo y contar sus tablas— ya la hizo el servidor antes
  de dejarlo ahi.
============================================================
#>

[CmdletBinding()]
param(
    # Donde se guardan las copias. FUERA de la carpeta del proyecto:
    # si algun dia se borra el repositorio, los respaldos siguen.
    [string]$Destino = "D:\Respaldos\Epic_Wallet",

    # El nombre del servidor en ~/.ssh/config. No hace falta usuario
    # ni llave: ya estan declarados ahi.
    [string]$Servidor = "jarvis-vps",

    [string]$Remoto = "/opt/epic-wallet/respaldos"
)

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
#  Las herramientas
# ------------------------------------------------------------
# Se nombra el OpenSSH de Windows con su ruta completa. Hay otro
# dentro de Git y, segun el PATH que herede una tarea programada,
# podria tomar cualquiera de los dos. Que sea siempre el mismo evita
# un dia de desconcierto.
$SSH = Join-Path $env:SystemRoot "System32\OpenSSH\ssh.exe"
$SCP = Join-Path $env:SystemRoot "System32\OpenSSH\scp.exe"
if (-not (Test-Path $SSH)) { $SSH = "ssh" }
if (-not (Test-Path $SCP)) { $SCP = "scp" }

# BatchMode: si la llave no sirve o el servidor no esta en
# known_hosts, falla en el acto en lugar de quedarse esperando una
# respuesta que nadie va a escribir. Una tarea programada colgada es
# peor que una que fallo.
$OpcionesSsh = @("-o", "BatchMode=yes", "-o", "ConnectTimeout=20")

function Correr {
    <#
      Llama a un programa externo y devuelve su salida, juntando lo que
      escribio por error.

      Existe por una particularidad de PowerShell 5.1: con
      `$ErrorActionPreference = "Stop"`, redirigir el error de un .exe
      con `2>&1` convierte cada linea en un error terminante. Asi, un
      `ssh` que no resuelve el nombre del servidor cortaba el script
      con un volcado ilegible en lugar de llegar al mensaje claro de
      mas abajo. Aca adentro eso se apaga, y afuera sigue valiendo.
    #>
    param([string]$programa, [string[]]$argumentos)
    $previo = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    # `"$_"` aplana cada linea: de un error de un .exe deja el texto
    # que el programa escribio, sin el volcado de PowerShell alrededor.
    try   { return (& $programa @argumentos 2>&1 | ForEach-Object { "$_" }) }
    finally { $ErrorActionPreference = $previo }
}

# ------------------------------------------------------------
#  Registro
# ------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $Destino | Out-Null
$Registro = Join-Path $Destino "traer_respaldos.log"

function Escribir([string]$texto, [string]$color = "Gray") {
    $linea = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $texto
    Write-Host $linea -ForegroundColor $color
    Add-Content -Path $Registro -Value $linea -Encoding utf8
}

function EsUnDump([string]$ruta) {
    # Los cinco primeros bytes de un dump `-Fc` son «PGDMP».
    try {
        $f = [System.IO.File]::OpenRead($ruta)
        try {
            $b = New-Object byte[] 5
            if ($f.Read($b, 0, 5) -ne 5) { return $false }
            return ([System.Text.Encoding]::ASCII.GetString($b) -eq "PGDMP")
        } finally { $f.Close() }
    } catch { return $false }
}

Escribir "----- $Servidor -> $Destino"

# ------------------------------------------------------------
#  Que hay del otro lado
# ------------------------------------------------------------
# `%P` es la ruta relativa a la carpeta de respaldos («diario/x.dump»)
# y `%s` el tamanio. Con eso alcanza para decidir que falta y para
# comprobar despues que lo que llego esta entero.
$comando = "find '$Remoto' -type f -name '*.dump' -printf '%P\t%s\n'"
$crudo = Correr $SSH ($OpcionesSsh + @($Servidor, $comando))
if ($LASTEXITCODE -ne 0) {
    Escribir "FALLA - no se pudo consultar el servidor:" "Red"
    Escribir ($crudo | Out-String).Trim() "Red"
    exit 1
}

$remotos = @()
foreach ($linea in $crudo) {
    $partes = "$linea".Split("`t")
    if ($partes.Count -ne 2) { continue }
    $remotos += [pscustomobject]@{ Ruta = $partes[0]; Bytes = [int64]$partes[1] }
}

if ($remotos.Count -eq 0) {
    Escribir "FALLA - el servidor no tiene ningun .dump. Reviselo." "Red"
    exit 1
}

# ------------------------------------------------------------
#  Bajar lo que falte
# ------------------------------------------------------------
$bajados = 0
$fallados = 0

foreach ($r in $remotos) {
    $local = Join-Path $Destino ($r.Ruta -replace "/", "\")

    # Ya esta y pesa lo mismo: no se vuelve a bajar. Asi una PC que
    # estuvo una semana apagada se trae la semana y nada mas.
    if ((Test-Path $local) -and ((Get-Item $local).Length -eq $r.Bytes)) { continue }

    New-Item -ItemType Directory -Force -Path (Split-Path $local) | Out-Null

    # A un archivo temporal: si la bajada se corta a la mitad, no queda
    # un archivo con el nombre bueno y el contenido malo.
    $parcial = "$local.parcial"
    Correr $SCP ($OpcionesSsh + @("-q", "${Servidor}:$Remoto/$($r.Ruta)", $parcial)) | Out-Null

    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $parcial)) {
        Escribir "FALLA - no se pudo bajar $($r.Ruta)" "Red"
        Remove-Item $parcial -ErrorAction SilentlyContinue
        $fallados++
        continue
    }

    $tam = (Get-Item $parcial).Length
    if ($tam -ne $r.Bytes) {
        Escribir "FALLA - $($r.Ruta) llego incompleto: $tam de $($r.Bytes) bytes" "Red"
        Remove-Item $parcial -Force
        $fallados++
        continue
    }
    if (-not (EsUnDump $parcial)) {
        Escribir "FALLA - $($r.Ruta) no parece un dump de Postgres" "Red"
        Remove-Item $parcial -Force
        $fallados++
        continue
    }

    Move-Item $parcial $local -Force
    Escribir "OK - $($r.Ruta) ($([math]::Round($r.Bytes / 1MB, 2)) MB)" "Green"
    $bajados++
}

# La constancia del servidor, para poder comparar sin entrar por ssh.
$constancia = Join-Path $Destino "ultimo_servidor.json"
Correr $SCP ($OpcionesSsh + @("-q", "${Servidor}:$Remoto/ultimo.json", $constancia)) | Out-Null

# ------------------------------------------------------------
#  Aviso si el respaldo dejo de correr - F18-T06
# ------------------------------------------------------------
#
# Vive en su propio script para dos cosas: poder preguntarlo a mano
# ("¿es esta al dia el respaldo?") y poder PROBAR que el aviso salta,
# pasandole una constancia inventada. Esperar a que el respaldo falle
# de verdad no es una prueba.
$revisor = Join-Path $PSScriptRoot "revisar_respaldo.ps1"
$problema = $false
if (Test-Path $revisor) {
    & $revisor -Constancia $constancia | ForEach-Object { Escribir $_ }
    if ($LASTEXITCODE -ne 0) { $problema = $true }
} else {
    Escribir "FALLA - no se encontro revisar_respaldo.ps1" "Red"
    $problema = $true
}

# ------------------------------------------------------------
#  Cierre
# ------------------------------------------------------------
$total = (Get-ChildItem $Destino -Recurse -Filter "*.dump" | Measure-Object -Property Length -Sum)
$resumen = "{0} nuevo(s), {1} fallado(s). En esta PC: {2} archivos, {3} MB." -f `
    $bajados, $fallados, $total.Count, [math]::Round($total.Sum / 1MB, 1)

if ($fallados -gt 0) {
    Escribir "TERMINO CON FALLAS - $resumen" "Red"
    exit 1
}

if ($problema) {
    # Que no haya nada nuevo esta bien si ya se corrio hoy. Que haga
    # dias que el servidor no toma un respaldo, no.
    Escribir "TERMINO CON AVISO - $resumen" "Red"
    exit 2
}

Escribir "LISTO - $resumen" "Green"
exit 0

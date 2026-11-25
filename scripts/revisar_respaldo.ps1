# ============================================================
#  Avisa si el respaldo dejo de correr - F18-T06
#
#      .\scripts\revisar_respaldo.ps1
#      .\scripts\revisar_respaldo.ps1 -Constancia otro.json -MaximoHoras 1
#
#  Mira la constancia que dejo `respaldo.sh` en el servidor y que
#  `traer_respaldos.ps1` baja a esta PC, y decide una sola cosa: si hay
#  una copia fresca de los datos o no.
#
#  POR QUE EL AVISO VIVE ACA Y NO SOLO EN /api/health
#
#  El endpoint tiene el dato, pero Gustavo no entra a mirarlo y lo dijo
#  con todas las letras. Un aviso que nadie ve no es un aviso.
#
#  `traer_respaldos.ps1` ya corre todos los dias en SU maquina a las
#  08:00: es el unico lugar del sistema que lo mira a el todos los
#  dias, asi que es donde el aviso tiene que aparecer. Este script es
#  el que lo da, y esta separado para poder correrlo a mano y para
#  poder probarlo contra una constancia inventada --que es como se
#  comprueba que un aviso salta, porque esperar a que el respaldo
#  falle de verdad no es una prueba.
#
#  AVISA DE TRES FORMAS, porque cada una falla distinto:
#    1. una notificacion de Windows: se ve si hay sesion abierta
#    2. un archivo en la carpeta de respaldos: se ve siempre
#    3. codigo de salida 2: el Programador de tareas lo muestra como
#       "ultimo resultado de la ejecucion"
# ============================================================

[CmdletBinding()]
param(
    [string]$Constancia  = "D:\Respaldos\Epic_Wallet\ultimo_servidor.json",
    [double]$MaximoHoras = 48,
    [switch]$SinNotificar
)

$ErrorActionPreference = "Stop"

# Donde se deja la marca: al lado de la constancia, que es la carpeta
# de respaldos.
$carpeta = Split-Path -Parent $Constancia
$marca = Join-Path $carpeta "RESPALDO_ATRASADO.txt"

function Avisar {
    param([string]$titulo, [string]$texto)
    if ($SinNotificar) { return }
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        Add-Type -AssemblyName System.Drawing -ErrorAction Stop
        $globo = New-Object System.Windows.Forms.NotifyIcon
        $globo.Icon = [System.Drawing.SystemIcons]::Warning
        $globo.BalloonTipIcon = "Warning"
        $globo.BalloonTipTitle = $titulo
        $globo.BalloonTipText = $texto
        $globo.Visible = $true
        $globo.ShowBalloonTip(20000)
        Start-Sleep -Seconds 12
        $globo.Dispose()
    } catch {
        # Sin sesion interactiva no hay notificacion que mostrar. No es
        # un problema: para eso estan el archivo y el codigo de salida.
    }
}

# ------------------------------------------------------------
#  El veredicto
# ------------------------------------------------------------
#
# Las cuatro razones se miran por separado porque fallan por motivos
# distintos, y la segunda es la que mas engana: una constancia de un
# respaldo que no se pudo abrir da tranquilidad sin darla.
$problema = $null
$horas = $null

if (-not (Test-Path $Constancia)) {
    $problema = "no hay constancia de ningun respaldo"
} else {
    $c = $null
    try { $c = Get-Content $Constancia -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $c = $null }

    if (-not $c) {
        $problema = "la constancia no se puede leer"
    } elseif ($c.verificado -ne $true) {
        $problema = "el ultimo respaldo NO quedo verificado"
    } elseif (-not $c.fecha) {
        $problema = "la constancia no dice cuando se tomo"
    } else {
        try {
            $cuando = [datetimeoffset]::Parse($c.fecha)
            $horas = [math]::Round(([datetimeoffset]::Now - $cuando).TotalHours, 1)
            if ($horas -lt -0.5) {
                # Una fecha en el futuro es un reloj mal puesto de algun
                # lado. No se da por bueno: el respaldo podria ser de
                # cualquier momento.
                $problema = "la constancia dice que el respaldo es del futuro (reloj mal puesto)"
            } elseif ($horas -gt $MaximoHoras) {
                $problema = "hace $horas horas que no hay un respaldo nuevo"
            }
        } catch {
            $problema = "la constancia tiene una fecha ilegible: $($c.fecha)"
        }
    }
}

# ------------------------------------------------------------
#  Avisar, o levantar el aviso
# ------------------------------------------------------------
if ($problema) {
    Write-Host "  AVISO - $problema" -ForegroundColor Red

    $texto = @(
        "EPIC WALLET - EL RESPALDO NO ESTA AL DIA",
        "",
        "Problema: $problema",
        "Revisado: $(Get-Date -Format 'yyyy-MM-dd HH:mm')",
        "",
        "QUE HACER: entrar al servidor y correrlo a mano.",
        "",
        "    ssh jarvis-vps",
        "    cd /opt/epic-wallet && ./scripts/respaldo.sh",
        "",
        "Si eso funciona, lo que fallo es la tarea nocturna (3:15).",
        "Si no funciona, el mensaje va a decir por que.",
        "",
        "Este archivo se borra solo en cuanto el respaldo vuelve a",
        "estar al dia. Mientras exista, no hay copia fresca de los",
        "datos."
    ) -join "`r`n"

    Set-Content -Path $marca -Value $texto -Encoding UTF8
    Write-Host "  se dejo la marca en $marca" -ForegroundColor Yellow
    Avisar "Epic Wallet: el respaldo no esta al dia" $problema
    exit 2
}

Write-Host "  OK - ultimo respaldo: hace $horas horas, verificado" -ForegroundColor Green
if (Test-Path $marca) {
    Remove-Item $marca -Force
    Write-Host "  el respaldo volvio a estar al dia: se saco la marca" -ForegroundColor Green
}
exit 0

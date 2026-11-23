<#
============================================================
  Programa la bajada diaria de respaldos · F18-T02

  Uso (una sola vez):
      powershell -ExecutionPolicy Bypass -File scripts\instalar_tarea_respaldos.ps1

  Para ver que quedo:   Get-ScheduledTask "Epic Wallet - traer respaldos"
  Para correrla ahora:  Start-ScheduledTask "Epic Wallet - traer respaldos"
  Para sacarla:         Unregister-ScheduledTask "Epic Wallet - traer respaldos"

  POR QUE A LAS 8 DE LA MANIANA

  El servidor respalda a las 3:15. A las 8 el archivo del dia ya
  existe hace rato y la PC suele estar prendida. No importa si no
  esta: `StartWhenAvailable` hace que la tarea corra en cuanto se
  prenda, y el script se trae todos los dias que falten de una.
============================================================
#>

[CmdletBinding()]
param(
    [string]$Nombre = "Epic Wallet - traer respaldos",
    [string]$Hora = "08:00"
)

$ErrorActionPreference = "Stop"

$Script = Join-Path $PSScriptRoot "traer_respaldos.ps1"
if (-not (Test-Path $Script)) { throw "no esta $Script" }

$accion = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$Script`""

$disparador = New-ScheduledTaskTrigger -Daily -At $Hora

$opciones = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

# `-Force` reemplaza la tarea si ya existia: reinstalar es idempotente.
Register-ScheduledTask `
    -TaskName $Nombre `
    -Action $accion `
    -Trigger $disparador `
    -Settings $opciones `
    -Description "Se trae los respaldos verificados de Epic Wallet desde el servidor de Contabo. F18-T02." `
    -Force | Out-Null

Write-Host "Programada: '$Nombre', todos los dias a las $Hora." -ForegroundColor Green
Write-Host "Si la PC estaba apagada a esa hora, corre al prenderse." -ForegroundColor Gray

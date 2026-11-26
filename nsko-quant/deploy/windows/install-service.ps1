<#
  NSKO QUANT engine as a Windows service, using NSSM (the Non-Sucking Service Manager).
  NSSM licence: public domain (https://nssm.cc). It is free to use and to ship.

  Run in an ADMIN PowerShell:
    powershell -ExecutionPolicy Bypass -File install-service.ps1
    powershell -ExecutionPolicy Bypass -File install-service.ps1 -Uninstall

  Keep-awake: the engine itself calls SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED |
  ES_AWAYMODE_REQUIRED) while it runs, so Windows will not sleep. Turning the screen off is fine.
#>
param(
  [string]$EngineExe = "$env:ProgramFiles\NSKO QUANT\engine\nsko-quant-engine.exe",
  [string]$NssmPath  = "$PSScriptRoot\nssm.exe",
  [string]$DataDir   = "$env:APPDATA\NSKO QUANT",
  [switch]$Uninstall
)
$ErrorActionPreference = "Stop"
$svc = "NSKOQuantEngine"
$wd  = "NSKOQuantWatchdog"

if (-not (Test-Path $NssmPath)) {
  $found = Get-Command nssm.exe -ErrorAction SilentlyContinue
  if ($found) { $NssmPath = $found.Source }
  else {
    Write-Host "nssm.exe not found. Download NSSM 2.24 from https://nssm.cc/download (win64\nssm.exe)"
    Write-Host "and put nssm.exe next to this script, or install it with: winget install NSSM.NSSM"
    exit 1
  }
}

if ($Uninstall) {
  & $NssmPath stop $wd 2>$null; & $NssmPath remove $wd confirm 2>$null
  & $NssmPath stop $svc 2>$null; & $NssmPath remove $svc confirm
  Write-Host "Removed."; exit 0
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
& $NssmPath install $svc $EngineExe
& $NssmPath set $svc DisplayName "NSKO QUANT engine"
& $NssmPath set $svc Description "NSKO QUANT trading engine (by NSKO Solutions). Localhost only."
& $NssmPath set $svc AppDirectory (Split-Path $EngineExe)
& $NssmPath set $svc AppEnvironmentExtra "NSQ_DATA=$DataDir"
& $NssmPath set $svc Start SERVICE_AUTO_START
& $NssmPath set $svc AppExit Default Restart
& $NssmPath set $svc AppRestartDelay 5000
& $NssmPath set $svc AppStdout "$DataDir\service.out.log"
& $NssmPath set $svc AppStderr "$DataDir\service.err.log"
& $NssmPath set $svc AppRotateFiles 1
& $NssmPath set $svc AppRotateBytes 5000000

& $NssmPath install $wd $EngineExe "--watchdog"
& $NssmPath set $wd DisplayName "NSKO QUANT watchdog"
& $NssmPath set $wd AppEnvironmentExtra "NSQ_DATA=$DataDir"
& $NssmPath set $wd Start SERVICE_AUTO_START
& $NssmPath set $wd AppExit Default Restart

# Recover automatically if the service manager itself sees a crash.
sc.exe failure $svc reset= 0 actions= restart/5000/restart/5000/restart/5000 | Out-Null

& $NssmPath start $svc
& $NssmPath start $wd
Write-Host "Installed. Check: Get-Service $svc ; then open http://127.0.0.1:8787/health"

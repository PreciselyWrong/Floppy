[CmdletBinding()]
param(
    [switch]$Dummy,
    [switch]$NonInteractive,
    [switch]$Plan
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$ComposeFile = Join-Path $ProjectRoot "scripts/dev-publish/compose.dev.yml"

if ($Dummy) {
    throw "Ce projet n'a pas de données de démonstration."
}

if ($Plan) {
    Write-Output "Mode : données locales isolées"
    Write-Output "Prérequis : Docker avec Compose"
    Write-Output "Services : Redis puis Floppy"
    Write-Output "Commande : docker compose -f scripts/dev-publish/compose.dev.yml up --build"
    Write-Output "Vérification : http://localhost:8299/health/"
    exit 0
}

Set-Location $ProjectRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker avec Compose est requis."
}

& docker compose -f $ComposeFile up --detach --build
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

for ($attempt = 0; $attempt -lt 90; $attempt++) {
    $health = & docker inspect floppy-dev --format "{{if .State.Health}}{{.State.Health.Status}}{{end}}" 2>$null
    if ($LASTEXITCODE -eq 0 -and $health -eq "healthy") {
        Write-Output "DEV_READY http://localhost:8299"
        & docker compose -f $ComposeFile logs --follow floppy
        exit $LASTEXITCODE
    }
    Start-Sleep -Seconds 2
}

& docker compose -f $ComposeFile logs --tail 200 floppy
Write-Error "Floppy n'est pas devenu sain sur http://localhost:8299."
exit 3

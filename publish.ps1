[CmdletBinding()]
param(
    [switch]$NonInteractive,
    [switch]$Plan,
    [switch]$Confirm,
    [string[]]$Destination = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$AllowedDestinations = @("ghcr", "unraid")
$SelectedDestinations = if (@($Destination).Count -gt 0) { @($Destination) } else { $AllowedDestinations }

foreach ($selected in $SelectedDestinations) {
    if ($selected -notin $AllowedDestinations) {
        Write-Error "Destination inconnue : $selected" -ErrorAction Continue
        Write-Output "PUBLISH_FAILED"
        exit 2
    }
}

Set-Location $ProjectRoot
$CommitSha = (& git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$ImmutableImage = "ghcr.io/preciselywrong/floppy:sha-$CommitSha"

if ($Plan) {
    Write-Output "Publication prête"
    Write-Output "Version : $CommitSha"
    Write-Output "Destinations : $($SelectedDestinations -join ', ')"
    Write-Output "Vérifications : branche custom, arbre propre, tests GitHub, smoke Docker"
    Write-Output "Construction : Linux AMD64 et ARM64"
    Write-Output "Image : $ImmutableImage"
    Write-Output "Secrets requis : GITHUB_TOKEN fourni par GitHub ; configuration privée conservée sur Unraid"
    Write-Output "Activation : sauvegarde, remplacement du conteneur Floppy, contrôle de santé"
    Write-Output "Retour : ghcr.io/dannyvfilms/floppy:latest et sauvegarde pre-custom"
    exit 0
}

if ($NonInteractive -and -not $Confirm) {
    Write-Error "La publication non interactive exige -Confirm." -ErrorAction Continue
    Write-Output "PUBLISH_FAILED"
    exit 2
}

if (-not $NonInteractive) {
    Write-Output "Publication de $CommitSha vers $($SelectedDestinations -join ', ')."
    Write-Output "Les tests et la construction seront lancés avant l'envoi."
    $answer = Read-Host "Publier maintenant ? [o/N]"
    if ($answer -notin @("o", "O", "oui", "Oui")) { exit 0 }
}

try {
    $branch = (& git branch --show-current).Trim()
    if ($branch -ne "custom") { throw "La publication doit partir de custom." }
    if (& git status --porcelain) { throw "L'arbre de travail doit être propre." }

    & git diff --check upstream/latest...HEAD
    if ($LASTEXITCODE -ne 0) { exit 3 }

    if ($SelectedDestinations -contains "ghcr") {
        & git push --set-upstream origin custom
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    $credentialLines = "protocol=https`nhost=github.com`n`n" | git credential fill
    if ($LASTEXITCODE -ne 0) { throw "Les identifiants GitHub sont indisponibles." }
    $GitHubToken = $null
    foreach ($line in $credentialLines) {
        if ($line -match "^password=(.*)$") { $GitHubToken = $matches[1] }
    }
    $credentialLines = $null
    if ([string]::IsNullOrWhiteSpace($GitHubToken)) {
        throw "Le jeton GitHub est indisponible."
    }
    $GitHubHeaders = @{
        Accept = "application/vnd.github+json"
        Authorization = "Bearer $GitHubToken"
        "X-GitHub-Api-Version" = "2022-11-28"
    }

    $api = "https://api.github.com/repos/PreciselyWrong/Floppy/actions/runs?branch=custom&per_page=30"
    $run = $null
    for ($attempt = 0; $attempt -lt 90; $attempt++) {
        $response = Invoke-RestMethod -Uri $api -Headers $GitHubHeaders
        $run = $response.workflow_runs |
            Where-Object { $_.head_sha -eq $CommitSha -and $_.name -eq "Custom Docker Image" } |
            Select-Object -First 1
        if ($null -ne $run) {
            Write-Output "GitHub Actions : $($run.status) $($run.html_url)"
            if ($run.status -eq "completed") { break }
        }
        Start-Sleep -Seconds 30
    }
    $GitHubToken = $null
    if ($null -eq $run -or $run.status -ne "completed" -or $run.conclusion -ne "success") {
        throw "La construction GitHub n'a pas réussi pour $CommitSha."
    }

    if ($SelectedDestinations -contains "unraid") {
        $deployScript = Get-Content -Raw (Join-Path $ProjectRoot "scripts/dev-publish/deploy-unraid.sh")
        $deployScript | & ssh unraid-server "sh -s -- deploy '$ImmutableImage' '$CommitSha'"
        if ($LASTEXITCODE -ne 0) { exit 4 }
    }

    Write-Output "PUBLISH_OK image=$ImmutableImage"
    exit 0
}
catch {
    Write-Error $_
    Write-Output "PUBLISH_FAILED"
    exit 4
}

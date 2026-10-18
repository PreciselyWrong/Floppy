[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^(feat|fix)/[a-z0-9][a-z0-9-]*$')]
    [string]$Branch,

    [switch]$Plan
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$currentBranch = (& git -C $repositoryRoot branch --show-current).Trim()
$commonGitDir = (& git -C $repositoryRoot rev-parse --git-common-dir).Trim()
if (-not [System.IO.Path]::IsPathRooted($commonGitDir)) {
    $commonGitDir = [System.IO.Path]::GetFullPath(
        (Join-Path $repositoryRoot $commonGitDir)
    )
}
$primaryWorktreeRoot = Split-Path $commonGitDir -Parent
$worktreesRoot = Join-Path $primaryWorktreeRoot ".worktrees"
$worktreeName = $Branch.Replace("/", "-")
$worktreePath = Join-Path $worktreesRoot $worktreeName

Write-Output "Branch: $Branch"
Write-Output "Base: upstream/latest"
Write-Output "Worktree: $worktreePath"

if ($Plan) {
    Write-Output "PLAN_OK"
    exit 0
}

if ($currentBranch -ne "custom") {
    throw "Run this command from the custom branch, not $currentBranch."
}

if (& git -C $repositoryRoot status --porcelain) {
    throw "The custom worktree must be clean before creating a feature worktree."
}

& git -C $repositoryRoot fetch upstream latest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& git -C $repositoryRoot show-ref --verify --quiet "refs/heads/$Branch"
if ($LASTEXITCODE -eq 0) {
    throw "Branch $Branch already exists."
}
if (Test-Path -LiteralPath $worktreePath) {
    throw "Worktree path already exists: $worktreePath"
}

New-Item -ItemType Directory -Force -Path $worktreesRoot | Out-Null

$excludePath = Join-Path $commonGitDir "info/exclude"
$excludeEntries = @("/.worktrees/", "/docs/agents/feature_delivery.md")
$excludeLines = if (Test-Path -LiteralPath $excludePath) {
    @(Get-Content -LiteralPath $excludePath)
} else {
    @()
}
foreach ($excludeEntry in $excludeEntries) {
    if ($excludeEntry -notin $excludeLines) {
        Add-Content -LiteralPath $excludePath -Value $excludeEntry
    }
}

& git -C $repositoryRoot worktree add -b $Branch $worktreePath upstream/latest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Copy-Item -LiteralPath (Join-Path $repositoryRoot "AGENTS.md") -Destination (Join-Path $worktreePath "AGENTS.md") -Force
& git -C $worktreePath update-index --skip-worktree AGENTS.md
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$guideDestination = Join-Path $worktreePath "docs/agents/feature_delivery.md"
Copy-Item -LiteralPath (Join-Path $repositoryRoot "docs/agents/feature_delivery.md") -Destination $guideDestination -Force

Write-Output "WORKTREE_OK path=$worktreePath branch=$Branch"

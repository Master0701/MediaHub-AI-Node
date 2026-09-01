param(
    [string]$Tag,
    [switch]$SkipTests,
    [switch]$NoPush,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$argsList = @(".\release_node.py")

if ($Tag) {
    $argsList += @("--tag", $Tag)
}

if ($SkipTests) {
    $argsList += "--skip-tests"
}

if ($NoPush) {
    $argsList += "--no-push"
}

if ($Yes) {
    $argsList += "--yes"
}

& python @argsList

if ($LASTEXITCODE -ne 0) {
    throw "Release-Assistent wurde mit Fehlercode $LASTEXITCODE beendet."
}

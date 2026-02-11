Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot
try {
    npm install
    vsce package
}
finally {
    Pop-Location
}

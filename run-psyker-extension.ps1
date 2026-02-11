# Run VS Code with the Psyker extension loaded (development mode).
# Double-click this file or run: .\run-psyker-extension.ps1

$repoRoot = $PSScriptRoot
$extPath = Join-Path $repoRoot "vscode-extension"

& code $repoRoot --extensionDevelopmentPath=$extPath

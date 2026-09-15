$ErrorActionPreference = "Stop"

$repoRoot = git rev-parse --show-toplevel
if (-not $repoRoot) {
    throw "Execute este script dentro do repositorio NFE_SCANNER."
}

Set-Location -LiteralPath $repoRoot

if (-not (Test-Path -LiteralPath ".githooks/pre-commit")) {
    throw "Hook .githooks/pre-commit nao encontrado. Atualize o repositorio."
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python nao encontrado no PATH. Instale ou configure o Python antes de continuar."
}

git config core.hooksPath .githooks
$configuredPath = git config --get core.hooksPath

if ($configuredPath -ne ".githooks") {
    throw "Nao foi possivel ativar os hooks Git."
}

Write-Host ""
Write-Host "Protecoes Git configuradas com sucesso." -ForegroundColor Green
Write-Host ""
Write-Host "Aplicativo Android:" -ForegroundColor Cyan
Write-Host "  main -> producao"
Write-Host ""
Write-Host "Painel/backend:" -ForegroundColor Cyan
Write-Host "  dev_testes -> homologacao -> main -> producao"
Write-Host ""
Write-Host "Execute este configurador uma vez em cada novo clone ou computador."

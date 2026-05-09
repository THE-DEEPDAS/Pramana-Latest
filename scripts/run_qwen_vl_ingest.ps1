$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:PYTHONPATH = Join-Path $repoRoot "service\src"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"

Set-Location $repoRoot

$python = Join-Path $env:CONDA_PREFIX "python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

& $python -m powermind_rag.cli ingest-dir `
    (Join-Path $repoRoot "service\data") `
    --doc-type "PDF document collection" `
    --section "service data folder" `
    --context "document text, native PDF tables, layout-derived numeric facts, financial figures, charts, infographics, and page visuals"

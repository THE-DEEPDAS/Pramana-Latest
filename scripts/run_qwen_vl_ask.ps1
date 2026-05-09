param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Question
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:PYTHONPATH = Join-Path $repoRoot "service\src"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:POWERMIND_GENERATION_PROVIDER = "nvidia"
$env:POWERMIND_IMAGE_PROVIDER = "qwen_vl"
$env:POWERMIND_ENABLE_QUERY_VISUAL_RETRIEVAL = "0"
$env:POWERMIND_ENABLE_QUERY_VLM_FALLBACK = "1"
$env:POWERMIND_RELEVANCE_PROVIDER = "lexical"
$env:POWERMIND_DEVICE = "cuda"
$env:QWEN_VL_DEVICE = "cuda"
$env:POWERMIND_INCLUDE_PAGE_IMAGES_IN_ANSWERS = "0"

Set-Location $repoRoot

$python = Join-Path $env:CONDA_PREFIX "python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

& $python -m powermind_rag.cli ask $Question --show-timings

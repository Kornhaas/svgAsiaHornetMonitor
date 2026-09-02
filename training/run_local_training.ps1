[CmdletBinding()]
param(
    [string]$PiHost = "hornet@hornet.local",
    [string]$PiProject = "/home/hornet/svgAsiaHornetMonitor",
    [ValidateRange(1, 10000)]
    [int]$Epochs = 50,
    [ValidateRange(32, 4096)]
    [int]$ImageSize = 640,
    [switch]$SkipDownload,
    [switch]$SkipImport,
    [string]$IdentityFile = (Join-Path $env:USERPROFILE ".ssh\asia_hornet_monitor_ed25519")
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$gpuPython = Join-Path $repositoryRoot ".venv-gpu\Scripts\python.exe"
$eventsDirectory = Join-Path $repositoryRoot "data\events"

if (-not (Test-Path $gpuPython)) {
    throw "GPU environment not found. Follow training/README.md once to create .venv-gpu."
}
if (-not (Test-Path -LiteralPath $IdentityFile)) {
    throw "Pi SSH key not found. Run training/initialize_pi_training_key.ps1 once, or pass -IdentityFile."
}

Set-Location $repositoryRoot
$identityPath = (Resolve-Path -LiteralPath $IdentityFile).Path
$sshOptions = @("-i", $identityPath, "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes")

if (-not $SkipDownload) {
    New-Item -ItemType Directory -Force $eventsDirectory | Out-Null
    & scp @sshOptions -r "${PiHost}:$PiProject/data/events/." "$eventsDirectory\"
    if ($LASTEXITCODE -ne 0) {
        throw "Copying event images from the Pi failed."
    }
    & scp @sshOptions "${PiHost}:$PiProject/data/annotations.jsonl" (Join-Path $repositoryRoot "data")
    if ($LASTEXITCODE -ne 0) {
        throw "Copying annotations from the Pi failed."
    }
}

& uv run python (Join-Path $PSScriptRoot "export_yolo.py")
if ($LASTEXITCODE -ne 0) {
    throw "YOLO export failed."
}

$dataset = Get-ChildItem (Join-Path $repositoryRoot "data\datasets") -Directory |
    Sort-Object Name -Descending |
    ForEach-Object { Join-Path $_.FullName "dataset.yaml" } |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1
if (-not $dataset) {
    throw "No exported dataset.yaml was found."
}

$runName = "local_" + (Get-Date -Format "yyyyMMdd_HHmmss")
& $gpuPython (Join-Path $PSScriptRoot "train_local.py") `
    --dataset $dataset --epochs $Epochs --image-size $ImageSize --device 0 --name $runName
if ($LASTEXITCODE -ne 0) {
    throw "GPU training failed."
}

$model = Join-Path $repositoryRoot "data\models\local-experiments\$runName\weights\best.pt"
& $gpuPython (Join-Path $PSScriptRoot "evaluate_model.py") $model --dataset $dataset --device 0
if ($LASTEXITCODE -ne 0) {
    throw "Model evaluation failed."
}

if (-not $SkipImport) {
    & (Join-Path $PSScriptRoot "import_model_to_pi.ps1") `
        -Model $model -Version $runName.Substring(6) -PiHost $PiHost -PiProject $PiProject `
        -IdentityFile $identityPath
    if ($LASTEXITCODE -ne 0) {
        throw "Importing the trained model to the Pi failed."
    }
}

Write-Host ""
Write-Host "Completed local training." -ForegroundColor Green
Write-Host "Dataset: $dataset"
Write-Host "Model:   $model"
if ($SkipImport) {
    Write-Host "Model import was skipped." -ForegroundColor Yellow
} else {
    Write-Host "The model was imported to the Pi. Activate it manually in Model & training."
}

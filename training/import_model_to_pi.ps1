[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Model,
    [Parameter(Mandatory)]
    [ValidatePattern("^\d{8}_\d{6}$")]
    [string]$Version,
    [string]$PiHost = "hornet@hornet.local",
    [string]$PiProject = "/home/hornet/svgAsiaHornetMonitor",
    [string]$IdentityFile
)

$ErrorActionPreference = "Stop"
$modelFile = (Resolve-Path $Model).Path
$remoteVersionDirectory = "$PiProject/data/models/$Version"
$remoteModel = "$remoteVersionDirectory/weights/best.pt"
$runDirectory = Split-Path (Split-Path $modelFile -Parent) -Parent
$resultsFile = Join-Path $runDirectory "results.csv"
$evaluation = @{}
if (Test-Path -LiteralPath $resultsFile) {
    $lastResult = Import-Csv -LiteralPath $resultsFile | Select-Object -Last 1
    $metricMap = @{
        "metrics/mAP50(B)" = "map50"
        "metrics/mAP50-95(B)" = "map50_95"
        "metrics/precision(B)" = "precision"
        "metrics/recall(B)" = "recall"
    }
    foreach ($source in $metricMap.Keys) {
        $value = $lastResult.$source
        if ($null -ne $value -and $value -ne "") {
            $evaluation[$metricMap[$source]] = [double]::Parse(
                $value, [Globalization.CultureInfo]::InvariantCulture
            )
        }
    }
}
$manifest = @{
    version = $Version
    model = $remoteModel
    source = "local-pc-import"
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    evaluation = $evaluation
} | ConvertTo-Json
$temporaryManifest = Join-Path ([System.IO.Path]::GetTempPath()) "hornet-model-$Version.json"
$sshOptions = @()
if ($IdentityFile) {
    $identityPath = (Resolve-Path -LiteralPath $IdentityFile).Path
    $sshOptions = @("-i", $identityPath, "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes")
}

try {
    [System.IO.File]::WriteAllText(
        $temporaryManifest, $manifest, [System.Text.UTF8Encoding]::new($false)
    )
    & ssh @sshOptions $PiHost "mkdir -p '$remoteVersionDirectory/weights'"
    if ($LASTEXITCODE -ne 0) {
        throw "Creating the model directory on the Pi failed."
    }
    & scp @sshOptions $modelFile "${PiHost}:$remoteModel"
    if ($LASTEXITCODE -ne 0) {
        throw "Copying best.pt to the Pi failed."
    }
    & scp @sshOptions $temporaryManifest "${PiHost}:$remoteVersionDirectory/model.json"
    if ($LASTEXITCODE -ne 0) {
        throw "Copying model metadata to the Pi failed."
    }
}
finally {
    Remove-Item -LiteralPath $temporaryManifest -Force -ErrorAction SilentlyContinue
}

Write-Host "Model $Version was imported. Select it on the Pi under Model & training, then use 'Use model' to activate it." -ForegroundColor Green
if ($evaluation.Count) {
    Write-Host "Imported evaluation metrics from $resultsFile." -ForegroundColor Green
} else {
    Write-Warning "No local results.csv was found; the Pi cannot display evaluation metrics for this import."
}

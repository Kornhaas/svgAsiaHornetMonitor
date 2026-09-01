[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Model,
    [Parameter(Mandatory)]
    [ValidatePattern("^\d{8}_\d{6}$")]
    [string]$Version,
    [string]$PiHost = "hornet@hornet.local",
    [string]$PiProject = "/home/hornet/svgAsiaHornetMonitor"
)

$ErrorActionPreference = "Stop"
$modelFile = (Resolve-Path $Model).Path
$remoteVersionDirectory = "$PiProject/data/models/$Version"
$remoteModel = "$remoteVersionDirectory/weights/best.pt"
$manifest = @{
    version = $Version
    model = $remoteModel
    source = "local-pc-import"
    created_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json
$temporaryManifest = Join-Path ([System.IO.Path]::GetTempPath()) "hornet-model-$Version.json"

try {
    [System.IO.File]::WriteAllText(
        $temporaryManifest, $manifest, [System.Text.UTF8Encoding]::new($false)
    )
    & ssh $PiHost "mkdir -p '$remoteVersionDirectory/weights'"
    if ($LASTEXITCODE -ne 0) {
        throw "Creating the model directory on the Pi failed."
    }
    & scp $modelFile "${PiHost}:$remoteModel"
    if ($LASTEXITCODE -ne 0) {
        throw "Copying best.pt to the Pi failed."
    }
    & scp $temporaryManifest "${PiHost}:$remoteVersionDirectory/model.json"
    if ($LASTEXITCODE -ne 0) {
        throw "Copying model metadata to the Pi failed."
    }
}
finally {
    Remove-Item -LiteralPath $temporaryManifest -Force -ErrorAction SilentlyContinue
}

Write-Host "Model $Version was imported. Select it on the Pi under Model & training, then use 'Use model' to activate it." -ForegroundColor Green

[CmdletBinding()]
param(
    [string]$PiHost = "hornet@hornet.local",
    [string]$IdentityFile = (Join-Path $env:USERPROFILE ".ssh\asia_hornet_monitor_ed25519")
)

$ErrorActionPreference = "Stop"
$sshDirectory = Split-Path -Parent $IdentityFile
$publicKeyFile = "$IdentityFile.pub"

if (-not (Test-Path -LiteralPath $IdentityFile)) {
    New-Item -ItemType Directory -Force $sshDirectory | Out-Null
    & ssh-keygen -t ed25519 -f $IdentityFile -N '""' -C "Asia Hornet Monitor training"
    if ($LASTEXITCODE -ne 0) {
        throw "Creating the local SSH key failed."
    }
}

$publicKey = (Get-Content -LiteralPath $publicKeyFile -Raw).Trim()
if (-not $publicKey.StartsWith("ssh-ed25519 ")) {
    throw "The local public key is not a valid ed25519 SSH key."
}

Write-Host "Enter the Pi password once to allow password-free training transfers." -ForegroundColor Yellow
$remoteCommand = "umask 077; mkdir -p ~/.ssh; touch ~/.ssh/authorized_keys; " +
    "cat >> ~/.ssh/authorized_keys; sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys; " +
    "chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys"
$publicKey | & ssh $PiHost $remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "Installing the training SSH key on the Pi failed."
}

Write-Host "SSH key installed. Future run_local_training.ps1 runs need no Pi password." -ForegroundColor Green

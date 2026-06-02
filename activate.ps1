# Custom activation script for the market_scanner conda environment in PowerShell.
# Run: .\activate.ps1

$envPrefix = "C:\Users\dmishra\.conda\envs\market_scanner"

if ($env:CONDA_PREFIX -eq $envPrefix) {
    Write-Host "Conda environment 'market_scanner' is already active." -ForegroundColor Green
    return
}

# Store old path to restore on deactivate
if (-not $env:_OLD_PATH) {
    $env:_OLD_PATH = $env:PATH
}

# Prepend virtual env paths
$env:PATH = "$envPrefix;$envPrefix\Scripts;$env:PATH"
$env:CONDA_PREFIX = $envPrefix
$env:CONDA_DEFAULT_ENV = "market_scanner"

# Backup prompt
if (-not (Get-Command -Name _old_prompt -ErrorAction SilentlyContinue)) {
    # Define a backup function for the prompt
    function _old_prompt { & $function:prompt }
}

# Define new prompt showing environment
function prompt {
    Write-Host "(market_scanner) " -NoNewline -ForegroundColor Green
    & $function:_old_prompt
}

# Define deactivate function
function global:deactivate {
    if ($env:_OLD_PATH) {
        $env:PATH = $env:_OLD_PATH
        Remove-Item env:_OLD_PATH
    }
    Remove-Item env:CONDA_PREFIX -ErrorAction SilentlyContinue
    Remove-Item env:CONDA_DEFAULT_ENV -ErrorAction SilentlyContinue
    
    # Restore old prompt
    if (Get-Command -Name _old_prompt -ErrorAction SilentlyContinue) {
        function prompt { & $function:_old_prompt }
        Remove-Item function:_old_prompt -ErrorAction SilentlyContinue
    }
    
    Write-Host "Conda environment 'market_scanner' deactivated." -ForegroundColor Yellow
}

Write-Host "Activated Conda environment: market_scanner" -ForegroundColor Green
Write-Host "Type 'deactivate' to exit the environment." -ForegroundColor Gray

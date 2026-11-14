# PokeMMO controller layout: one-command setup for Windows.
#   irm https://raw.githubusercontent.com/jordanallenlewis/pokemmo-controller/main/install.ps1 | iex
# Undo:
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/jordanallenlewis/pokemmo-controller/main/install.ps1))) -Uninstall
# Nothing to install first. Downloads this project (and, only if Python 3.9+ is
# missing, a private copy of Python via uv) into a temp folder, runs
# tools/setup.py, then deletes the temp folder.
param([switch]$Uninstall, [switch]$NoWheel, [switch]$SwitchPositional,
      [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$repo = 'jordanallenlewis/pokemmo-controller'
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("pokemmo-controller-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    Write-Host "Downloading pokemmo-controller..."
    $src = if ($env:POKEMMO_CONTROLLER_SRC) { $env:POKEMMO_CONTROLLER_SRC } else { "https://github.com/$repo/archive/refs/heads/main.zip" }
    Invoke-WebRequest $src -OutFile "$tmp\src.zip" -UseBasicParsing
    Expand-Archive "$tmp\src.zip" -DestinationPath $tmp
    $setup = Get-ChildItem $tmp -Recurse -Filter setup.py | Where-Object { $_.Directory.Name -eq 'tools' } | Select-Object -First 1

    $toolArgs = @()
    if ($Uninstall) { $toolArgs += '--uninstall' }
    if ($NoWheel) { $toolArgs += '--no-wheel' }
    if ($SwitchPositional) { $toolArgs += '--switch-positional' }
    if ($Rest) { $toolArgs += $Rest }

    # Use an existing Python 3.9+ if there is one (skips the Microsoft Store stub).
    $py = $null
    foreach ($c in @(@('py', '-3'), @('python'), @('python3'))) {
        try {
            $out = & $c[0] $c[1..9] -c "import sys; print(sys.version_info >= (3, 9))" 2>$null
            if ($LASTEXITCODE -eq 0 -and "$out".Trim() -eq 'True') { $py = $c; break }
        } catch { }
    }
    if ($py) {
        & $py[0] $py[1..9] $setup.FullName @toolArgs
    } else {
        Write-Host "Python not found: fetching a private copy just for this run..."
        $arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'aarch64' } else { 'x86_64' }
        Invoke-WebRequest "https://github.com/astral-sh/uv/releases/latest/download/uv-$arch-pc-windows-msvc.zip" -OutFile "$tmp\uv.zip" -UseBasicParsing
        Expand-Archive "$tmp\uv.zip" -DestinationPath "$tmp\uv"
        $env:UV_CACHE_DIR = "$tmp\uv-cache"
        $env:UV_PYTHON_INSTALL_DIR = "$tmp\uv-python"
        & "$tmp\uv\uv.exe" run --quiet --no-project --python 3.12 $setup.FullName @toolArgs
    }
    if ($LASTEXITCODE) { throw "setup exited with code $LASTEXITCODE" }
} finally {
    Set-Location $env:TEMP
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

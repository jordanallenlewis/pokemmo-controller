# PokeMMO controller layout: one-command setup for Windows.
# Install, or update to the newest version (run it again any time):
#   irm https://raw.githubusercontent.com/jordanallenlewis/pokemmo-controller/main/install.ps1 | iex
# Undo:
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/jordanallenlewis/pokemmo-controller/main/install.ps1))) -Uninstall
# Nothing to install first. Downloads this project (and, only if Python 3.9+ is
# missing, a private copy of Python via uv) into a temp folder, runs
# tools/setup.py, then deletes the temp folder. Works in Windows PowerShell 5.1
# and PowerShell 7; `irm | iex` is not blocked by the execution policy.
param([switch]$Uninstall, [switch]$NoWheel, [switch]$SwitchPositional, [switch]$Ui, [switch]$InstallUi,
      [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)

# Everything runs in its own scope so your PowerShell session is left as it was.
& {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    # .NET unzip: Expand-Archive is a script module that a strict execution policy blocks.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    function Expand-Zip([string]$Zip, [string]$To) { [IO.Compression.ZipFile]::ExtractToDirectory($Zip, $To) }

    function Get-File([string]$From, [string]$To) {
        if (Test-Path -LiteralPath $From) { Copy-Item -LiteralPath $From -Destination $To; return }
        for ($i = 1; ; $i++) {
            try { Invoke-WebRequest $From -OutFile $To -UseBasicParsing; return }
            catch {
                if ($i -ge 3) { throw "Could not download $From ($($_.Exception.Message)). Check your internet connection and try again." }
                Start-Sleep -Seconds (3 * $i)
            }
        }
    }

    $repo = 'jordanallenlewis/pokemmo-controller'
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ("pokemmo-controller-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    try {
        Write-Host "Downloading pokemmo-controller..."
        $src = if ($env:POKEMMO_CONTROLLER_SRC) { $env:POKEMMO_CONTROLLER_SRC } else { "https://github.com/$repo/archive/refs/heads/main.zip" }
        Get-File $src "$tmp\src.zip"
        Expand-Zip "$tmp\src.zip" "$tmp\src"
        $setup = Get-ChildItem "$tmp\src" -Recurse -Filter setup.py | Where-Object { $_.Directory.Name -eq 'tools' } | Select-Object -First 1
        if (-not $setup) { throw "The download was incomplete (no tools\setup.py). Try again." }

        $toolArgs = @()
        if ($Uninstall) { $toolArgs += '--uninstall' }
        if ($NoWheel) { $toolArgs += '--no-wheel' }
        if ($SwitchPositional) { $toolArgs += '--switch-positional' }
        if ($Ui) { $toolArgs += '--ui' }
        if ($InstallUi) { $toolArgs += '--install-ui' }
        if ($Rest) { $toolArgs += $Rest }

        # Use an existing Python 3.9+ if there is one (skips the Microsoft Store stub).
        $py = $null
        if ($env:POKEMMO_CONTROLLER_FORCE_UV -ne '1') {
            foreach ($c in @(@('py', '-3'), @('python'), @('python3'))) {
                try {
                    $out = & $c[0] $c[1..9] -c "import sys; print(sys.version_info >= (3, 9))" 2>$null
                    if ($LASTEXITCODE -eq 0 -and "$out".Trim() -eq 'True') { $py = $c; break }
                } catch { }
            }
        }
        if ($py) {
            & $py[0] $py[1..9] $setup.FullName @toolArgs
        } else {
            Write-Host "Python not found: fetching a private copy just for this run..."
            $arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'aarch64' } else { 'x86_64' }
            Get-File "https://github.com/astral-sh/uv/releases/latest/download/uv-$arch-pc-windows-msvc.zip" "$tmp\uv.zip"
            Expand-Zip "$tmp\uv.zip" "$tmp\uv"
            $env:UV_CACHE_DIR = "$tmp\uv-cache"
            $env:UV_PYTHON_INSTALL_DIR = "$tmp\uv-python"
            try {
                & "$tmp\uv\uv.exe" run --quiet --no-project --no-config --python 3.12 $setup.FullName @toolArgs
            } finally {
                Remove-Item Env:UV_CACHE_DIR, Env:UV_PYTHON_INSTALL_DIR -ErrorAction SilentlyContinue
            }
        }
        if ($LASTEXITCODE) { throw "Setup stopped (exit code $LASTEXITCODE): see the message above." }
    } finally {
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

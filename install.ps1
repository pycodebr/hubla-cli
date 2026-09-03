$ErrorActionPreference = "Stop"

$RepositoryUrl = "https://github.com/pycodebr/hubla-cli"
$Version = if ($env:HUBLA_CLI_VERSION) { $env:HUBLA_CLI_VERSION } else { "0.1.0" }
$PackageUrl = if ($env:HUBLA_CLI_PACKAGE_URL) {
    $env:HUBLA_CLI_PACKAGE_URL
} else {
    "$RepositoryUrl/archive/refs/tags/v$Version.zip"
}
$InstallRoot = if ($env:HUBLA_CLI_HOME) {
    $env:HUBLA_CLI_HOME
} else {
    Join-Path $env:LOCALAPPDATA "hubla-cli"
}
$BinDir = if ($env:HUBLA_CLI_BIN_DIR) {
    $env:HUBLA_CLI_BIN_DIR
} else {
    Join-Path $HOME ".local\bin"
}
$Agent = if ($env:HUBLA_CLI_AGENT) { $env:HUBLA_CLI_AGENT } else { "auto" }

function Write-Step([string]$Message) {
    Write-Host $Message -ForegroundColor Cyan
}

function Test-Python([string]$Executable, [string[]]$Prefix) {
    try {
        & $Executable @Prefix -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

$PythonExecutable = $null
$PythonPrefix = @()
if ($env:HUBLA_CLI_PYTHON) {
    $PythonExecutable = $env:HUBLA_CLI_PYTHON
    if (-not (Test-Python $PythonExecutable @())) {
        throw "HUBLA_CLI_PYTHON precisa apontar para Python 3.10 ou superior."
    }
}
if (-not $PythonExecutable -and (Get-Command py -ErrorAction SilentlyContinue)) {
    if (Test-Python "py" @("-3")) {
        $PythonExecutable = "py"
        $PythonPrefix = @("-3")
    }
}
if (-not $PythonExecutable -and (Get-Command python -ErrorAction SilentlyContinue)) {
    if (Test-Python "python" @()) {
        $PythonExecutable = "python"
    }
}

if (-not $PythonExecutable) {
    throw "Python 3.10 ou superior não foi encontrado. Instale o Python e tente novamente."
}

$VenvDir = Join-Path $InstallRoot "venv"
Write-Step "Instalando Hubla CLI em $InstallRoot"
New-Item -ItemType Directory -Force -Path $InstallRoot, $BinDir | Out-Null
& $PythonExecutable @PythonPrefix -m venv $VenvDir
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível criar o ambiente Python isolado."
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$CliExecutable = Join-Path $VenvDir "Scripts\hubla-cli.exe"
& $VenvPython -m pip install --disable-pip-version-check --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível preparar o instalador Python."
}
& $VenvPython -m pip install --disable-pip-version-check --upgrade $PackageUrl
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível instalar o Hubla CLI."
}

$ManagedMarker = "rem hubla-cli managed wrapper"
$Wrapper = '{0}{1}@echo off{1}"{2}" %*{1}' -f `
    $ManagedMarker, [Environment]::NewLine, $CliExecutable
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$WrapperPaths = @(
    (Join-Path $BinDir "hubla-cli.cmd"),
    (Join-Path $BinDir "hubla.cmd")
)
foreach ($WrapperPath in $WrapperPaths) {
    if (Test-Path $WrapperPath) {
        $ExistingWrapper = [System.IO.File]::ReadAllText($WrapperPath)
        if (-not $ExistingWrapper.StartsWith($ManagedMarker)) {
            throw "$WrapperPath já existe e não é gerenciado pelo Hubla CLI."
        }
    }
    [System.IO.File]::WriteAllText($WrapperPath, $Wrapper, $Utf8NoBom)
}

if ($env:HUBLA_CLI_SKIP_SKILL -ne "1") {
    Write-Step "Instalando a skill para agentes de IA"
    & $CliExecutable --json skill install --agent $Agent
    if ($LASTEXITCODE -ne 0) {
        throw "O CLI foi instalado, mas a skill precisa de revisão manual."
    }
}

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$UserEntries = @($UserPath -split ";" | Where-Object { $_ })
if ($UserEntries -notcontains $BinDir) {
    $UpdatedPath = if ($UserPath) { "$BinDir;$UserPath" } else { $BinDir }
    [Environment]::SetEnvironmentVariable("Path", $UpdatedPath, "User")
}
if (@($env:Path -split ";") -notcontains $BinDir) {
    $env:Path = "$BinDir;$env:Path"
}

Write-Host "Hubla CLI instalado." -ForegroundColor Green
Write-Host "Executável: $(Join-Path $BinDir 'hubla-cli.cmd')"
Write-Host "Próximo passo: hubla-cli login"

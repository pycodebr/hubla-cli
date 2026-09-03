$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion -lt [Version]"5.1") {
    throw "PowerShell 5.1 ou superior é necessário."
}

function Enable-Tls12 {
    [Net.ServicePointManager]::SecurityProtocol = `
        [Net.ServicePointManager]::SecurityProtocol -bor `
        [Net.SecurityProtocolType]::Tls12
}

Enable-Tls12

$RepositoryUrl = "https://github.com/pycodebr/hubla-cli"
$Version = if ($env:HUBLA_CLI_VERSION) { $env:HUBLA_CLI_VERSION } else { "0.1.2" }
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
$UvVersion = if ($env:HUBLA_CLI_UV_VERSION) { $env:HUBLA_CLI_UV_VERSION } else { "0.12.9" }
$ManagedPythonVersion = if ($env:HUBLA_CLI_MANAGED_PYTHON_VERSION) {
    $env:HUBLA_CLI_MANAGED_PYTHON_VERSION
} else {
    "3.12"
}
$UvBootstrapDir = Join-Path $InstallRoot "bootstrap"

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

function Test-UvVersion([string]$Executable) {
    try {
        $VersionOutput = @(& $Executable --version 2>$null)
        if ($LASTEXITCODE -ne 0 -or $VersionOutput.Count -eq 0) {
            return $false
        }
        $ExpectedVersion = "uv $UvVersion"
        $ActualVersion = $VersionOutput[-1].Trim()
        return $ActualVersion -eq $ExpectedVersion -or $ActualVersion.StartsWith("$ExpectedVersion ")
    } catch {
        return $false
    }
}

function Get-UvExecutable {
    if ($env:HUBLA_CLI_UV) {
        if (
            -not (Test-Path -Path $env:HUBLA_CLI_UV -PathType Leaf) -or
            -not (Test-UvVersion $env:HUBLA_CLI_UV)
        ) {
            throw "HUBLA_CLI_UV precisa executar uv $UvVersion."
        }
        return $env:HUBLA_CLI_UV
    }

    $UvExecutable = Join-Path $UvBootstrapDir "uv.exe"
    if (
        $env:HUBLA_CLI_FORCE_UV_INSTALL -ne "1" -and
        (Test-Path -Path $UvExecutable -PathType Leaf) -and
        (Test-UvVersion $UvExecutable)
    ) {
        return $UvExecutable
    }

    Write-Step "Python compatível não encontrado. Instalando uv $UvVersion."
    New-Item -ItemType Directory -Force -Path $UvBootstrapDir | Out-Null
    $PreviousUvInstallDir = $env:UV_UNMANAGED_INSTALL
    $PreviousUvInstallerPath = $env:HUBLA_CLI_UV_INSTALLER_PATH
    $InstallerPath = Join-Path (
        [System.IO.Path]::GetTempPath()
    ) "hubla-cli-uv-$([Guid]::NewGuid().ToString('N')).ps1"
    try {
        $env:UV_UNMANAGED_INSTALL = $UvBootstrapDir
        $InstallerUrl = "https://astral.sh/uv/$UvVersion/install.ps1"
        Invoke-WebRequest -UseBasicParsing -Uri $InstallerUrl -OutFile $InstallerPath
        $PowerShellExecutable = (Get-Process -Id $PID).Path
        $env:HUBLA_CLI_UV_INSTALLER_PATH = $InstallerPath
        $BootstrapCommand = @'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
& $env:HUBLA_CLI_UV_INSTALLER_PATH
'@
        $InstallerOutput = @(
            & $PowerShellExecutable -NoProfile -ExecutionPolicy Bypass -Command $BootstrapCommand
        )
        $InstallerExitCode = $LASTEXITCODE
        $InstallerOutput | Out-Host
        if ($InstallerExitCode -ne 0) {
            throw "Não foi possível instalar o uv."
        }
    } finally {
        Remove-Item $InstallerPath -Force -ErrorAction SilentlyContinue
        if ($null -eq $PreviousUvInstallDir) {
            Remove-Item Env:UV_UNMANAGED_INSTALL -ErrorAction SilentlyContinue
        } else {
            $env:UV_UNMANAGED_INSTALL = $PreviousUvInstallDir
        }
        if ($null -eq $PreviousUvInstallerPath) {
            Remove-Item Env:HUBLA_CLI_UV_INSTALLER_PATH -ErrorAction SilentlyContinue
        } else {
            $env:HUBLA_CLI_UV_INSTALLER_PATH = $PreviousUvInstallerPath
        }
    }

    if (-not (Test-Path -Path $UvExecutable -PathType Leaf)) {
        throw "A instalação automática do uv não produziu um executável válido."
    }
    if (-not (Test-UvVersion $UvExecutable)) {
        throw "O uv instalado não corresponde à versão $UvVersion."
    }
    return $UvExecutable
}

function Install-ManagedPython {
    $UvExecutable = Get-UvExecutable
    $PreviousPythonInstallDir = $env:UV_PYTHON_INSTALL_DIR
    $PreviousPythonInstallBin = $env:UV_PYTHON_INSTALL_BIN
    try {
        $env:UV_PYTHON_INSTALL_DIR = Join-Path $InstallRoot "python"
        $env:UV_PYTHON_INSTALL_BIN = "0"
        Write-Step "Instalando Python $ManagedPythonVersion sem acesso administrativo."
        & $UvExecutable python install $ManagedPythonVersion | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Não foi possível instalar o Python gerenciado."
        }
        $PythonCandidates = @(
            & $UvExecutable python find --managed-python $ManagedPythonVersion
        )
        if ($LASTEXITCODE -ne 0 -or $PythonCandidates.Count -eq 0) {
            throw "Não foi possível localizar o Python gerenciado."
        }
        $ManagedPython = $PythonCandidates[-1].Trim()
        if (-not (Test-Python $ManagedPython @())) {
            throw "O Python gerenciado instalado não é compatível."
        }
        return $ManagedPython
    } finally {
        if ($null -eq $PreviousPythonInstallDir) {
            Remove-Item Env:UV_PYTHON_INSTALL_DIR -ErrorAction SilentlyContinue
        } else {
            $env:UV_PYTHON_INSTALL_DIR = $PreviousPythonInstallDir
        }
        if ($null -eq $PreviousPythonInstallBin) {
            Remove-Item Env:UV_PYTHON_INSTALL_BIN -ErrorAction SilentlyContinue
        } else {
            $env:UV_PYTHON_INSTALL_BIN = $PreviousPythonInstallBin
        }
    }
}

function Test-OrInstallVenvPip([string]$VenvPython) {
    & $VenvPython -m pip --version *> $null
    if ($LASTEXITCODE -eq 0) {
        return $true
    }
    & $VenvPython -m ensurepip --upgrade 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    & $VenvPython -m pip --version *> $null
    return $LASTEXITCODE -eq 0
}

$PythonExecutable = $null
$PythonPrefix = @()
if ($env:HUBLA_CLI_PYTHON) {
    $PythonExecutable = $env:HUBLA_CLI_PYTHON
    if (-not (Test-Python $PythonExecutable @())) {
        throw "HUBLA_CLI_PYTHON precisa apontar para Python 3.10 ou superior."
    }
}
if (
    -not $PythonExecutable -and
    $env:HUBLA_CLI_FORCE_MANAGED_PYTHON -ne "1" -and
    (Get-Command py -ErrorAction SilentlyContinue)
) {
    if (Test-Python "py" @("-3")) {
        $PythonExecutable = "py"
        $PythonPrefix = @("-3")
    }
}
if (
    -not $PythonExecutable -and
    $env:HUBLA_CLI_FORCE_MANAGED_PYTHON -ne "1" -and
    (Get-Command python -ErrorAction SilentlyContinue)
) {
    if (Test-Python "python" @()) {
        $PythonExecutable = "python"
    }
}

if (-not $PythonExecutable) {
    $PythonExecutable = Install-ManagedPython
    $PythonPrefix = @()
}

$VenvDir = Join-Path $InstallRoot "venv"
Write-Step "Instalando Hubla CLI em $InstallRoot"
New-Item -ItemType Directory -Force -Path $InstallRoot, $BinDir | Out-Null
& $PythonExecutable @PythonPrefix -m venv $VenvDir
if ($LASTEXITCODE -ne 0) {
    Write-Step "O módulo venv não está disponível. Usando Python gerenciado pelo uv."
    $PythonExecutable = Install-ManagedPython
    $PythonPrefix = @()
    & $PythonExecutable -m venv --clear $VenvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível criar o ambiente Python isolado."
    }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$CliExecutable = Join-Path $VenvDir "Scripts\hubla-cli.exe"
if (-not (Test-OrInstallVenvPip $VenvPython)) {
    Write-Step "O pip não está disponível. Recriando o ambiente com Python gerenciado pelo uv."
    $PythonExecutable = Install-ManagedPython
    $PythonPrefix = @()
    & $PythonExecutable -m venv --clear $VenvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível recriar o ambiente Python isolado."
    }
    if (-not (Test-OrInstallVenvPip $VenvPython)) {
        throw "Não foi possível instalar o pip no ambiente isolado."
    }
}
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
Write-Host "Próximo passo do usuário, em terminal separado: hubla-cli login"
Write-Host 'Se um agente executou este script, ele deve parar e aguardar a resposta "autenticado".'

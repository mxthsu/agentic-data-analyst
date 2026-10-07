[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath $Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "O comando falhou: $FilePath $($Arguments -join ' ')"
    }
}

function Get-BasePython {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return @{
                File = "py"
                Prefix = @("-3.12")
            }
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return @{
                File = $python.Source
                Prefix = @()
            }
        }
    }

    throw "Python 3.12 ou superior não foi encontrado. Instale o Python e execute o script novamente."
}

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Content
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

Write-Step "Verificando o Python"
$basePython = Get-BasePython
$baseArgs = @($basePython.Prefix) + @("--version")
Invoke-Checked -FilePath $basePython.File -Arguments $baseArgs

$venvPath = Join-Path $ProjectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Step "Criando o ambiente virtual"
    $venvArgs = @($basePython.Prefix) + @("-m", "venv", ".venv")
    Invoke-Checked -FilePath $basePython.File -Arguments $venvArgs
}
else {
    Write-Step "Ambiente virtual já existe"
}

Write-Step "Instalando as dependências"
Invoke-Checked -FilePath $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked -FilePath $venvPython -Arguments @("-m", "pip", "install", "-e", ".")

$envExample = Join-Path $ProjectRoot ".env.example"
$envPath = Join-Path $ProjectRoot ".env"

if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Step "Criando o arquivo .env"
    Copy-Item -LiteralPath $envExample -Destination $envPath
}

$envContent = [System.IO.File]::ReadAllText($envPath)
$keyMatch = [regex]::Match($envContent, '(?m)^GOOGLE_API_KEY=(.*)$')
$currentKey = if ($keyMatch.Success) { $keyMatch.Groups[1].Value.Trim() } else { "" }

if ([string]::IsNullOrWhiteSpace($currentKey) -or $currentKey -eq "sua_chave") {
    Write-Step "Configurando a chave do Gemini"
    $secureKey = Read-Host "Cole a GOOGLE_API_KEY" -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

    try {
        $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        if ([string]::IsNullOrWhiteSpace($plainKey)) {
            throw "A GOOGLE_API_KEY não pode ficar vazia."
        }

        if ($keyMatch.Success) {
            $replacement = "GOOGLE_API_KEY=$plainKey"
            $envContent = [regex]::Replace(
                $envContent,
                '(?m)^GOOGLE_API_KEY=.*$',
                [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $replacement }
            )
        }
        else {
            $envContent = $envContent.TrimEnd() + [Environment]::NewLine + "GOOGLE_API_KEY=$plainKey" + [Environment]::NewLine
        }

        Write-Utf8NoBom -Path $envPath -Content $envContent
    }
    finally {
        if ($pointer -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        }
    }
}
else {
    Write-Step "GOOGLE_API_KEY já configurada"
}

$dataDir = Join-Path $ProjectRoot "data"
$dbPath = Join-Path $dataDir "anexo_desafio_1.db"

if (-not (Test-Path -LiteralPath $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

if (-not (Test-Path -LiteralPath $dbPath)) {
    Write-Step "Configurando o banco SQLite"
    Write-Host "O banco não está no projeto."
    $sourceDb = (Read-Host "Informe o caminho completo do arquivo SQLite fornecido no desafio").Trim().Trim('"')

    if (-not (Test-Path -LiteralPath $sourceDb -PathType Leaf)) {
        throw "Arquivo não encontrado: $sourceDb"
    }

    Copy-Item -LiteralPath $sourceDb -Destination $dbPath
}
else {
    Write-Step "Banco SQLite já configurado"
}

Write-Step "Validando a configuração"
Invoke-Checked -FilePath $venvPython -Arguments @(
    "-c",
    "from data_analyst.config import Settings; s = Settings(); assert s.database_path.exists(), f'Banco não encontrado: {s.database_path}'; print('Configuração OK')"
)

Write-Host ""
Write-Host "Configuração concluída." -ForegroundColor Green
Write-Host "Para iniciar a aplicação, execute:"
Write-Host "  .\start.ps1" -ForegroundColor Yellow

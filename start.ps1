[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$envPath = Join-Path $ProjectRoot ".env"
$dbPath = Join-Path $ProjectRoot "data\anexo_desafio_1.db"

function Import-DotEnv {
    param([string]$Path)

    foreach ($rawLine in Get-Content -LiteralPath $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        $parts = $line.Split("=", 2)
        if ($parts.Count -ne 2) {
            continue
        }

        $name = $parts[0].Trim()
        $value = $parts[1]
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

function Test-HttpEndpoint {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-HttpEndpoint {
    param(
        [string]$Url,
        [int]$Attempts = 40,
        [int]$DelayMilliseconds = 500
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        if (Test-HttpEndpoint -Url $Url) {
            return $true
        }

        Start-Sleep -Milliseconds $DelayMilliseconds
    }

    return $false
}

function Test-TcpPort {
    param([int]$Port)

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(500)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Ambiente virtual não encontrado. Execute .\setup.ps1 primeiro."
}

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Arquivo .env não encontrado. Execute .\setup.ps1 primeiro."
}

if (-not (Test-Path -LiteralPath $dbPath)) {
    throw "Banco não encontrado em data\anexo_desafio_1.db. Execute .\setup.ps1 primeiro."
}

Import-DotEnv -Path $envPath

& $venvPython -c "from data_analyst.config import Settings; Settings(); print('Configuração carregada')" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "A configuração da aplicação é inválida. Execute .\setup.ps1 novamente."
}

$apiUrl = if ($env:API_URL) { $env:API_URL.TrimEnd("/") } else { "http://localhost:8000" }
$apiHealthBase = $apiUrl -replace '://localhost(?=[:/]|$)', '://127.0.0.1'
$apiHealth = "$apiHealthBase/health"
$uiUrl = "http://localhost:8501"
$uiHealth = "http://127.0.0.1:8501/_stcore/health"

Write-Host ""
Write-Host "Iniciando Agentic Data Analyst" -ForegroundColor Cyan

if (Test-HttpEndpoint -Url $apiHealth) {
    Write-Host "API já está em execução: $apiUrl"
}
else {
    if (Test-TcpPort -Port 8000) {
        throw "A porta 8000 já está em uso por outro processo."
    }

    $apiCommand = "& '$venvPython' -m uvicorn data_analyst.api.main:app --app-dir src"
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoLogo",
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $apiCommand
    ) -WorkingDirectory $ProjectRoot | Out-Null

    Write-Host "Aguardando a API..."
    if (-not (Wait-HttpEndpoint -Url $apiHealth)) {
        throw "A API não respondeu em $apiHealth. Verifique a janela da API."
    }
}

if (Test-HttpEndpoint -Url $uiHealth) {
    Write-Host "Streamlit já está em execução: $uiUrl"
}
else {
    if (Test-TcpPort -Port 8501) {
        throw "A porta 8501 já está em uso por outro processo."
    }

    $uiCommand = "& '$venvPython' -m streamlit run ui/streamlit_app.py --server.headless true --server.port 8501"
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoLogo",
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $uiCommand
    ) -WorkingDirectory $ProjectRoot | Out-Null

    Write-Host "Aguardando o Streamlit..."
    if (-not (Wait-HttpEndpoint -Url $uiHealth)) {
        throw "O Streamlit não respondeu em $uiHealth. Verifique a janela da interface."
    }
}

Write-Host ""
Write-Host "Aplicação pronta." -ForegroundColor Green
Write-Host "Interface: $uiUrl"
Write-Host "API:       $apiUrl"
Write-Host "Swagger:   $apiUrl/docs"
Write-Host ""
Write-Host "Feche as janelas da API e do Streamlit para encerrar a aplicação."

Start-Process $uiUrl

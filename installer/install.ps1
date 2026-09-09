# SoSmart Bilgi Asistanı — Kurulum Sonrası Yapılandırma Scripti
# Inno Setup tarafından otomatik çağrılır.
# Manuel çalıştırmak için: YÖNETİCİ PowerShell → Set-ExecutionPolicy Bypass -Scope Process -Force → .\install.ps1

$ErrorActionPreference = "Continue"
$INSTALL_DIR = "C:\SoSmart"
$APP_DIR     = "$INSTALL_DIR\app"
$LOG_DIR     = "$INSTALL_DIR\logs"
$NSSM        = "$INSTALL_DIR\nssm.exe"
$PYTHON_URL  = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$OLLAMA_URL  = "https://ollama.com/download/OllamaSetup.exe"

function Write-Step($msg) { Write-Host "`n===[ $msg ]===" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  [OK] $msg"    -ForegroundColor Green }
function Write-Info($msg) { Write-Host "  [..] $msg"    -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  [!!] $msg"    -ForegroundColor Red }
function Test-Cmd($cmd)   { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

Clear-Host
Write-Host @"
╔══════════════════════════════════════════════════════════════╗
║         SoSmart Bilgi Asistanı — Kurulum Yapilandirmasi     ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Magenta

function Download-FileWithRetry($url, $destPath, $minSizeMB = 5) {
    $oldPref = $global:ProgressPreference
    $global:ProgressPreference = 'SilentlyContinue'
    $attempts = 0
    $success = $false
    while (($attempts -lt 3) -and (-not $success)) {
        $attempts++
        try {
            Write-Info "Indiriliyor (Deneme $attempts/3)..."
            Invoke-WebRequest -Uri $url -OutFile $destPath -UseBasicParsing -TimeoutSec 600
            if ((Test-Path $destPath) -and ((Get-Item $destPath).Length -ge ($minSizeMB * 1MB))) {
                $success = $true
            }
        } catch {
            Write-Err "Indirme zaman asimina ugradi, tekrar deneniyor..."
            Remove-Item $destPath -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 3
        }
    }
    $global:ProgressPreference = $oldPref
    return $success
}

# ─── ADIM 1: Dizinler ────────────────────────────────────────────────────────
Write-Step "Dizinler hazirlaniyor"
New-Item -ItemType Directory -Path $LOG_DIR              -Force | Out-Null
New-Item -ItemType Directory -Path "$INSTALL_DIR\data\chroma_db" -Force | Out-Null
New-Item -ItemType Directory -Path "$INSTALL_DIR\data\uploads"   -Force | Out-Null
Write-OK "Dizinler hazir."

# ─── ADIM 2: Python Kontrolü ─────────────────────────────────────────────────
Write-Step "Python kontrol ediliyor"
$pythonOK = $false
if (Test-Cmd "python") {
    $ver = python --version 2>&1
    if ($ver -match "3\.(11|12|13)") {
        Write-OK "Python zaten kurulu: $ver"
        $pythonOK = $true
    }
}
if (-not $pythonOK) {
    Write-Info "Python 3.11 indiriliyor..."
    $tmp = "$INSTALL_DIR\_tmp"
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $pyExe = "$tmp\python_setup.exe"
    $dlOK = Download-FileWithRetry -url $PYTHON_URL -destPath $pyExe -minSizeMB 20
    if ($dlOK) {
        Start-Process -FilePath $pyExe -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait
        $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
        Write-OK "Python kuruldu."
    } else {
        Write-Err "Python indirilemedi, lutfen internet baglantinizi kontrol edin."
    }
}

# ─── ADIM 3: .env Dosyası ────────────────────────────────────────────────────
Write-Step ".env yapilandirma dosyasi"
$envPath = "$APP_DIR\.env"
if (-not (Test-Path $envPath)) {
    @"
APP_NAME=SoSmart Bilgi Asistani
APP_VERSION=2.0.0
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
JWT_SECRET_KEY=sosmart-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
USER_USERNAME=user
USER_PASSWORD=user123
CONFIDENCE_THRESHOLD=0.5
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=C:/SoSmart/data/chroma_db
UPLOAD_DIR=C:/SoSmart/data/uploads
DATABASE_URL=sqlite+aiosqlite:///C:/SoSmart/data/sosmart.db
"@ | Out-File -FilePath $envPath -Encoding UTF8
    Write-OK ".env olusturuldu."
} else {
    Write-OK ".env zaten mevcut."
}

# ─── ADIM 4: Python Sanal Ortam ve Bağımlılıklar ─────────────────────────────
Write-Step "Python sanal ortam ve bagimliliklar kuruluyor"
Write-Info "Bu adim 5-15 dakika surebilir..."

Set-Location $APP_DIR

if (-not (Test-Path "$APP_DIR\venv")) {
    python -m venv venv
    Write-OK "Sanal ortam olusturuldu."
} else {
    Write-OK "Sanal ortam zaten mevcut."
}

& "$APP_DIR\venv\Scripts\pip.exe" install --upgrade pip -q 2>&1 | Out-Null
& "$APP_DIR\venv\Scripts\pip.exe" install -r "$APP_DIR\requirements.txt" -q
Write-OK "Bagimliliklar yuklendi."

Write-Info "Embedding modeli indiriliyor (~100 MB, bir kez yapilir)..."
& "$APP_DIR\venv\Scripts\python.exe" -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); print('[OK] Embedding modeli hazir.')"

# ─── ADIM 5: Ollama ──────────────────────────────────────────────────────────
Write-Step "Ollama LLM motoru"
$localOllamaExe = "$env:LocalAppData\Programs\Ollama\ollama.exe"
$progOllamaExe  = "C:\Program Files\Ollama\ollama.exe"

if ((Test-Cmd "ollama") -or (Test-Path $localOllamaExe) -or (Test-Path $progOllamaExe)) {
    if (Test-Path "$env:LocalAppData\Programs\Ollama") {
        $env:Path += ";$env:LocalAppData\Programs\Ollama"
    }
    Write-OK "Ollama zaten kurulu."
} else {
    Write-Info "Ollama indiriliyor (~100 MB)..."
    $tmp = "$INSTALL_DIR\_tmp"
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $ollamaExe = "$tmp\OllamaSetup.exe"
    
    $dlOK = Download-FileWithRetry -url $OLLAMA_URL -destPath $ollamaExe -minSizeMB 50
    if ($dlOK) {
        Write-Info "Ollama sessizce C:\Program Files\Ollama konumuna kuruluyor..."
        Start-Process -FilePath $ollamaExe -ArgumentList '/SILENT /DIR="C:\Program Files\Ollama"'
        
        # OllamaSetup.exe kurulum sürecinin bitmesini bekle (arkaplan tepsi uygulamasını bekleme)
        $maxWait = 60
        while ((Get-Process -Name "OllamaSetup" -ErrorAction SilentlyContinue) -and ($maxWait -gt 0)) {
            Start-Sleep -Seconds 2
            $maxWait -= 2
        }
        Start-Sleep -Seconds 4
    } else {
        Write-Err "Ollama kurulum dosyasi indirilemedi. İnternet baglantinizi kontrol edip tekrar deneyin."
    }

    # Ollama Program Files ve LocalAppData dizinlerini PATH'e ekle
    $progOllama = "C:\Program Files\Ollama"
    $localOllama = "$env:LocalAppData\Programs\Ollama"
    if (Test-Path $progOllama) {
        $env:Path += ";$progOllama"
    }
    if (Test-Path $localOllama) {
        $env:Path += ";$localOllama"
    }
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
    Write-OK "Ollama C:\Program Files\Ollama konumuna kuruldu."
}

# Ollama sunucusunun (ollama serve) arka planda çalıştığından emin ol
Write-Info "Ollama sunucusu kontrol ediliyor..."
if (-not (Get-Process "ollama" -ErrorAction SilentlyContinue)) {
    Write-Info "Ollama sunucusu (ollama serve) arka planda baslatiliyor..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

Write-Info "LLM modeli cekiliyor: qwen2.5:3b (~2 GB, internet baglantisi gerekli)..."
Write-Info "Lutfen bekleyin, indirme islemi devam ediyor..."
try {
    & ollama pull qwen2.5:3b
    Write-OK "LLM modeli hazir."
} catch {
    Write-Err "Model indirilemedi. Kurulum sonrasinda 'ollama pull qwen2.5:3b' komutunu elle calistirabilirsiniz."
}

# ─── ADIM 6: Windows Servisleri (NSSM) ───────────────────────────────────────
Write-Step "Windows servisleri kuruluyor"

if (-not (Test-Path $NSSM)) {
    Write-Err "nssm.exe bulunamadi: $NSSM"
    Write-Err "Lutfen https://nssm.cc/release/nssm-2.24.zip adresinden indirip"
    Write-Err "nssm-2.24\win64\nssm.exe dosyasini $NSSM konumuna kopyalayin."
    Write-Err "Servis kurulumu atlaniyor..."
} else {
    $uvicorn   = "$APP_DIR\venv\Scripts\uvicorn.exe"
    $pythonExe = "$APP_DIR\venv\Scripts\python.exe"

    # Ollama servisi (NSSM ile varsayılan Windows servisi yap)
    Write-Info "SoSmart-Ollama servisi kuruluyor..."
    $ollamaBinPath = "C:\Program Files\Ollama\ollama.exe"
    if (-not (Test-Path $ollamaBinPath)) {
        $ollamaBinPath = "$env:LocalAppData\Programs\Ollama\ollama.exe"
    }
    if (Test-Path $ollamaBinPath) {
        & $NSSM remove "SoSmart-Ollama" confirm 2>$null
        & $NSSM install "SoSmart-Ollama" $ollamaBinPath
        & $NSSM set "SoSmart-Ollama" AppParameters "serve"
        & $NSSM set "SoSmart-Ollama" DisplayName   "SoSmart - Ollama LLM Motoru"
        & $NSSM set "SoSmart-Ollama" Description   "SoSmart Bilgi Asistani Ollama LLM Motoru"
        & $NSSM set "SoSmart-Ollama" Start         SERVICE_AUTO_START
        & $NSSM set "SoSmart-Ollama" AppStdout     "$LOG_DIR\ollama.log"
        & $NSSM set "SoSmart-Ollama" AppStderr     "$LOG_DIR\ollama_error.log"
        Write-OK "SoSmart-Ollama servisi kuruldu."
    }

    # Backend servisi
    Write-Info "SoSmart-Backend servisi kuruluyor..."
    & $NSSM remove "SoSmart-Backend" confirm 2>$null
    & $NSSM install "SoSmart-Backend" $uvicorn
    & $NSSM set "SoSmart-Backend" AppParameters "main:app --host 0.0.0.0 --port 8000"
    & $NSSM set "SoSmart-Backend" AppDirectory  $APP_DIR
    & $NSSM set "SoSmart-Backend" DisplayName   "SoSmart - Backend API"
    & $NSSM set "SoSmart-Backend" Description   "SoSmart Bilgi Asistani FastAPI Backend"
    & $NSSM set "SoSmart-Backend" Start         SERVICE_AUTO_START
    & $NSSM set "SoSmart-Backend" AppStdout     "$LOG_DIR\backend.log"
    & $NSSM set "SoSmart-Backend" AppStderr     "$LOG_DIR\backend_error.log"
    Write-OK "SoSmart-Backend servisi kuruldu."

    # Frontend servisi
    Write-Info "SoSmart-Frontend servisi kuruluyor..."
    & $NSSM remove "SoSmart-Frontend" confirm 2>$null
    & $NSSM install "SoSmart-Frontend" $pythonExe
    & $NSSM set "SoSmart-Frontend" AppParameters "frontend\app.py"
    & $NSSM set "SoSmart-Frontend" AppDirectory  $APP_DIR
    & $NSSM set "SoSmart-Frontend" DisplayName   "SoSmart - Frontend Arayuz"
    & $NSSM set "SoSmart-Frontend" Description   "SoSmart Bilgi Asistani Gradio Arayuzu"
    & $NSSM set "SoSmart-Frontend" Start         SERVICE_AUTO_START
    & $NSSM set "SoSmart-Frontend" AppStdout     "$LOG_DIR\frontend.log"
    & $NSSM set "SoSmart-Frontend" AppStderr     "$LOG_DIR\frontend_error.log"
    Write-OK "SoSmart-Frontend servisi kuruldu."

    # Servisleri başlat
    Write-Step "Servisler baslatiliyor"
    Start-Service -Name "SoSmart-Ollama"   -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Start-Service -Name "SoSmart-Backend"  -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 6
    Start-Service -Name "SoSmart-Frontend" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Write-OK "Servisler baslatildi."
}

# ─── Temizlik ─────────────────────────────────────────────────────────────────
Remove-Item -Path "$INSTALL_DIR\_tmp" -Recurse -Force -ErrorAction SilentlyContinue

# ─── BİTİŞ ───────────────────────────────────────────────────────────────────
Write-Host @"

  ✅ KURULUM TAMAMLANDI!

  Arayuz       : http://localhost:7860
  API          : http://localhost:8000
  API Docs     : http://localhost:8000/docs
  Log dosyalari: $LOG_DIR\

  Servis yonetimi (PowerShell):
    Start-Service SoSmart-Backend, SoSmart-Frontend
    Stop-Service  SoSmart-Backend, SoSmart-Frontend
    Get-Service   SoSmart-Backend, SoSmart-Frontend

"@ -ForegroundColor Green

Set-Location $HOME

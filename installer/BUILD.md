# SoSmart Bilgi Asistanı — Kurulum ve Servis Yönetimi Kılavuzu

## EXE Dosyasını Oluşturmadan Önce Gerekenler

### 1. Inno Setup İndir
https://jrsoftware.org/isdl.php adresinden **Inno Setup 6.x** indirin ve kurun.

### 2. NSSM İndir
https://nssm.cc/release/nssm-2.24.zip adresinden indirin.
- ZIP'i açın
- `nssm-2.24\win64\nssm.exe` dosyasını `installer\tools\` klasörüne kopyalayın:

```
installer\
  tools\
    nssm.exe   ← buraya koyun
  install.ps1
  setup.iss
  BUILD.md
```

### 3. EXE'yi Derle
1. Inno Setup'ı açın
2. `installer\setup.iss` dosyasını yükleyin
3. **Build → Compile** (veya F9) tuşuna basın
4. `dist\SoSmartSetup.exe` dosyası oluşacak

---

## Kurulum EXE'si Nasıl Çalışır?

```
SoSmartSetup.exe
  │
  ├── 1. Wizard ekranı (kurulum yolu seçimi)
  ├── 2. Proje dosyalarını C:\SoSmart\ altına kopyalar
  ├── 3. install.ps1 scriptini çalıştırır:
  │       ├── Python 3.11 kontrol/kurulum
  │       ├── pip install requirements.txt
  │       ├── Embedding model indir
  │       ├── Ollama kontrol/kurulum
  │       ├── qwen2.5:3b modeli çek
  │       ├── NSSM ile "SoSmart-Backend" servisi kur
  │       └── NSSM ile "SoSmart-Frontend" servisi kur
  └── 4. http://localhost:7860 otomatik açılır
```

---

## Servis Yönetimi (Kurulum Sonrası)

### PowerShell ile
```powershell
# Servisleri başlat
Start-Service SoSmart-Backend
Start-Service SoSmart-Frontend

# Servisleri durdur
Stop-Service SoSmart-Backend
Stop-Service SoSmart-Frontend

# Durum kontrolü
Get-Service SoSmart-Backend, SoSmart-Frontend

# Servis logları
Get-Content C:\SoSmart\logs\backend.log -Tail 50
Get-Content C:\SoSmart\logs\frontend.log -Tail 50
```

### Windows Hizmetler panelinden
`Win + R` → `services.msc` → "SoSmart" ara

---

## Kurulum Dizin Yapısı

```
C:\SoSmart\
  app\                  ← Proje kodları
    main.py
    requirements.txt
    .env
    venv\               ← Python sanal ortam
    app\                ← Backend modülleri
    frontend\           ← Gradio arayüzü
  data\                 ← Veriler (git'e gitmez)
    chroma_db\          ← Vektör veritabanı
    uploads\            ← Yüklenen dosyalar
    sosmart.db          ← SQLite veritabanı
  logs\                 ← Servis logları
    backend.log
    frontend.log
  nssm.exe              ← Windows servis yöneticisi
  installer\            ← Kurulum scriptleri
  api_documentation.md  ← API Dokümantasyonu
  README.md
```

---

## Sıfırdan Test Kurulumu (EXE Olmadan)

Sunucuda test etmek için EXE beklemeden manuel kurulum:

```powershell
# YÖNETİCİ olarak PowerShell aç
Set-ExecutionPolicy Bypass -Scope Process -Force
.\installer\install.ps1
```

---

## Sistem Gereksinimleri

| Bileşen | Minimum | Önerilen |
|---|---|---|
| İşletim Sistemi | Windows 10 (64-bit) | Windows 11 |
| RAM | 8 GB | 16 GB |
| Disk | 10 GB | 20 GB |
| CPU | 4 çekirdek | 8 çekirdek |
| İnternet | Kurulum için gerekli | — |

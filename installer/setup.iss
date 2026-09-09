; SoSmart Bilgi Asistanı — Inno Setup Scripti
; Bu script ile tek bir .exe kurulum dosyası oluşturulur.
;
; Gereksinim: Inno Setup 6.x (https://jrsoftware.org/isinfo.php)
; Derleme: Inno Setup'ı açın, bu dosyayı yükleyin, Build > Compile

#define MyAppName "SoSmart Bilgi Asistani"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "SoSmart Staj Projesi"
#define MyAppURL "http://localhost:7860"
#define MyAppExeName "SoSmartSetup.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName=C:\SoSmart
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Kurulum sıkıştırma ayarları
Compression=lzma2/ultra64
SolidCompression=yes
; Görünüm
WizardStyle=modern
; Yönetici yetkisi gerekli (servis kurulumu için)
PrivilegesRequired=admin
; Çıktı dosyası
OutputDir=..\dist
OutputBaseFilename=SoSmartSetup
; Lisans dosyası
; LicenseFile=..\LICENSE.txt
; Kurulum dili
[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Ana proje dosyaları (venv ve data hariç — bunlar kurulum sırasında oluşturulur)
Source: "..\app\*"; DestDir: "{app}\app\app"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__"
Source: "..\frontend\*"; DestDir: "{app}\app\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__"
Source: "..\main.py"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\api_documentation.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "install.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion

; NSSM (önceden indirilmiş olmalı: installer\tools\nssm.exe)
; NSSM'i https://nssm.cc/release/nssm-2.24.zip adresinden indirin
; nssm-2.24\win64\nssm.exe dosyasını installer\tools\ klasörüne kopyalayın
Source: "tools\nssm.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName} - Arayuz"; Filename: "{sys}\cmd.exe"; Parameters: "/c start http://localhost:7860"; Comment: "Gradio Arayüzünü Aç"
Name: "{group}\{#MyAppName} - API Docs"; Filename: "{sys}\cmd.exe"; Parameters: "/c start http://localhost:8000/docs"; Comment: "API Dokümantasyonunu Aç"
Name: "{group}\Servisleri Baslat"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-Command ""Start-Service SoSmart-Backend; Start-Service SoSmart-Frontend; Write-Host 'Servisler baslatildi!'"""; Comment: "SoSmart Servislerini Başlat"
Name: "{group}\Servisleri Durdur"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-Command ""Stop-Service SoSmart-Backend; Stop-Service SoSmart-Frontend; Write-Host 'Servisler durduruldu!'"""; Comment: "SoSmart Servislerini Durdur"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{sys}\cmd.exe"; Parameters: "/c start http://localhost:7860"; Tasks: desktopicon

[Run]
; Kurulum sonrası PowerShell scriptini çalıştır (Siyah terminal penceresinde canlı ilerleme gösterilir)
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; \
  Parameters: "-ExecutionPolicy Bypass -File ""{app}\installer\install.ps1"""; \
  Description: "SoSmart kurulumunu tamamla (Python, bagimliliklar, Windows servisleri)"; \
  Flags: waituntilterminated; \
  StatusMsg: "Kurulum yapılandırılıyor, lütfen açılan terminal penceresini takip edin..."

; Kurulum bitince arayüzü aç
Filename: "{sys}\cmd.exe"; \
  Parameters: "/c start http://localhost:7860"; \
  Description: "SoSmart arayuzunu ac"; \
  Flags: nowait postinstall skipifsilent; \
  StatusMsg: "Arayuz aciliyor..."

[UninstallRun]
; Kaldırma sırasında servisleri durdur ve sil
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; \
  Parameters: "-Command ""Stop-Service SoSmart-Backend, SoSmart-Frontend, SoSmart-Ollama -Force -ErrorAction SilentlyContinue; & '{app}\nssm.exe' remove SoSmart-Backend confirm; & '{app}\nssm.exe' remove SoSmart-Frontend confirm; & '{app}\nssm.exe' remove SoSmart-Ollama confirm"""; \
  Flags: runhidden

[Code]
// Kurulum öncesi sistem kontrolü
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // Windows sürüm kontrolü (Windows 10+)
  if not (GetWindowsVersion >= $0A000000) then begin
    MsgBox('Bu uygulama Windows 10 veya üzeri gerektirir.', mbError, MB_OK);
    Result := False;
    Exit;
  end;

  // Mevcut kurulum kontrolü
  if RegValueExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1', 'UninstallString') then begin
    if MsgBox('SoSmart zaten kurulu. Güncelleme yapmak istiyor musunuz?', mbConfirmation, MB_YESNO) = IDNO then begin
      Result := False;
    end;
  end;
end;

// Kurulum tamamlandığında bilgi ver
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    MsgBox(
      'SoSmart Bilgi Asistanı kurulumu tamamlandı!' + #13#10 + #13#10 +
      'Arayüz: http://localhost:7860' + #13#10 +
      'API Docs: http://localhost:8000/docs' + #13#10 + #13#10 +
      'NOT: İlk başlatma sırasında modeller yüklenirken' + #13#10 +
      'birkaç dakika beklemeniz gerekebilir.',
      mbInformation, MB_OK
    );
  end;
end;

; Inno Setup betiği: Yıldız Yapı Mimarlık - Müşteri Takip kurulum programı
#define MyAppName "Müşteri Takip"
#define MyAppPublisher "Yıldız Yapı Mimarlık"
#define MyAppExeName "MusteriTakip.exe"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{B7C1E6F2-5A44-4D0B-9C33-7E21A9D4F801}
AppName={#MyAppPublisher} - {#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Yildiz Yapi Mimarlik\Musteri Takip
DefaultGroupName={#MyAppPublisher}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=YildizYapi_MusteriTakip_Kurulum
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
MinVersion=6.1sp1

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"; GroupDescription: "Ek görevler:"

[Files]
Source: "..\dist\MusteriTakip\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppPublisher} - {#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppPublisher} - {#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Programı şimdi başlat"; Flags: nowait postinstall skipifsilent

; Kullanıcı verileri (%APPDATA%\Yildiz Yapi Mimarlik) kaldırmada silinmez.

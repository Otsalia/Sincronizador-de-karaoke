; Instalador de Windows (Inno Setup 6.3 o superior)
; Requiere haber construido antes el ejecutable: dist\KaraokeSync\

#define AppName "Sincronizador de karaoke"
#define AppVersion "1.0.0"
#define AppExe "KaraokeSync.exe"

[Setup]
AppId={{7747A507-E0BB-4029-9CFE-A3B5FF5D0946}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\KaraokeSync
DefaultGroupName={#AppName}
OutputDir=..\Output
OutputBaseFilename=KaraokeSync-Setup
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Instalación solo para el usuario actual: no pide permisos de administrador
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\assets\icon.ico

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\KaraokeSync\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

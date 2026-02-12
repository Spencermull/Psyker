; Psyker Installer — minimal wizard, everything pre-bundled
; Run: iscc installer\Psyker.iss
; Or: scripts\build_installer.ps1 (builds PyInstaller output first, then runs iscc)

#define MyAppName "Psyker"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Psyker"
#define MyAppURL "https://github.com/.../Psyker"
#define MyAppExeName "Psyker.exe"

[Setup]
AppId={{8B3E9A2C-1F4D-4E7B-9C6A-3D2B8F1E0A4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Psyker
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Psyker-Setup-{#MyAppVersion}
SetupIconFile=..\vscode-extension\icons\logo_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Minimal wizard: skip dir selection prompt (use default)
DisableDirPage=yes

; Minimal wizard: skip Start Menu folder selection
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Bundle entire PyInstaller output — all dependencies pre-wrapped
Source: "..\dist\Psyker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Pre-create sandbox so user has zero setup — matches PSYKER_SANDBOX.md layout
; {%USERPROFILE} expands to user's home; sandbox is never uninstalled (user data)
Name: "{%USERPROFILE}\psyker_sandbox\workspace"; Flags: uninsneveruninstall
Name: "{%USERPROFILE}\psyker_sandbox\logs"; Flags: uninsneveruninstall
Name: "{%USERPROFILE}\psyker_sandbox\tmp"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove app dir only; sandbox stays (user data)
Type: dirifempty; Name: "{app}"

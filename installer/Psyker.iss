; Psyker Installer — GUI + CLI, minimal wizard
; Run: iscc installer\Psyker.iss
; Or: scripts\build_installer.ps1 (builds PyInstaller output first, then runs iscc)

#define MyAppName "Psyker"
#define MyAppVersion "0.1.1"
#define MyAppPublisher "Psyker"
#define MyAppURL "https://github.com/.../Psyker"
#define MyAppExeName "PsykerGUI.exe"
#define MyAppExeNameCLI "Psyker.exe"

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
UninstallDisplayIcon={app}\PsykerGUI\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Minimal wizard: skip dir selection prompt (use default)
DisableDirPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "clishortcut"; Description: "Create Start Menu shortcut for CLI (Psyker.exe)"; GroupDescription: "Shortcuts"; Flags: unchecked

[Files]
; Bundle both CLI and GUI PyInstaller outputs
Source: "..\dist\Psyker\*"; DestDir: "{app}\Psyker"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\PsykerGUI\*"; DestDir: "{app}\PsykerGUI"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Pre-create sandbox so user has zero setup
Name: "{%USERPROFILE}\psyker_sandbox\workspace"; Flags: uninsneveruninstall
Name: "{%USERPROFILE}\psyker_sandbox\logs"; Flags: uninsneveruninstall
Name: "{%USERPROFILE}\psyker_sandbox\tmp"; Flags: uninsneveruninstall

[Icons]
; Primary: GUI (embedded terminal)
Name: "{group}\{#MyAppName}"; Filename: "{app}\PsykerGUI\{#MyAppExeName}"; Comment: "Psyker GUI (recommended)"
Name: "{group}\Psyker CLI"; Filename: "{app}\Psyker\{#MyAppExeNameCLI}"; Comment: "Psyker CLI (terminal)"; Tasks: clishortcut
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\PsykerGUI\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\PsykerGUI\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: dirifempty; Name: "{app}\Psyker"
Type: dirifempty; Name: "{app}\PsykerGUI"
Type: dirifempty; Name: "{app}"

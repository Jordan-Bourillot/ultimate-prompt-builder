; ============================================================
;  AlphaBeast - installeur Windows (Inno Setup)
;  Compilation : double-cliquer sur build_installer.bat
;  Sortie : installer_output\AlphaBeast_setup_X.Y.Z.exe
; ============================================================

#define MyAppName "AlphaBeast"
#ifndef MyAppVersion
  #define MyAppVersion "1.4.0"
#endif
#define MyAppPublisher "Triskell Studio"
#define MyAppURL "https://prompt-builder.triskell-studio.fr"
#define MyAppExeName "UltimatePromptBuilder.exe"

[Setup]
AppId={{8F2D4E3A-9C5B-4A1F-B8D7-3E6A2F1C5D9B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\AlphaBeast
DefaultGroupName=AlphaBeast
DisableProgramGroupPage=yes
OutputDir=..\installer_output
OutputBaseFilename=AlphaBeast_setup_{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} - 16 Mega Prompts pour 5 IA
VersionInfoProductName={#MyAppName}
VersionInfoVersion={#MyAppVersion}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\UltimatePromptBuilder\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\UltimatePromptBuilder\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName} maintenant"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

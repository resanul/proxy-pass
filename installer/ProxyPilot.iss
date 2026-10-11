; ProxyPilot v1.1 Inno Setup installer
; Build the EXE first, then compile this script with Inno Setup 6.
#define MyAppName "ProxyPilot"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "ProxyPilot"
#define MyAppExeName "ProxyPilot.exe"

[Setup]
AppId={{C2B04127-C4A8-4A79-8B63-A4F6676A8D10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ProxyPilot
DefaultGroupName={#MyAppName}
OutputDir=..\dist-installer
OutputBaseFilename=ProxyPilot-Setup-1.1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\ProxyPilot.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ProxyPilot"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ProxyPilot"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch ProxyPilot"; Flags: postinstall nowait skipifsilent

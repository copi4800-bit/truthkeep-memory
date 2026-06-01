; Optional Inno Setup script. This creates an EXE wrapper around the Easy Mode installer.
; You must install Inno Setup and then sign the resulting EXE with sign_installer.ps1.
#define MyAppName "TruthKeep Memory"
#define MyAppVersion "11.0.0-alpha"
#define MyAppPublisher "TruthKeep"
#define MyAppExeName "INSTALL_TRUTHKEEP_WINDOWS.cmd"

[Setup]
AppId={{9C0D6BBE-204B-4F0C-8E5A-TRUTHKEEPV11}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userappdata}\TruthKeepMemory
DisableProgramGroupPage=yes
OutputBaseFilename=TruthKeepSetup-v11-alpha
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\..\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Excludes: "*.pyc,__pycache__,.pytest_cache,.git,*.db,*.db-wal,*.db-shm,truthkeep.log,dist-enterprise"

[Icons]
Name: "{userdesktop}\TruthKeep Setup"; Filename: "{app}\INSTALL_TRUTHKEEP_WINDOWS.cmd"

[Run]
Filename: "{app}\INSTALL_TRUTHKEEP_WINDOWS.cmd"; Description: "Run TruthKeep Easy Mode setup"; Flags: postinstall nowait skipifsilent

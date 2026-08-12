#define MyAppName "Rizwan Media Saver PC"
#define MyAppVersion "1.1.2"
#define MyAppPublisher "Muhammad Rizwan"
#define MyAppExeName "Rizwan Media Saver PC.exe"

[Setup]
AppId={{A0E1D312-76BA-4B60-9D16-6409C96442C4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Rizwan Media Saver PC
DefaultGroupName=Rizwan Media Saver PC
DisableProgramGroupPage=yes
OutputDir=..\desktop-artifacts
OutputBaseFilename=Rizwan-Media-Saver-PC-v1.1.2-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=Rizwan Media Saver PC
SetupLogging=yes

[Files]
Source: "publish\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Rizwan Media Saver PC"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Rizwan Media Saver PC"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Rizwan Media Saver PC"; Flags: nowait postinstall skipifsilent

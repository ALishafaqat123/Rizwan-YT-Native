#define MyAppName "Rizwan Media Saver PC Preview"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "Muhammad Rizwan"
#define MyAppExeName "Rizwan Media Saver PC.exe"

[Setup]
AppId={{7E91B954-8E4E-4D86-A72E-4C18F1201201}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Rizwan Media Saver PC Preview
DefaultGroupName=Rizwan Media Saver PC Preview
DisableProgramGroupPage=yes
OutputDir=..\desktop-artifacts
OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview1-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=Rizwan Media Saver PC Preview
SetupLogging=yes

[Files]
Source: "publish\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Rizwan Media Saver PC Preview"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Rizwan Media Saver PC Preview"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Rizwan Media Saver PC Preview"; Flags: nowait postinstall skipifsilent

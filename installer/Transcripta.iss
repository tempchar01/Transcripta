; Version is supplied by scripts/build_windows.ps1 from app/release.py.
#ifndef ProductVersion
  #error ProductVersion must be provided by the release build script.
#endif
#define ProductName "Transcripta"
#define ProductExe "Transcripta.exe"
#define BrandIcon "..\assets\branding\generated\app_icon.ico"
#define BuildDir "..\dist\Transcripta"
#define InstalledIcon "{app}\_internal\assets\branding\generated\app_icon.ico"

[Setup]
AppId={{CE45A5C8-6EAF-4E72-9F7D-A5B71C3E8F40}
AppName={#ProductName}
AppVersion={#ProductVersion}
AppPublisher=Maksim Pershikov
DefaultDirName={localappdata}\Programs\Transcripta
DefaultGroupName={#ProductName}
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=Transcripta-{#ProductVersion}-Windows-x64-Setup
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
VersionInfoVersion=1.0.0.0
VersionInfoDescription=Local AI transcription application
WizardStyle=modern
SetupIconFile={#BrandIcon}
UninstallDisplayIcon={app}\{#ProductExe}
UninstallDisplayName={#ProductName}
ShowLanguageDialog=auto
Compression=lzma2
SolidCompression=yes
LZMAUseSeparateProcess=yes
DisableProgramGroupPage=no

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#ProductName}"; Filename: "{app}\{#ProductExe}"; IconFilename: "{#InstalledIcon}"
Name: "{autodesktop}\{#ProductName}"; Filename: "{app}\{#ProductExe}"; IconFilename: "{#InstalledIcon}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ProductExe}"; Description: "{cm:LaunchProgram,{#ProductName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; User data in %LOCALAPPDATA%\Transcripta is intentionally never deleted here.

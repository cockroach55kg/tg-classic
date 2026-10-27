#ifndef PayloadDir
  #error PayloadDir is required
#endif
#ifndef OutputPath
  #error OutputPath is required
#endif
#ifndef InstallerVersion
  #define InstallerVersion "7.3.3.1"
#endif

[Setup]
AppId={{F58E5C0A-50CA-43FD-91F4-773CE1D70C8B}
AppName=TG Classic
AppVersion={#InstallerVersion}
AppVerName=TG Classic
AppPublisher=TG Classic contributors
AppPublisherURL=https://github.com/cockroach55kg/tg-classic
AppSupportURL=https://github.com/cockroach55kg/tg-classic/issues
AppUpdatesURL=https://github.com/cockroach55kg/tg-classic/releases
DefaultDirName={localappdata}\Programs\TG Classic
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputPath}
OutputBaseFilename=TG-Classic-Windows-x64-Setup
SetupIconFile=installer-assets\TG Classic.ico
UninstallDisplayIcon={app}\TG Classic.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=classic
WizardResizable=no
CloseApplications=no
RestartApplications=no
VersionInfoVersion={#InstallerVersion}
VersionInfoDescription=TG Classic Windows installer
VersionInfoCompany=TG Classic contributors
VersionInfoProductName=TG Classic
UninstallDisplayName=TG Classic
Uninstallable=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
Name: "{userappdata}\TG Classic"; Flags: uninsneveruninstall

[Files]
Source: "{#PayloadDir}\TG Classic.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadDir}\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadDir}\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadDir}\build-info.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\TG Classic"; Filename: "{app}\TG Classic.exe"; Parameters: "-workdir ""{userappdata}\TG Classic"""; WorkingDir: "{userappdata}\TG Classic"
Name: "{autodesktop}\TG Classic"; Filename: "{app}\TG Classic.exe"; Parameters: "-workdir ""{userappdata}\TG Classic"""; WorkingDir: "{userappdata}\TG Classic"; Tasks: desktopicon

[Run]
Filename: "{app}\TG Classic.exe"; Parameters: "-workdir ""{userappdata}\TG Classic"""; WorkingDir: "{userappdata}\TG Classic"; Description: "{cm:LaunchProgram,TG Classic}"; Flags: nowait postinstall skipifsilent unchecked

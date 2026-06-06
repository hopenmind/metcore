; Inno Setup script for the Hope 'n Mind desktop app (Windows).
; Build:  iscc /DAppVersion=0.1.0 /DExeName=hopenmind-windows-x86_64.exe installer\hopenmind.iss
; Produces installer\Output\hopenmind-setup-<arch>.exe
; The packaged GUI exe must already exist in dist\ (built by packaging\build_exe.py).

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef ExeName
  #define ExeName "metcore-windows-x86_64.exe"
#endif

[Setup]
AppName=Metcore
AppVersion={#AppVersion}
AppPublisher=Hope 'n Mind SASU - Research
AppPublisherURL=https://github.com/hopenmind/hopenmind-suite
DefaultDirName={autopf}\HopenMind
DefaultGroupName=Hope 'n Mind
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=metcore-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible arm64
ArchitecturesInstallIn64BitMode=x64compatible arm64
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts"

[Files]
Source: "..\dist\{#ExeName}"; DestDir: "{app}"; DestName: "metcore.exe"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE";   DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Metcore"; Filename: "{app}\metcore.exe"
Name: "{group}\Uninstall Metcore"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Metcore"; Filename: "{app}\metcore.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\metcore.exe"; Description: "Launch Metcore"; Flags: nowait postinstall skipifsilent

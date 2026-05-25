; ============================================================
; DataRescue - Inno Setup Installer Script
; Requires: Inno Setup 6.x  (https://jrsoftware.org/isdl.php)
;
; BEFORE RUNNING:
;   1. Run build_win.bat first to produce the dist\DataRescue\ folder.
;   2. Open this .iss in Inno Setup Compiler and click Build > Compile,
;      OR run from command line:
;        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" datarescue_installer.iss
;
; OUTPUT: build\installer\DataRescue_Setup_1.0.0.exe
; ============================================================

#define AppName        "DataRescue"
#define AppVersion     "1.0.0"
#define AppPublisher   "Zuper Inc."
#define AppURL         "https://datarescue.app"
#define AppExeName     "DataRescue.exe"
#define SourceDir      "dist\DataRescue"
#define OutputDir      "installer"

[Setup]
AppId={{A3F2B901-7C44-4E8D-9B12-3F5A6C8D1E20}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/support
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Request admin rights so we can write to Program Files
PrivilegesRequired=admin
OutputDir={#OutputDir}
OutputBaseFilename=DataRescue_Setup_{#AppVersion}
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Minimum Windows version: Windows 10 (6.2 = Win 8, 10.0 = Win 10)
MinVersion=10.0
; Show a "What's New" page after install
InfoAfterFile=..\THIRD_PARTY_NOTICES.txt
UninstallDisplayIcon={app}\{#AppExeName}
; Add to Add/Remove Programs
CreateUninstallRegKey=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";        GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunch";   Description: "Add to Quick Launch bar";       GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; Copy the entire PyInstaller output folder
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: The wildcard above already includes the binaries\win\ subfolder with
;       photorec.exe, testdisk.exe and all required DLLs.

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";   Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Optionally launch the app after install
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove the user config directory on uninstall (optional — comment out to keep user data)
; Type: filesandordirs; Name: "{localappdata}\DataRescue"

[Registry]
; Register app in Windows "Open With" — optional
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: createvalueifdoesntexist

[Code]
// Check that the user is on Windows 10 or later
function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
begin
  GetWindowsVersionEx(Version);
  if Version.Major < 10 then begin
    MsgBox('DataRescue requires Windows 10 or later.', mbError, MB_OK);
    Result := False;
  end else
    Result := True;
end;

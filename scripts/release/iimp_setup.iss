; ============================================================================
; IIMP (Integrated Interactive Module Platform) — Inno Setup Installer Script
; ============================================================================
;
; Prerequisites:
;   1. PyInstaller build must have been run first:
;        pyinstaller iimp.spec
;      which produces: dist\IIMP\  (one-directory bundle)
;   2. Inno Setup 6.x must be installed (https://jrsoftware.org/isinfo.php)
;
; Usage:
;   Open this file in the Inno Setup Compiler (ISCC.exe) and click Compile,
;   or run from CLI:
;        ISCC.exe scripts\release\iimp_setup.iss
;
; Output:
;   scripts\release\output\IIMP_Setup_v1.0.0.exe
; ============================================================================

#define MyAppName        "IIMP"
#define MyAppFullName    "Integrated Interactive Module Platform"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "IIMP Team"
#define MyAppExeName     "IIMP.exe"
#define MyAppURL         "https://github.com/your-org/iimp"
; Path to the PyInstaller output directory (relative to this script)
#define MyDistDir        "..\..\dist\IIMP"

; ── [Setup] section ──────────────────────────────────────────────────────────

[Setup]
AppId={{A3F7C2E1-8D4B-4F9A-B201-7E6C3A1D5F80}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppFullName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Default install location: C:\Program Files\IIMP
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppFullName}

; Allow user to choose install directory
DirExistsWarning=yes
DisableDirPage=no
DisableProgramGroupPage=no

; Output
OutputDir=output
OutputBaseFilename=IIMP_Setup_v{#MyAppVersion}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes

; Appearance
WizardStyle=modern
WizardSizePercent=120

; Requires Windows 10 or later (64-bit only)
MinVersion=10.0.17763
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Do NOT require admin rights — install to per-user AppData if non-admin
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Licensing
; LicenseFile=..\..\LICENSE.txt   ; Uncomment when licence file exists

; Icon
; SetupIconFile=..\..\ui\resources\iimp.ico   ; Uncomment when icon exists

; Uninstaller
UninstallDisplayName={#MyAppFullName}
UninstallDisplayIcon={app}\{#MyAppExeName}
CreateUninstallRegKey=yes

; ── [Languages] section ──────────────────────────────────────────────────────

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ── [Tasks] section ──────────────────────────────────────────────────────────

[Tasks]
Name: "desktopicon";    Description: "Create a &desktop icon";            GroupDescription: "Additional icons:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon";      GroupDescription: "Additional icons:"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

; ── [Files] section ──────────────────────────────────────────────────────────

[Files]
; Ship entire PyInstaller one-directory bundle
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Optional: ship a sample user guide alongside the binary
; Source: "..\..\docs\quickstart.pdf"; DestDir: "{app}\docs"; Flags: ignoreversion

; ── [Icons] section ──────────────────────────────────────────────────────────

[Icons]
; Start-menu shortcut
Name: "{group}\{#MyAppName}";          Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop shortcut (created only if task selected)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Quick Launch shortcut (legacy — Windows 7 and earlier)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

; ── [Run] section ────────────────────────────────────────────────────────────

[Run]
; Offer to launch IIMP after installation finishes
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

; ── [UninstallRun] section ───────────────────────────────────────────────────

[UninstallRun]
; Nothing special needed on uninstall — all files are under {app}

; ── [Registry] section ────────────────────────────────────────────────────────

[Registry]
; Register the app version in Windows Apps & Features
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; ── [Dirs] section ───────────────────────────────────────────────────────────

[Dirs]
; Create user data directory on install so IIMP can write on first launch
Name: "{userappdata}\{#MyAppName}";         Flags: uninsneveruninstall
Name: "{userappdata}\{#MyAppName}\modules"; Flags: uninsneveruninstall
Name: "{userappdata}\{#MyAppName}\exports"; Flags: uninsneveruninstall
Name: "{userappdata}\{#MyAppName}\logs";    Flags: uninsneveruninstall

; ── [Code] section ────────────────────────────────────────────────────────────

[Code]
// Inno Setup Pascal Script

function GetUninstallString(): string;
var
  sUnInstPath: string;
  sUnInstallString: string;
begin
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppId")}_is1');
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function UninstallPreviousVersion(): Integer;
var
  sUnInstallString: string;
  iResultCode: integer;
begin
  Result := 0;
  sUnInstallString := GetUninstallString();
  if sUnInstallString <> '' then begin
    sUnInstallString := RemoveQuotes(sUnInstallString);
    if Exec(sUnInstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_HIDE, ewWaitUntilTerminated, iResultCode) then
      Result := iResultCode
    else
      Result := 1;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep=ssInstall) then begin
    if (IsUpgrade()) then begin
      UninstallPreviousVersion();
    end;
  end;
end;

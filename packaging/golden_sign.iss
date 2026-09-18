; Golden Sign — Inno Setup script
; Build (after PyInstaller onedir):
;   ISCC.exe packaging\golden_sign.iss
; Requires: Inno Setup 6, dist\GoldenSign\ prepared by packaging\build_release.ps1

#define MyAppName "Golden Sign"
#define MyAppVersion "1.1.13"
#define MyAppPublisher "HOC HK"
#define MyAppExeName "GoldenSign.exe"
#define MyAppURL "https://github.com/hochk2019/Golden-Signing"
; Repo root = parent of packaging\
#define RepoRoot ".."
#define PayloadDir RepoRoot + "\dist\GoldenSign"

[Setup]
AppId={{6F2A9C40-8E1B-4D7A-B3C5-9E4A1D0F22B1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\GoldenSign
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#RepoRoot}\dist\release
OutputBaseFilename=GoldenSign-Setup-{#MyAppVersion}
SetupIconFile={#RepoRoot}\assets\branding\gsign\golden-signing.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Khởi động cùng Windows (không khuyến nghị)"; GroupDescription: "Tùy chọn khác:"; Flags: unchecked

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\GoldenSign.exe"

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Keep user data under %LOCALAPPDATA%\GoldenSign — do not delete here
Type: filesandordirs; Name: "{app}"

[Code]
var
  ResultCode: Integer;

procedure RefreshIconCache();
var
  PS: String;
begin
  { Clear Windows icon cache + notify shell so Desktop .lnk shows new EXE icon.
    OneDrive Desktop paths still work because we target the .lnk we just wrote. }
  PS := 'Remove-Item -LiteralPath (Join-Path $env:LOCALAPPDATA ''IconCache.db'') -Force -ErrorAction SilentlyContinue; '
      + 'ie4uinit.exe -ClearIconCache; ie4uinit.exe -show; '
      + '$t = Add-Type -MemberDefinition ''[DllImport(\"shell32.dll\")] public static extern void SHChangeNotify(uint e, uint f, IntPtr a, IntPtr b);'' '
      + '-Name W -Namespace N -PassThru; $t::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero);';
  Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "' + PS + '"',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DesktopLnk: String;
begin
  if CurStep = ssInstall then
  begin
    { Drop stale .lnk so [Icons] recreates it bound to the new EXE icon }
    DesktopLnk := ExpandConstant('{autodesktop}\Golden Sign.lnk');
    if FileExists(DesktopLnk) then
      DeleteFile(DesktopLnk);
  end;
  if CurStep = ssPostInstall then
    RefreshIconCache();
end;

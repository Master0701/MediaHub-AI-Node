#define MyAppName "MediaHub Compute Node"
#ifndef MyAppVersion
#define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "MediaHub"
#define MyAppExeName "MediaHub-Compute-Node.exe"

[Setup]
AppId={{6AA267EC-133B-45F4-82ED-7CB6E28EA208}
AppName={#MyAppName}
SetupIconFile=..\assets\MediaHub-Compute-Node.ico
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\MediaHub Compute Node
DefaultGroupName=MediaHub Compute Node

OutputDir=..\..\release\windows_compute_node
OutputBaseFilename=MediaHub-Compute-Node_Setup_v{#MyAppVersion}

Compression=lzma2
SolidCompression=yes

WizardStyle=modern

PrivilegesRequired=admin

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

CloseApplications=yes
RestartApplications=no

SetupLogging=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

Name: "autostart"; Description: "MediaHub Compute Node beim Windows-Start starten"; GroupDescription: "Autostart:"; Flags: checkedonce

[Files]
Source: "..\..\dist\windows_compute_node\MediaHub-Compute-Node.exe"; DestDir: "{app}"; Flags: ignoreversion

Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

Source: "..\..\THIRD_PARTY_LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion

Source: "..\..\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs

Source: "remove_persistent_data.ps1"; DestDir: "{commonappdata}\MediaHub\ComputeNode"; Flags: ignoreversion uninsneveruninstall

Source: "..\assets\MediaHub-Compute-Node.ico"; DestDir: "{commonappdata}\MediaHub\ComputeNode"; DestName: "MediaHub-Compute-Node.ico"; Flags: ignoreversion uninsneveruninstall

[Icons]
Name: "{group}\MediaHub Compute Node"; Filename: "{app}\{#MyAppExeName}"

Name: "{group}\Drittanbieter-Lizenzen"; Filename: "{app}\THIRD_PARTY_LICENSES.md"

Name: "{group}\Deinstallieren"; Filename: "{uninstallexe}"

Name: "{autodesktop}\MediaHub Compute Node"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

Name: "{commonstartup}\MediaHub Compute Node"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: autostart

[Run]
Filename: "{cmd}"; Parameters: "/C type nul > ""{app}\installed.mode"""; Flags: runhidden waituntilterminated

Filename: "{app}\{#MyAppExeName}"; Description: "MediaHub Compute Node starten"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM ""{#MyAppExeName}"" >nul 2>&1"; Flags: runhidden; RunOnceId: "StopComputeNode"

[UninstallDelete]
Type: files; Name: "{app}\installed.mode"
Type: dirifempty; Name: "{app}"

[Code]

const
  PersistentUninstallKey =
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MediaHubComputeNodePersistentData';


procedure RemovePersistentUninstallEntry;
begin
  RegDeleteKeyIncludingSubkeys(
    HKLM,
    PersistentUninstallKey
  );
end;


procedure RegisterPersistentUninstallEntry;
var
  RuntimeDir: String;
  CleanupScript: String;
  CleanupIcon: String;
  PowerShellExe: String;
  UninstallCommand: String;
begin
  RuntimeDir :=
    ExpandConstant(
      '{commonappdata}\MediaHub\ComputeNode'
    );

  CleanupScript :=
    RuntimeDir +
    '\remove_persistent_data.ps1';

  CleanupIcon :=
    RuntimeDir +
    '\MediaHub-Compute-Node.ico';

  PowerShellExe :=
    ExpandConstant(
      '{sys}\WindowsPowerShell\v1.0\powershell.exe'
    );

  UninstallCommand :=
    '"' +
    PowerShellExe +
    '" -NoProfile -ExecutionPolicy Bypass -File "' +
    CleanupScript +
    '"';

  RegWriteStringValue(
    HKLM,
    PersistentUninstallKey,
    'DisplayName',
    'MediaHub Compute Node – gespeicherte Daten entfernen'
  );

  RegWriteStringValue(
    HKLM,
    PersistentUninstallKey,
    'DisplayVersion',
    '{#MyAppVersion}'
  );

  RegWriteStringValue(
    HKLM,
    PersistentUninstallKey,
    'Publisher',
    '{#MyAppPublisher}'
  );

  RegWriteStringValue(
    HKLM,
    PersistentUninstallKey,
    'DisplayIcon',
    CleanupIcon
  );

  RegWriteStringValue(
    HKLM,
    PersistentUninstallKey,
    'UninstallString',
    UninstallCommand
  );

  RegWriteStringValue(
    HKLM,
    PersistentUninstallKey,
    'QuietUninstallString',
    UninstallCommand
  );

  RegWriteDWordValue(
    HKLM,
    PersistentUninstallKey,
    'NoModify',
    1
  );

  RegWriteDWordValue(
    HKLM,
    PersistentUninstallKey,
    'NoRepair',
    1
  );
end;


procedure CurStepChanged(
  CurStep: TSetupStep
);
begin
  if CurStep = ssPostInstall then
  begin
    ForceDirectories(
      ExpandConstant(
        '{commonappdata}\MediaHub\ComputeNode'
      )
    );

    { Bei Neuinstallation darf kein alter Restdaten-Eintrag bleiben. }
    RemovePersistentUninstallEntry;
  end;
end;


var
  DeletePersistentData: Boolean;


procedure CurUninstallStepChanged(
  CurUninstallStep: TUninstallStep
);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    DeletePersistentData :=
      MsgBox(
        'Sollen die persistenten Daten des MediaHub Compute Node ebenfalls gelöscht werden? Dazu gehören Einstellungen, Pairing-Daten, API-Token, Jobs und installierte Plugins.',
        mbConfirmation,
        MB_YESNO
      ) = IDYES;
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    if DeletePersistentData then
    begin
      RemovePersistentUninstallEntry;

      Exec(
        ExpandConstant('{cmd}'),
        '/C rmdir /S /Q "' +
        ExpandConstant(
          '{commonappdata}\MediaHub\ComputeNode'
        ) +
        '"',
        '',
        SW_HIDE,
        ewWaitUntilTerminated,
        ResultCode
      );
    end;

    if not DeletePersistentData then
    begin
      RegisterPersistentUninstallEntry;
    end;
  end;
end;

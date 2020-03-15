; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "bookmarks"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "Gergely Wootsch"
#define MyAppURL "http://wgergely.github.io/bookmarks"
#define MyAppExeName "bookmarks.exe"
#define MyAppExeDName "bookmarks_d.exe"


[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{43C00B91-E185-48A1-9FF0-0A90F0AB831C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}

ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
DisableDirPage=false
DisableProgramGroupPage=false
; The [Icons] "quicklaunchicon" entry uses {userappdata} but its [Tasks] entry has a proper IsAdminInstallMode Check.
UsedUserAreasWarning=no
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
OutputDir={#SourcePath}..\..\..\{#MyAppName}-standalone

ChangesEnvironment=yes
ChangesAssociations=yes

OutputBaseFilename={#MyAppName}_setup_{#MyAppVersion}
SetupIconFile={#SourcePath}..\..\bookmarks\rsc\icon.ico

;Compression
;https://stackoverflow.com/questions/40447498/best-compression-settings-in-inno-setup-compiler
SolidCompression=no
Compression=lzma2/ultra64
LZMAUseSeparateProcess=yes
LZMADictionarySize=65536
LZMANumFastBytes=64

WizardStyle=modern
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=
VersionInfoTextVersion=
VersionInfoCopyright={#MyAppPublisher}
VersionInfoProductName=
VersionInfoProductVersion=
AppCopyright={#MyAppPublisher}
ShowLanguageDialog=no
WizardImageFile={#SourcePath}inno\WIZMODERNIMAGE.BMP
WizardImageBackColor=clGray
WizardSmallImageFile={#SourcePath}inno\WIZMODERNSMALLIMAGE.BMP
UsePreviousGroup=false
UninstallDisplayIcon={#SourcePath}..\..\bookmarks\rsc\icon.ico
UninstallDisplayName={#MyAppName}

[Languages]
Name: english; MessagesFile: compiler:Default.isl

[installDelete]
Type: filesandordirs; Name: {app}

[Tasks]
Name: desktopicon; Description: {cm:CreateDesktopIcon}; GroupDescription: {cm:AdditionalIcons}; Flags: unchecked
Name: quicklaunchicon; Description: {cm:CreateQuickLaunchIcon}; GroupDescription: {cm:AdditionalIcons}; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Components]
Name: standalone; Description: Standalone; Types: full compact custom; Flags: fixed;
Name: maya; Description: mBookmarks: Maya Plugin; Types: full; Check: DirExists(ExpandConstant('{userdocs}\maya'))

[Files]
Source: {#SourcePath}..\..\..\{#MyAppName}-standalone\{#MyAppName}\*; DestDir: {app}; Components: standalone; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify

; mBookmarks
Source:  {#SourcePath}..\..\..\{#MyAppName}-standalone\{#MyAppName}\shared\{#MyAppName}\maya\mBookmarks.py; DestDir: {userdocs}\maya\plug-ins; Components: maya; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: expandsz; ValueName: "BOOKMARKS_ROOT"; ValueData: "{app}";

; Extension
Root: HKCR; Subkey: ".favourites";                             ValueData: "{#MyAppName}";          Flags: uninsdeletevalue; ValueType: string;  ValueName: ""
Root: HKCR; Subkey: "{#MyAppName}";                     ValueData: "Program {#MyAppName}";  Flags: uninsdeletekey;   ValueType: string;  ValueName: ""
Root: HKCR; Subkey: "{#MyAppName}\DefaultIcon";         ValueData: "{app}\{#MyAppExeName},0";               ValueType: string;  ValueName: ""
Root: HKCR; Subkey: "{#MyAppName}\shell\open\command";  ValueData: """{app}\{#MyAppExeName}"" ""%1""";  ValueType: string;  ValueName: ""
Root: HKCR; Subkey: "{#MyAppName}\shell\open\command";  ValueData: """{app}\{#MyAppExeName}"" ""%1""";  ValueType: string;  ValueName: ""

; Install path
Root: HKCR; Subkey: "{#MyAppName}\installpath";  ValueData: "{app}\{#MyAppExeName}";  ValueType: string;  ValueName: ""
Root: HKCU; Subkey: "Software\{#MyAppName}\{#MyAppName}";  ValueData: "{app}\{#MyAppExeName}";  ValueType: string;  ValueName: "installpath"

[Icons]
Name: {autoprograms}\{#MyAppName}; Filename: {app}\{#MyAppExeName}
Name: {autodesktop}\{#MyAppName}; Filename: {app}\{#MyAppExeName}; Tasks: desktopicon
Name: {userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}; Filename: {app}\{#MyAppExeName}; Tasks: quicklaunchicon

[Run]
Filename: {app}\{#MyAppExeName}; Description: {cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}; Flags: nowait postinstall skipifsilent

; ============================================================
; GitHub 连接一键修复工具 - Inno Setup 安装程序脚本
; 生成一个专业的 setup.exe 安装程序
; ============================================================

#define MyAppName "GitHub 连接一键修复工具"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "GitHub Fixer"
#define MyAppExeName "GitHub修复工具.exe"

[Setup]
; 应用标识（固定，用于卸载识别）
AppId={{8E6C4F2A-3B7D-4A91-9C2E-5D1F6A8B0C3D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\GitHub修复工具
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; 生成安装程序位：安装包自身无需管理员，但安装的程序会请求管理员
PrivilegesRequired=admin
; 输出
OutputDir=installer_output
OutputBaseFilename=GitHub修复工具_Setup
; 图标
SetupIconFile=app_icon.ico
; 压缩设置
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 语言
; 版本信息
VersionInfoVersion=1.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion=1.0.0
; 允许用户选择安装路径
SetupLogging=yes

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: checkedonce

[Files]
; 主程序
Source: "dist\GitHub修复工具.exe"; DestDir: "{app}"; Flags: ignoreversion
; 使用说明
Source: "GitHub修复工具_使用说明.md"; DestDir: "{app}"; Flags: ignoreversion
; 图标
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
; 桌面（如果用户勾选）
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon
; 卸载程序
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\app_icon.ico"

[Run]
; 安装完成后可选运行
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 清理使用说明等文件
Type: files; Name: "{app}\GitHub修复工具_使用说明.md"
Type: files; Name: "{app}\app_icon.ico"

[Code]
// 安装完成后提示信息
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 空实现，保留用于扩展
  end;
end;

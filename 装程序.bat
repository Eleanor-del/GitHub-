@echo off
chcp 65001 >nul
title GitHub 修复工具 - 一键生成安装程序 (Setup.exe)

echo ============================================================
echo   GitHub 连接修复工具 - 安装程序生成向导
echo   自动完成: Python - 打包EXE - InnoSetup - 生成Setup.exe
echo ============================================================
echo.

cd /d "%~dp0"

:: ============================================================
:: 步骤 1: 检查 Python
:: ============================================================
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo  [!] 未检测到 Python，正在自动安装...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe' -OutFile 'python_installer.exe'"
    if exist python_installer.exe (
        python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
        del python_installer.exe
        echo  已安装 Python，请重新运行本脚本
    ) else (
        echo  [错误] Python 下载失败，请手动安装 https://www.python.org/downloads/
    )
    pause
    exit /b 1
)
for /f "delims=" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  ✓ Python: %PYVER%
echo.

:: ============================================================
:: 步骤 2: 安装 PyInstaller 并打包 EXE
:: ============================================================
echo [2/5] 打包主程序为 EXE...
python -m pip show pyinstaller >nul 2>&1
if %errorLevel% neq 0 (
    echo  安装 PyInstaller...
    python -m pip install pyinstaller --quiet
)

set ICON_ARG=
if exist app_icon.ico set ICON_ARG=--icon=app_icon.ico

python -m PyInstaller ^
    --noconfirm --onefile --windowed --uac-admin ^
    --name "GitHub修复工具" --clean %ICON_ARG% ^
    github_fixer.py
if %errorLevel% neq 0 (
    echo  [错误] EXE 打包失败
    pause
    exit /b 1
)
echo  ✓ EXE 打包完成
echo.

:: ============================================================
:: 步骤 3: 检查 Inno Setup
:: ============================================================
echo [3/5] 检查安装程序制作工具 Inno Setup...
set INNO_COMPILER="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %INNO_COMPILER% set INNO_COMPILER="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist %INNO_COMPILER% (
    echo  [!] 未安装 Inno Setup，正在下载安装...
    powershell -Command "Invoke-WebRequest -Uri 'https://jrsoftware.org/download.php/is.exe' -OutFile 'innosetup_installer.exe'"
    if exist innosetup_installer.exe (
        echo  正在静默安装 Inno Setup...
        innosetup_installer.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
        del innosetup_installer.exe
        echo  已安装 Inno Setup
    ) else (
        echo  [错误] Inno Setup 下载失败，请手动下载安装: https://jrsoftware.org/isinfo.php
        pause
        exit /b 1
    )
)
echo  ✓ Inno Setup 就绪
echo.

:: ============================================================
:: 步骤 4: 编译生成 Setup.exe
:: ============================================================
echo [4/5] 正在生成安装程序 Setup.exe（约需30秒）...
set INNO_COMPILER="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %INNO_COMPILER% set INNO_COMPILER="%ProgramFiles%\Inno Setup 6\ISCC.exe"

%INNO_COMPILER% "GitHub修复工具_安装脚本.iss"
if %errorLevel% neq 0 (
    echo  [错误] 安装程序生成失败，请检查上方日志
    pause
    exit /b 1
)
echo  ✓ 安装程序生成成功
echo.

:: ============================================================
:: 步骤 5: 完成
:: ============================================================
echo [5/5] 全部完成！
echo.
echo ============================================================
echo   ✅ 安装程序已生成！
echo.
echo   位置: %cd%\installer_output\GitHub修复工具_Setup.exe
echo.
echo   使用方法:
echo     1. 双击 "GitHub修复工具_Setup.exe"
echo     2. 按向导点击"下一步"即可安装
echo     3. 会自动创建开始菜单和桌面快捷方式
echo     4. 该安装包可发给任何人，双击即可安装使用
echo ============================================================
echo.

if exist installer_output (
    explorer "%~dp0installer_output"
)

pause

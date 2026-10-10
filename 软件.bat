@echo off
chcp 65001 >nul
title GitHub 修复工具 - 一键打包为软件 (EXE)

echo ============================================================
echo   GitHub 连接一键修复工具 - 打包向导
echo   本脚本会自动完成：检查Python - 安装依赖 - 打包EXE
echo ============================================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: ============================================================
:: 步骤 1: 检查 Python
:: ============================================================
echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo  [!] 未检测到 Python，正在尝试自动安装...
    echo  正在下载 Python 安装包...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe' -OutFile 'python_installer.exe'"
    if exist python_installer.exe (
        echo  正在静默安装 Python（会自动加入 PATH）...
        python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
        del python_installer.exe
        echo  已安装 Python，请重新运行本脚本
    ) else (
        echo  [错误] Python 下载失败，请手动安装：
        echo  访问 https://www.python.org/downloads/
        echo  安装时务必勾选 "Add Python to PATH"
    )
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  ✓ 检测到 %PYVER%
echo.

:: ============================================================
:: 步骤 2: 安装 PyInstaller
:: ============================================================
echo [2/4] 检查/安装打包工具 PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if %errorLevel% neq 0 (
    echo  正在安装 PyInstaller（首次约需1-2分钟）...
    python -m pip install pyinstaller --quiet
    if %errorLevel% neq 0 (
        echo  [错误] PyInstaller 安装失败，请检查网络后重试
        echo  可尝试: python -m pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
        pause
        exit /b 1
    )
)
echo  ✓ PyInstaller 就绪
echo.

:: ============================================================
:: 步骤 3: 打包 EXE
:: ============================================================
echo [3/4] 正在打包为 EXE 软件（约需1-2分钟）...
echo.

:: 检查是否提供图标
set ICON_ARG=
if exist app_icon.ico set ICON_ARG=--icon=app_icon.ico

python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --uac-admin ^
    --name "GitHub修复工具" ^
    --clean ^
    %ICON_ARG% ^
    github_fixer.py

if %errorLevel% neq 0 (
    echo.
    echo  [错误] 打包失败，请将上方报错信息截图反馈
    pause
    exit /b 1
)

:: ============================================================
:: 步骤 4: 完成
:: ============================================================
echo.
echo [4/4] 打包完成！
echo.
echo ============================================================
echo   ✅ 软件已生成！
echo.
echo   位置: %cd%\dist\GitHub修复工具.exe
echo.
echo   使用方法:
echo     1. 双击 "GitHub修复工具.exe" 即可运行
echo     2. 首次运行会弹出"用户账户控制"，点击"是"授权
echo     3. 该 exe 可复制到任何 Windows 电脑使用，无需安装 Python
echo ============================================================
echo.

:: 打开 dist 目录
if exist dist (
    explorer "%~dp0dist"
)

pause

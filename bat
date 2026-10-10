@echo off
chcp 65001 >nul
title GitHub 连接一键修复工具

:: 检查是否以管理员身份运行
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 正在请求管理员权限...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 检查 Python 是否安装
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.7+
    echo 下载地址: https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

:: 运行工具
echo 正在启动 GitHub 连接修复工具...
python github_fixer.py

if %errorLevel% neq 0 (
    echo.
    echo [错误] 程序运行出错，请检查 github_fixer.py 是否在同一目录下
    pause
)

@echo off
chcp 936 >nul
title 织造 - 安装
cd /d "%~dp0"

echo.
echo  ============================================
echo    织造 - 安装
echo  ============================================
echo.
echo  安装过程大约一分钟，请不要关闭这个窗口。
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

echo.
echo  按任意键关闭窗口。
pause >nul
@echo off
chcp 936 >nul
title 织造 - 数据服务（请不要关闭这个窗口）
cd /d "%~dp0"

if not exist "server.py" (
  if exist "lingzao-local\server.py" (
    cd /d "%~dp0lingzao-local"
  )
)

if not exist "server.py" (
  echo.
  echo  [出错了] 这里找不到 server.py
  echo  请确认本文件和 lingzao-local 文件夹在同一层。
  echo.
  pause
  exit /b 1
)

netstat -ano | findstr ":8787" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
  echo.
  echo  数据服务已经在运行了，不用重复启动。
  echo  直接回到聊天窗口说话就行。
  echo.
  pause
  exit /b 0
)

echo.
echo  ============================================
echo    织造 - 数据服务启动中
echo  ============================================
echo.
echo  这个黑色窗口需要一直开着，关掉服务就停了。
echo  现在可以回到聊天窗口，直接跟 Agent 说话。
echo.
echo  --------------------------------------------
echo.

set "LINGZAO_LOCAL_BACKEND=justone:JustOneBackend"
python server.py --port 8787

echo.
echo  服务已停止。按任意键关闭窗口。
pause >nul
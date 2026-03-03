@echo off
echo [INFO] Starting Abogen...
echo [INFO] Setting up environment...

REM 确保使用正确的用户目录
set "USERPROFILE=C:\Users\dell"
set "APPDATA=C:\Users\dell\AppData\Roaming"
set "LOCALAPPDATA=C:\Users\dell\AppData\Local"
set "HOME=C:\Users\dell"

echo [INFO] USERPROFILE: %USERPROFILE%
echo [INFO] APPDATA: %APPDATA%
echo [INFO] Working directory: D:\python\abogen

cd /d "D:\python\abogen"
echo [INFO] Launching server on port 8808...
"D:\python\abogen\.venv\scripts\python.exe" -c "from abogen.webui.app import main; main()"

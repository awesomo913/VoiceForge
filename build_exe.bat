@echo off
setlocal EnableDelayedExpansion

echo [VoiceForge] Building exe...

:: Activate venv
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo FAILED: Could not activate venv
    exit /b 1
)

:: Install/update deps
uv pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo FAILED: dependency install
    exit /b 1
)

:: Install PyInstaller if not present
uv pip install pyinstaller
if %errorlevel% neq 0 (
    echo FAILED: PyInstaller install
    exit /b 1
)

:: Build
pyinstaller --noconfirm --onefile --windowed ^
  --name VoiceForge ^
  --add-data "presets/builtin;presets/builtin" ^
  --icon assets/icon.ico ^
  --hidden-import customtkinter ^
  --hidden-import sounddevice ^
  --hidden-import soundfile ^
  --hidden-import pedalboard ^
  --hidden-import pyrubberband ^
  --hidden-import df ^
  --collect-data customtkinter ^
  --collect-submodules customtkinter ^
  --collect-data df ^
  --exclude-module rvc_python ^
  main.py

if %errorlevel% neq 0 (
    echo FAILED: PyInstaller build
    exit /b 1
)

:: Move to My Apps
if not exist "%USERPROFILE%\Desktop\My Apps\" mkdir "%USERPROFILE%\Desktop\My Apps\"
copy /y dist\VoiceForge.exe "%USERPROFILE%\Desktop\My Apps\VoiceForge.exe"
if %errorlevel% neq 0 (
    echo FAILED: Could not copy exe to My Apps
    exit /b 1
)

:: Create Desktop shortcut
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\VoiceForge.lnk'); $s.TargetPath = '%USERPROFILE%\Desktop\My Apps\VoiceForge.exe'; $s.Save()"

echo.
echo [VoiceForge] Build complete!
echo   Exe: %USERPROFILE%\Desktop\My Apps\VoiceForge.exe
echo   Shortcut: %USERPROFILE%\Desktop\VoiceForge.lnk

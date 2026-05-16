@echo off
REM ============================================================
REM  Paperclip — one double-click installer + launcher
REM  Double-click this file. That's it. You're done.
REM ============================================================
setlocal
cd /d "%~dp0"
title Paperclip Setup

echo.
echo  ============================================
echo    PAPERCLIP — setting up. Wait 30 seconds.
echo  ============================================
echo.

REM --- Find Python, install it silently if missing -----------
where pythonw >nul 2>&1
if errorlevel 1 (
    echo  [1/4] Python not found. Downloading and installing...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe -OutFile python_setup.exe"
    python_setup.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del python_setup.exe
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
) else (
    echo  [1/4] Python already installed. Good.
)

REM --- Install dependencies ----------------------------------
echo  [2/4] Installing Paperclip's bits (pynput, pystray, pillow, pywin32, etc.)
pythonw -m pip install --quiet --disable-pip-version-check --upgrade pip
pythonw -m pip install --quiet --disable-pip-version-check pynput pystray pillow pywin32 psutil pyperclip mss uiautomation

REM --- Add to Windows Startup so it boots with the PC --------
echo  [3/4] Setting Paperclip to start automatically with Windows.
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET=%~dp0launch_paperclip.pyw"
powershell -NoProfile -Command "$s=New-Object -ComObject WScript.Shell; $lnk=$s.CreateShortcut('%STARTUP%\Paperclip.lnk'); $lnk.TargetPath='%TARGET%'; $lnk.WorkingDirectory='%~dp0'; $lnk.IconLocation='%TARGET%'; $lnk.Save()"

REM --- Launch it ---------------------------------------------
echo  [4/4] Launching Paperclip.
start "" pythonw "%~dp0launch_paperclip.pyw"

echo.
echo  ============================================
echo    DONE. Look top-left for the paperclip.
echo    Look bottom-right (system tray) for the
echo    settings icon — click the ^^ arrow if
echo    you don't see it.
echo.
echo    USE IT: right-click 3 times, fast,
echo    anywhere. That's the whole thing.
echo  ============================================
echo.
timeout /t 8 >nul
endlocal

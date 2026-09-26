@echo off
setlocal
cd /d "%~dp0"

set "APP_NAME=SunoMasterPromptStudio_v0.5.2"
set "BUILD_VENV=.venv-desktop-build"

echo.
echo ============================================================
echo  Suno Master Prompt Studio v0.5.2 - Windows Desktop Builder
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python Launcher ^(py.exe^) not found.
  echo Install Python 3.11 or 3.12 from python.org and try again.
  pause
  exit /b 1
)

if not exist "%BUILD_VENV%\Scripts\python.exe" (
  echo [1/7] Creating build environment...
  py -3.11 -m venv "%BUILD_VENV%"
  if errorlevel 1 (
    echo Python 3.11 unavailable. Trying default Python...
    py -m venv "%BUILD_VENV%"
    if errorlevel 1 goto :fail
  )
) else (
  echo [1/7] Reusing build environment...
)

call "%BUILD_VENV%\Scripts\activate.bat"
if errorlevel 1 goto :fail

echo [2/7] Installing/updating build tools...
python -m pip install --upgrade pip pytest pyinstaller
if errorlevel 1 goto :fail

echo [3/7] Running tests...
python -m pytest -q
if errorlevel 1 goto :fail

echo [4/7] Checking Python compilation...
python -m compileall -q .
if errorlevel 1 goto :fail

echo [5/7] Cleaning old desktop build...
if exist "build\SunoMasterPromptStudio" rmdir /s /q "build\SunoMasterPromptStudio"
if exist "dist\%APP_NAME%" rmdir /s /q "dist\%APP_NAME%"
if exist "dist\%APP_NAME%_WINDOWS.zip" del /q "dist\%APP_NAME%_WINDOWS.zip"

echo [6/7] Building desktop EXE...
pyinstaller --noconfirm --clean --distpath dist --workpath build\SunoMasterPromptStudio SunoMasterPromptStudio.spec
if errorlevel 1 goto :fail

if not exist "dist\%APP_NAME%\%APP_NAME%.exe" (
  echo [ERROR] EXE was not created.
  goto :fail
)

copy /y "DESKTOP_README.txt" "dist\%APP_NAME%\DESKTOP_README.txt" >nul
copy /y "VERSION.txt" "dist\%APP_NAME%\VERSION.txt" >nul
if not exist "dist\%APP_NAME%\user_data" mkdir "dist\%APP_NAME%\user_data"

echo [7/7] Creating portable ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\%APP_NAME%\*' -DestinationPath 'dist\%APP_NAME%_WINDOWS.zip' -Force"
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo  BUILD PASS
echo  EXE: dist\%APP_NAME%\%APP_NAME%.exe
echo  ZIP: dist\%APP_NAME%_WINDOWS.zip
echo ============================================================
echo.
pause
exit /b 0

:fail
echo.
echo ============================================================
echo  BUILD FAILED
echo  Check the error above. No release should be distributed.
echo ============================================================
echo.
pause
exit /b 1

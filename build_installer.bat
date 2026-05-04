@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  Ultimate Prompt Builder - construction de l installeur
echo ============================================================

REM ---- Verifie que le .exe est deja construit ----
if not exist "dist\UltimatePromptBuilder\UltimatePromptBuilder.exe" (
    echo.
    echo [ERREUR] dist\UltimatePromptBuilder\UltimatePromptBuilder.exe introuvable.
    echo Lance d abord build.bat pour construire l executable.
    pause
    exit /b 1
)

REM ---- Localise Inno Setup compiler (ISCC.exe) ----
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo.
    echo [ERREUR] Inno Setup 6 n est pas installe.
    echo.
    echo Telecharge-le ici : https://jrsoftware.org/isdl.php
    echo Choisis la version standard (unicode), francaise.
    echo Puis relance ce script.
    pause
    exit /b 1
)

echo Inno Setup detecte : %ISCC%

REM ---- Lit la version depuis updater.py ----
for /f "tokens=2 delims= =" %%a in ('findstr /R "^APP_VERSION" updater.py') do (
    set "VER=%%a"
)
set "VER=!VER:"=!"
set "VER=!VER: =!"
echo Version detectee : !VER!

REM ---- Compile l installeur ----
if not exist installer_output mkdir installer_output

echo.
echo Compilation de l installeur (1-2 min)...
echo.

"%ISCC%" /Qp /DMyAppVersion=!VER! installer\ultimate_prompt_builder.iss
if errorlevel 1 (
    echo.
    echo [ERREUR] Compilation echouee.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  TERMINE
echo ============================================================
echo  Installeur : installer_output\UltimatePromptBuilder_setup_!VER!.exe
echo.
echo  Etape suivante :
echo   1. Cree une release sur https://github.com/Jordan-Bourillot/ultimate-prompt-builder/releases/new
echo   2. Tag : v!VER!
echo   3. Upload UltimatePromptBuilder_setup_!VER!.exe comme asset
echo   4. Publish release
echo ============================================================
pause

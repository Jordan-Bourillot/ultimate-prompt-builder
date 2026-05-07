@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  AlphaBeast - construction de l installeur
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

"%ISCC%" /Qp /DMyAppVersion=!VER! installer\alphabeast.iss
if errorlevel 1 (
    echo.
    echo [ERREUR] Compilation echouee.
    pause
    exit /b 1
)

REM ---- Copie sous l ancien nom legacy pour les v1.3.x installees ----
REM Les v1.3.x ont UPDATE_INSTALLER_PATTERN="UltimatePromptBuilder_setup_*.exe"
REM (avant le rebrand AlphaBeast). Sans cet alias, leur fnmatch retourne False
REM et l auto-update ne trouve pas l installer dans la GitHub Release.
if exist "installer_output\AlphaBeast_setup_!VER!.exe" (
    copy /Y "installer_output\AlphaBeast_setup_!VER!.exe" "installer_output\UltimatePromptBuilder_setup_!VER!.exe" >nul
    echo Alias legacy cree : UltimatePromptBuilder_setup_!VER!.exe
)

echo.
echo ============================================================
echo  TERMINE
echo ============================================================
echo  Installeur : installer_output\AlphaBeast_setup_!VER!.exe
echo  Alias v1.3 : installer_output\UltimatePromptBuilder_setup_!VER!.exe
echo.
echo  Etape suivante :
echo   1. Cree une release sur https://github.com/Jordan-Bourillot/ultimate-prompt-builder/releases/new
echo   2. Tag : v!VER!
echo   3. Upload LES DEUX .exe comme assets (les v1.3.x cherchent l ancien nom)
echo   4. Publish release
echo ============================================================
pause

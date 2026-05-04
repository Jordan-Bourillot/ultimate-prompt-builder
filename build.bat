@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  Ultimate Prompt Builder - construction de l executable
echo ============================================================

REM ---- Detection Python ----
py -3.12 -c "import pip" >nul 2>nul
if not errorlevel 1 ( set "PYCMD=py -3.12" & goto :pyfound )
py -3.13 -c "import pip" >nul 2>nul
if not errorlevel 1 ( set "PYCMD=py -3.13" & goto :pyfound )
py -3.11 -c "import pip" >nul 2>nul
if not errorlevel 1 ( set "PYCMD=py -3.11" & goto :pyfound )
py -3 -c "import pip" >nul 2>nul
if not errorlevel 1 ( set "PYCMD=py -3" & goto :pyfound )
echo [ERREUR] Aucun Python 3.10+ trouve.
pause
exit /b 1

:pyfound
echo Python : !PYCMD!

REM ---- Cree/active le venv ----
if not exist .venv\Scripts\python.exe (
    echo Creation du venv...
    !PYCMD! -m venv .venv
    if errorlevel 1 (
        echo [ERREUR] Creation venv echouee.
        pause
        exit /b 1
    )
)
call .venv\Scripts\activate.bat

REM ---- Installe les deps build ----
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Installation des dependances build...
    pip install -r requirements-build.txt
    if errorlevel 1 (
        echo [ERREUR] Installation echouee.
        pause
        exit /b 1
    )
)

REM ---- Genere l icone .ico ----
echo Generation de l icone Triskell...
python tools\make_icon.py
if errorlevel 1 (
    echo [ERREUR] Generation icone echouee.
    pause
    exit /b 1
)

REM ---- Nettoie l ancien build ----
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM ---- Lance PyInstaller ----
echo.
echo Construction en cours (1-3 min selon la machine)...
echo.
pyinstaller ultimate_prompt_builder.spec --noconfirm
if errorlevel 1 (
    echo [ERREUR] PyInstaller a echoue.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  TERMINE
echo ============================================================
echo  Executable : dist\UltimatePromptBuilder\UltimatePromptBuilder.exe
echo.
echo  Etape suivante : double-clique build_installer.bat pour
echo  generer l installeur Windows (setup.exe).
echo ============================================================
pause

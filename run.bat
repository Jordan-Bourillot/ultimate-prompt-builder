@echo off
cd /d "%~dp0"
REM Utilise `py` (Python launcher) au lieu de `python` car certains systèmes ont
REM Python d'Inkscape ou MS Store devant le vrai Python 3.x dans le PATH.
REM `py` choisit toujours le dernier Python installé via py-launcher.
py app.py
if errorlevel 1 pause

@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Creez l'environnement avec python -m venv .venv
    echo Puis executez .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo RouteLab : ouvrez http://127.0.0.1:5000 dans votre navigateur.
echo Pour arreter le serveur, appuyez sur Ctrl+C.
".venv\Scripts\python.exe" app.py
pause

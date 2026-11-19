@echo off
setlocal
cd /d "%~dp0"

echo === Sincronizador de karaoke: instalacion ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python. Instala Python 3.9 o superior desde https://www.python.org
    echo y marca la casilla "Add python.exe to PATH" durante la instalacion.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 goto error
)

echo Instalando dependencias (puede tardar varios minutos y descargar ~2 GB)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error

where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo.
    echo AVISO: ffmpeg no esta instalado. Instalalo con:
    echo     winget install ffmpeg
    echo y reinicia esta ventana.
)

echo.
echo Creando acceso directo en el Escritorio y en el menu Inicio...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0crear_acceso_directo.ps1"

echo.
echo Listo. Abre el programa con el acceso directo "Sincronizador de karaoke"
echo (o con run.bat). No muevas ni borres esta carpeta.
pause
exit /b 0

:error
echo.
echo Algo fallo durante la instalacion. Revisa los mensajes de arriba.
pause
exit /b 1

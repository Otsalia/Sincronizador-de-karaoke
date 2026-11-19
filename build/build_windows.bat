@echo off
setlocal
rem Construye el ejecutable de Windows. Ejecutar desde cualquier carpeta.
cd /d "%~dp0\.."

echo === Construyendo Sincronizador de karaoke ===
echo.

if not exist ".venv-build\Scripts\python.exe" (
    python -m venv .venv-build
    if errorlevel 1 goto error
)
set PY=.venv-build\Scripts\python.exe

%PY% -m pip install --upgrade pip
rem PyTorch solo CPU: mucho mas ligero. Para GPU NVIDIA usa el codigo fuente (install.bat).
%PY% -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto error
%PY% -m pip install stable-ts demucs pyinstaller
if errorlevel 1 goto error

%PY% -m PyInstaller build\karaoke_sync.spec --noconfirm --distpath dist --workpath build\work
if errorlevel 1 goto error

echo.
echo Listo: dist\KaraokeSync\KaraokeSync.exe
echo.
echo Para crear el instalador, abre build\installer.iss con Inno Setup y pulsa Compilar
echo (o ejecuta: ISCC build\installer.iss).
pause
exit /b 0

:error
echo.
echo La construccion fallo. Revisa los mensajes de arriba.
pause
exit /b 1

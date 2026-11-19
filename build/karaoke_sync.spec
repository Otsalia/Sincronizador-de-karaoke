# -*- mode: python ; coding: utf-8 -*-
# Configuración de PyInstaller para el Sincronizador de karaoke.
#
# Genera dos ejecutables que comparten las mismas librerías:
#   KaraokeSync.exe        -> la ventana del programa (sin consola)
#   KaraokeSyncWorker.exe  -> hace la alineación en segundo plano (se puede cancelar)
#
# Uso (desde la raíz del repositorio):
#   pyinstaller build/karaoke_sync.spec --noconfirm --distpath dist --workpath build/work
import os
from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas, binaries, hiddenimports = [], [], ["tiktoken_ext.openai_public"]

# Paquetes que cargan archivos de datos o módulos de forma dinámica
for pkg in ("stable_whisper", "whisper", "demucs", "tiktoken", "tiktoken_ext", "torchaudio"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:  # el paquete no está instalado (p. ej. demucs opcional)
        print(f"[spec] aviso: no se pudo recoger {pkg}: {e}")

# Icono de la ventana (el programa lo carga desde la carpeta assets)
datas.append((os.path.join(ROOT, "assets"), "assets"))

# ffmpeg y modelos opcionales: si existen estas carpetas, se incluyen en el programa
for extra in ("ffmpeg", "models"):
    folder = os.path.join(ROOT, "build", extra)
    if os.path.isdir(folder):
        datas.append((folder, extra))

a = Analysis(
    [os.path.join(ROOT, "karaoke_sync.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "IPython", "jupyter", "notebook", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe_gui = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="KaraokeSync",
    console=False,          # ventana sin consola
    icon=os.path.join(ROOT, "assets", "icon.ico"),
)

exe_worker = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="KaraokeSyncWorker",
    console=True,           # necesita consola para enviar el progreso; se lanza oculta
)

coll = COLLECT(
    exe_gui, exe_worker,
    a.binaries, a.datas,
    strip=False, upx=False,
    name="KaraokeSync",
)

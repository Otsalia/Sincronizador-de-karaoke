"""
Sincronizador de karaoke / Karaoke Sync
Alinea la letra de una canción con el audio (MP3, AAC, FLAC, OPUS, M4A...)
y exporta .ass (karaoke con \\k por sílaba) y/o .srt.

Requisitos:
  - Python 3.9+
  - ffmpeg instalado y en el PATH   (Windows: winget install ffmpeg)
  - stable-ts  (el programa tiene un botón para instalarlo)

Uso:  python karaoke_sync.py
"""
import importlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unicodedata
from collections import deque
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

MODELO = "small"
__version__ = "1.0.0"
FROZEN = getattr(sys, "frozen", False)          # True dentro del .exe (PyInstaller)
APP_DIR = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))
RES_DIR = getattr(sys, "_MEIPASS", APP_DIR)      # donde PyInstaller deja los recursos
AUDIO_EXTS = ["mp3", "aac", "flac", "opus", "m4a", "ogg", "wav", "wma", "mp4", "webm"]

# --------------------------------------------------------------------------
# Idiomas de la letra: (clave, código de Whisper, modo de sílabas)
#   latin  : cada vocal es una sílaba (español, inglés, portugués, francés)
#   romaji : como latin, con la opción de separar la «n»  (arigatou -> a ri ga to u)
#   pinyin : sílabas del pinyin (nihao -> ni hao, xiang -> xiang)
#   cjk    : un carácter = una sílaba (kanji/kana, hanzi, hangul)
# El romaji y el pinyin se alinean con el modelo "es" porque son letras latinas.
# --------------------------------------------------------------------------
LANG_DEFS = [
    ("es", "es", "latin"),
    ("en", "en", "latin"),
    ("ja_kanji", "ja", "cjk"),
    ("ja_romaji", "es", "romaji"),
    ("zh_kanji", "zh", "cjk"),
    ("zh_pinyin", "es", "pinyin"),
    ("pt", "pt", "latin"),
    ("fr", "fr", "latin"),
    ("ko", "ko", "cjk"),
]

LANG_NAMES = {
    "es": {"es": "Español", "en": "Inglés", "ja_kanji": "Japonés (kanji)",
           "ja_romaji": "Japonés (romaji)", "zh_kanji": "Chino (kanji)",
           "zh_pinyin": "Chino (pinyin)", "pt": "Portugués", "fr": "Francés",
           "ko": "Coreano (hangul)"},
    "en": {"es": "Spanish", "en": "English", "ja_kanji": "Japanese (kanji)",
           "ja_romaji": "Japanese (romaji)", "zh_kanji": "Chinese (kanji)",
           "zh_pinyin": "Chinese (pinyin)", "pt": "Portuguese", "fr": "French",
           "ko": "Korean (hangul)"},
}

# --------------------------------------------------------------------------
# Textos de la interfaz
# --------------------------------------------------------------------------
TXT = {
    "es": {
        "title": "Sincronizador de karaoke",
        "pick_audio": "Elegir audio…",
        "no_file": "(ningún archivo)",
        "theme_on": "Modo oscuro: activado",
        "theme_off": "Modo oscuro: desactivado",
        "ui_lang": "Idioma de la interfaz:",
        "lyrics_lang": "Idioma de la letra:",
        "isolate": "Aislar voz (demucs)",
        "export": "Exportar:",
        "n_cb": "Separar la «n» como sílaba (u n me i)",
        "t_cb": "Separar la «t» doble como sílaba (ki t ta)",
        "formats": "Formatos aceptados: {list}",
        "style": "Estilo ASS:",
        "line_type": "Tipo de línea:",
        "kind_comment": "Comentario (Comment)",
        "kind_dialogue": "Diálogo (Dialogue)",
        "lyrics_label": "Letra (un verso por línea):",
        "start": "▶  Empezar",
        "ready": "Listo.",
        "offset": "Desfase de tiempos (s):",
        "offset_hint": "+ retrasa · − adelanta",
        "offset_bad_title": "Desfase no válido",
        "offset_bad_body": "Escribe un número, por ejemplo 0.15 o -0.2.",
        "cancel": "Cancelar",
        "rom_off": "No disponible con kanji, hangul ni pinyin.",
        "lead": "Empezar antes (s):",
        "tail": "Terminar después (s):",
        "pad_bad_title": "Margen no válido",
        "pad_bad_body": "Los márgenes deben ser números entre 0 y 5, por ejemplo 0.10.",
        "cancelled": "Cancelado.",
        "proc_fail": "El proceso terminó con un error inesperado.",
        "st_loading": "Cargando el modelo… (la primera vez se descarga)",
        "st_aligning": "Alineando la letra con el audio…",
        "st_aligning_iso": "Aislando la voz y alineando…",
        "st_writing": "Generando archivos…",
        "st_installing": "Instalando {pkg}… no cierres la ventana.",
        "install_stable": "Instalar stable-ts",
        "need_stable": "Falta la librería stable-ts (pulsa el botón para instalarla; "
                       "puede tardar varios minutos y descargar ~2 GB).",
        "need_ffmpeg": "No se encuentra ffmpeg. Instálalo (Windows: «winget install "
                       "ffmpeg») y reinicia el programa.",
        "installing": "Instalando {pkg}… no cierres la ventana.",
        "installed": "{pkg} instalado correctamente. Pulsa Empezar.",
        "install_fail": "No se pudo instalar {pkg}.",
        "install_fail_title": "Error al instalar",
        "install_fail_body": "Comando:\n{cmd}\n\n{out}",
        "missing_title": "Faltan datos",
        "missing_body": "Elige un audio y pega la letra.",
        "fmt_title": "Formato",
        "fmt_body": "Marca al menos .ass o .srt.",
        "demucs_title": "Falta demucs",
        "demucs_ask": "Para aislar la voz hace falta demucs.\n\n"
                      "¿Instalarlo ahora? (puede tardar unos minutos)",
        "aligning": "Alineando… (la primera vez descarga el modelo)",
        "done": "Listo en {time}: guardado como «{name}» ({exts}) junto al audio.",
        "error": "Error",
        "error_status": "Error.",
        "dep_stable": "Falta stable-ts. Pulsa el botón «Instalar stable-ts» "
                      "de la parte superior de la ventana.",
        "dep_demucs": "Para aislar la voz hace falta demucs. Instálalo con:\n\n{cmd}\n\n"
                      "o desmarca «Aislar voz».",
        "dialog_title": "Elegir audio",
        "ft_audio": "Audio",
        "ft_all": "Todos los archivos",
    },
    "en": {
        "title": "Karaoke Sync",
        "pick_audio": "Choose audio…",
        "no_file": "(no file)",
        "theme_on": "Dark mode: on",
        "theme_off": "Dark mode: off",
        "ui_lang": "Interface language:",
        "lyrics_lang": "Lyrics language:",
        "isolate": "Isolate vocals (demucs)",
        "export": "Export:",
        "n_cb": "Split «n» into its own syllable (u n me i)",
        "t_cb": "Split double «t» into its own syllable (ki t ta)",
        "formats": "Accepted formats: {list}",
        "style": "ASS style:",
        "line_type": "Line type:",
        "kind_comment": "Comment",
        "kind_dialogue": "Dialogue",
        "lyrics_label": "Lyrics (one verse per line):",
        "start": "▶  Start",
        "ready": "Ready.",
        "offset": "Time offset (s):",
        "offset_hint": "+ delays · − advances",
        "offset_bad_title": "Invalid offset",
        "offset_bad_body": "Enter a number, for example 0.15 or -0.2.",
        "cancel": "Cancel",
        "rom_off": "Not available with kanji, hangul or pinyin.",
        "lead": "Start earlier (s):",
        "tail": "End later (s):",
        "pad_bad_title": "Invalid margin",
        "pad_bad_body": "Margins must be numbers between 0 and 5, for example 0.10.",
        "cancelled": "Cancelled.",
        "proc_fail": "The process ended with an unexpected error.",
        "st_loading": "Loading the model… (it is downloaded the first time)",
        "st_aligning": "Aligning the lyrics with the audio…",
        "st_aligning_iso": "Isolating the vocals and aligning…",
        "st_writing": "Writing files…",
        "st_installing": "Installing {pkg}… don't close the window.",
        "install_stable": "Install stable-ts",
        "need_stable": "The stable-ts library is missing (press the button to install it; "
                       "it can take several minutes and download ~2 GB).",
        "need_ffmpeg": "ffmpeg was not found. Install it (Windows: “winget install "
                       "ffmpeg”) and restart the program.",
        "installing": "Installing {pkg}… don't close the window.",
        "installed": "{pkg} installed successfully. Press Start.",
        "install_fail": "Could not install {pkg}.",
        "install_fail_title": "Installation error",
        "install_fail_body": "Command:\n{cmd}\n\n{out}",
        "missing_title": "Missing data",
        "missing_body": "Choose an audio file and paste the lyrics.",
        "fmt_title": "Format",
        "fmt_body": "Tick at least .ass or .srt.",
        "demucs_title": "demucs is missing",
        "demucs_ask": "demucs is required to isolate the vocals.\n\n"
                      "Install it now? (it can take a few minutes)",
        "aligning": "Aligning… (the first run downloads the model)",
        "done": "Done in {time}: saved as “{name}” ({exts}) next to the audio.",
        "error": "Error",
        "error_status": "Error.",
        "dep_stable": "stable-ts is missing. Press the “Install stable-ts” button "
                      "at the top of the window.",
        "dep_demucs": "demucs is required to isolate the vocals. Install it with:\n\n{cmd}\n\n"
                      "or untick “Isolate vocals”.",
        "dialog_title": "Choose audio",
        "ft_audio": "Audio",
        "ft_all": "All files",
    },
}

# --------------------------------------------------------------------------
# Separación en sílabas
# --------------------------------------------------------------------------
VOWELS = set("aeiouáéíóúüàèìòùâêîôûāēīōū")
ONSETS = {
    "sh", "ch", "ts", "ky", "gy", "ny", "hy", "my", "ry", "py", "by", "dy",
    "ty", "fy", "jy", "zy", "ll", "rr", "pr", "br", "tr", "dr", "cr", "gr",
    "fr", "pl", "bl", "cl", "gl", "fl", "th", "ph", "wh", "qu",
}
PY_VOWELS = set("aeiouüvāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ")
CJK_ATTACH = set("ゃゅょぁぃぅぇぉゎャュョァィゥェォヮっッー")  # se pegan al carácter anterior


def clean_word(word):
    """Quita signos de puntuación. Devuelve (palabra_limpia, índices_originales)."""
    keep = [i for i, c in enumerate(word) if c.isalnum() or c in "'’-"]
    while keep and word[keep[0]] == "-":
        keep.pop(0)
    while keep and word[keep[-1]] == "-":
        keep.pop()
    return "".join(word[i] for i in keep), keep


def latin_cuts(clean, n_sola=False, t_sola=False):
    low = clean.lower()
    vidx = [i for i, c in enumerate(low) if c in VOWELS]
    if not vidx:
        return [0, len(clean)]

    def aparte(ch):
        return (ch == "n" and n_sola) or (ch == "t" and t_sola)

    cuts = [0]
    for prev, cur in zip(vidx, vidx[1:]):
        cluster = low[prev + 1:cur]
        k = len(cluster)
        if k == 0:
            cuts.append(cur)
            continue
        onset = 2 if k >= 2 and cluster[-2:] in ONSETS else 1
        rest = cluster[:k - onset]
        for j, ch in enumerate(rest):
            if aparte(ch):                   # «n» o «t» doble como sílaba propia
                cuts.append(prev + 1 + j)
        cuts.append(cur - onset)
    tail = low[vidx[-1] + 1:]
    if tail and aparte(tail[0]):
        cuts.append(vidx[-1] + 1)
    cuts.append(len(clean))
    return sorted(set(cuts))


def pinyin_cuts(clean):
    low = clean.lower()
    n = len(low)
    cuts = {0, n}
    i = 0
    while i < n:
        c = low[i]
        if c in "'’-":                       # separador explícito: xi'an
            cuts.update((i, i + 1))
            i += 1
            continue
        j = i + 2 if low[i:i + 2] in ("zh", "ch", "sh") else (i if c in PY_VOWELS else i + 1)
        k = j
        while k < n and low[k] in PY_VOWELS:
            k += 1
        if k == j:                           # sin vocal (n, ng, m...)
            k = max(j, i + 1)
            while k < n and low[k] not in PY_VOWELS and low[k] not in "'’-":
                k += 1
        else:
            nxt2 = low[k + 2] if k + 2 < n else ""
            nxt1 = low[k + 1] if k + 1 < n else ""
            if low[k:k + 2] == "ng" and nxt2 not in PY_VOWELS:
                k += 2
            elif low[k:k + 1] == "n" and nxt1 not in PY_VOWELS:
                k += 1
            elif low[k:k + 1] == "r" and k + 1 >= n:
                k += 1
        cuts.add(k)
        i = k
    return sorted(cuts)


def cjk_cuts(clean):
    cuts = [0]
    for i in range(1, len(clean)):
        c, p = clean[i], clean[i - 1]
        if c in CJK_ATTACH:
            continue
        if c.isascii() and c.isalnum() and p.isascii() and p.isalnum():
            continue                         # una palabra en letras latinas no se parte
        cuts.append(i)
    cuts.append(len(clean))
    return cuts


def syllable_cuts(clean, mode="latin", n_sola=False, t_sola=False):
    if mode == "cjk":
        return cjk_cuts(clean)
    if mode == "pinyin":
        return pinyin_cuts(clean)
    return latin_cuts(clean, n_sola, t_sola)


def split_syllables(word, mode="latin", n_sola=False, t_sola=False):
    clean, _ = clean_word(word)
    if not clean:
        return []
    cuts = syllable_cuts(clean, mode, n_sola, t_sola)
    out = []
    for a, b in zip(cuts, cuts[1:]):
        t = clean[a:b]
        if mode == "pinyin":
            t = t.strip("'’-")
        if t:
            out.append(t)
    return out


# --------------------------------------------------------------------------
# Construcción de líneas con tiempos
# --------------------------------------------------------------------------
def pieces_to_chars(result):
    """Cada letra recibe su tiempo (interpolado dentro de cada trozo que devuelve Whisper)."""
    chars = []
    for seg in result.segments:
        for w in seg.words:
            cs = [c for c in w.word if not c.isspace()]
            n = len(cs)
            if n == 0:
                continue
            dur = max(w.end - w.start, 0.0)
            for j, c in enumerate(cs):
                chars.append((c, w.start + dur * j / n, w.start + dur * (j + 1) / n))
    return chars


def lines_from_original(chars, lyric_lines, mode, n_sola, t_sola):
    """Usa las palabras de TU letra y les asigna los tiempos letra por letra."""
    lines, idx = [], 0
    for line in lyric_lines:
        syls = []
        for word in line:
            wchars = chars[idx:idx + len(word)]
            idx += len(word)
            clean, keep = clean_word(word)
            if not clean:
                continue
            cuts = syllable_cuts(clean, mode, n_sola, t_sola)
            ws = []
            for a, b in zip(cuts, cuts[1:]):
                text = clean[a:b]
                if mode == "pinyin":
                    text = text.strip("'’-")
                if not text:
                    continue
                ws.append([text, wchars[keep[a]][1], wchars[keep[b - 1]][2], False])
            if ws:
                ws[-1][3] = True             # fin de palabra
                syls.extend(tuple(x) for x in ws)
        if syls:
            lines.append(syls)
    return lines


def lines_from_pieces(result, mode, n_sola, t_sola):
    """Plan B si el texto no coincide: usa las palabras tal como las devuelve Whisper."""
    lines = []
    for seg in result.segments:
        syls = []
        for w in seg.words:
            parts = split_syllables(w.word, mode, n_sola, t_sola)
            if not parts:
                continue
            total = sum(len(p) for p in parts)
            dur = max(w.end - w.start, 0.01)
            cur = w.start
            for i, p in enumerate(parts):
                d = dur * len(p) / total
                syls.append((p, cur, cur + d, i == len(parts) - 1))
                cur += d
        if syls:
            lines.append(syls)
    return lines


def build_lines(result, lyrics, mode="latin", n_sola=False, t_sola=False):
    lyric_lines = [ln.split() for ln in lyrics.splitlines() if ln.split()]
    chars = pieces_to_chars(result)
    total = sum(len(w) for ln in lyric_lines for w in ln)
    if total == len(chars):
        return lines_from_original(chars, lyric_lines, mode, n_sola, t_sola)
    return lines_from_pieces(result, mode, n_sola, t_sola)


# --------------------------------------------------------------------------
# Archivos de salida
# --------------------------------------------------------------------------
def fmt_srt(t):
    ms = int(round(max(t, 0) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_ass_cs(cs):
    cs = max(int(cs), 0)
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def write_srt(lines, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, syls in enumerate(lines, 1):
            text = " ".join(s[0] for s in syls)
            f.write(f"{i}\n{fmt_srt(syls[0][1])} --> {fmt_srt(syls[-1][2])}\n{text}\n\n")


def write_ass(lines, path, style="OP Romanji", kind="Comment"):
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
        "LayoutResX: 1920\nLayoutResY: 1080\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: {style},Arial,72,&H0000FFFF,&H00FFFFFF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,0,0,1,4,2,2,45,45,60,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(header)
        for syls in lines:
            # Cada \k dura hasta el inicio de la siguiente sílaba, así la suma
            # de los \k es exactamente la duración de la línea.
            bounds = [int(round(s[1] * 100)) for s in syls] + [int(round(syls[-1][2] * 100))]
            text = ""
            last = len(syls) - 1
            for i, (syl, _s, _e, fin_palabra) in enumerate(syls):
                d = max(bounds[i + 1] - bounds[i], 0)
                text += f"{{\\k{d}}}{syl}"
                if fin_palabra and i != last:
                    text += " "
            f.write(f"{kind}: 0,{fmt_ass_cs(bounds[0])},{fmt_ass_cs(bounds[-1])},"
                    f"{style},,0,0,0,,{text}\n")


def free_base(base, exts):
    """Devuelve 'base', 'base (2)', 'base (3)'... el primero cuyos archivos no existan."""
    n = 1
    while True:
        cand = base if n == 1 else f"{base} ({n})"
        if not any(os.path.exists(cand + e) for e in exts):
            return cand
        n += 1


# --------------------------------------------------------------------------
# Desfase de tiempos
# --------------------------------------------------------------------------
def parse_offset(text):
    """'+0.15', '-0,2', '0.3' -> float. Lanza ValueError si no es un número válido."""
    t = (text or "").strip().replace(",", ".").replace("−", "-")
    if not t:
        return 0.0
    v = float(t)
    if not math.isfinite(v):
        raise ValueError(t)
    return v


def apply_offset(lines, off):
    if not off:
        return lines
    return [[(t, max(s + off, 0.0), max(e + off, 0.0), fw) for t, s, e, fw in syls]
            for syls in lines]


def parse_margin(text):
    """Margen en segundos, entre 0 y 5. Lanza ValueError si no es válido."""
    v = parse_offset(text)
    if not 0.0 <= v <= 5.0:
        raise ValueError(text)
    return v


def apply_padding(lines, lead, tail):
    """Whisper suele marcar el inicio tarde y el final pronto. Esto adelanta el inicio
    de cada línea `lead` segundos y retrasa su final `tail` segundos, sin invadir la
    línea vecina: si el hueco entre dos líneas es pequeño, se reparte entre las dos."""
    total = lead + tail
    if not lines or total <= 0:
        return lines
    n = len(lines)
    lead_eff, tail_eff = [0.0] * n, [0.0] * n
    lead_eff[0] = min(lead, lines[0][0][1])          # la primera línea no baja de 0 s
    tail_eff[-1] = tail
    for i in range(n - 1):
        gap = max(lines[i + 1][0][1] - lines[i][-1][2], 0.0)
        tail_eff[i] = min(tail, gap * tail / total)
        lead_eff[i + 1] = min(lead, gap * lead / total)
    out = []
    for i, syls in enumerate(lines):
        syls = list(syls)
        t, st, e, f = syls[0]
        syls[0] = (t, st - lead_eff[i], e, f)
        t, st, e, f = syls[-1]
        syls[-1] = (t, st, e + tail_eff[i], f)
        out.append(syls)
    return out


# --------------------------------------------------------------------------
# Configuración guardada
# --------------------------------------------------------------------------
def config_path():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "KaraokeSync", "config.json")


def load_config():
    try:
        with open(config_path(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def save_config(d):
    try:
        p = config_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _bool(v, default):
    return v if isinstance(v, bool) else default


# --------------------------------------------------------------------------
# Alineación (stable-ts / Whisper) en un proceso aparte, para poder cancelarla
# --------------------------------------------------------------------------
MARK = "@@KS@@"


def have(module):
    importlib.invalidate_caches()
    return importlib.util.find_spec(module) is not None


def python_exe():
    """Intérprete de Python para lanzar procesos (evita pythonw.exe, que no tiene consola)."""
    exe = sys.executable
    if os.name == "nt" and os.path.basename(exe).lower() == "pythonw.exe":
        cand = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.exists(cand):
            return cand
    return exe


def child_command(args_path):
    """Comando para ejecutar la alineación en un proceso aparte."""
    if FROZEN:
        worker = os.path.join(APP_DIR, "KaraokeSyncWorker.exe")   # versión con consola oculta
        return [worker if os.path.exists(worker) else sys.executable, "--align", args_path]
    return [python_exe(), os.path.abspath(__file__), "--align", args_path]


def prepare_environment():
    """Si hay un ffmpeg incluido junto al programa, lo pone al principio del PATH."""
    for base in (RES_DIR, APP_DIR):
        for d in (os.path.join(base, "ffmpeg"), base):
            if os.path.isfile(os.path.join(d, "ffmpeg.exe")) or \
                    os.path.isfile(os.path.join(d, "ffmpeg")):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
                return


def model_root():
    """Carpeta 'models' incluida con el programa (si existe), para no descargar el modelo."""
    for base in (RES_DIR, APP_DIR):
        d = os.path.join(base, "models")
        if os.path.isdir(d):
            return d
    return None


def emit(**kw):
    print(MARK + json.dumps(kw, ensure_ascii=False), flush=True)


def run_child(args_path):
    """Se ejecuta como:  python karaoke_sync.py --align args.json"""
    import traceback
    try:
        with open(args_path, encoding="utf-8") as f:
            a = json.load(f)
        if not have("stable_whisper"):
            emit(t="error", kind="stable_whisper")
            sys.exit(1)
        if a["iso"] and not have("demucs"):
            emit(t="error", kind="demucs")
            sys.exit(1)
        import stable_whisper

        emit(t="stage", key="loading")
        root = model_root()
        model = stable_whisper.load_model(MODELO, **({"download_root": root} if root else {}))

        emit(t="stage", key="aligning_iso" if a["iso"] else "aligning")
        kwargs = dict(language=a["code"], original_split=True)
        if a["iso"]:
            kwargs["denoiser"] = "demucs"

        try:
            import inspect
            has_cb = "progress_callback" in inspect.signature(model.align).parameters
        except Exception:  # noqa: BLE001
            has_cb = False
        if has_cb:
            state = {"last": -1.0, "first": True}

            def cb(*cb_args):
                try:
                    seek, total = float(cb_args[0]), float(cb_args[1])
                    if total <= 0:
                        return
                    pct = max(0.0, min(100.0, seek / total * 100.0))
                    if state["first"]:
                        state["first"] = False
                        emit(t="stage", key="aligning")
                    if pct - state["last"] >= 1.0 or pct >= 100.0:
                        state["last"] = pct
                        emit(t="progress", pct=round(pct, 1))
                except Exception:  # noqa: BLE001
                    pass
            kwargs["progress_callback"] = cb

        result = model.align(a["audio"], a["lyrics"], **kwargs)
        segs = [[[w.word, float(w.start), float(w.end)] for w in seg.words]
                for seg in result.segments]
        with open(a["out"], "w", encoding="utf-8") as f:
            json.dump(segs, f, ensure_ascii=False)
        emit(t="done")
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        emit(t="error", kind="exception", msg=f"{type(e).__name__}: {e}")
        sys.exit(1)


# --------------------------------------------------------------------------
# Interfaz
# --------------------------------------------------------------------------
FONT = "Segoe UI"

THEMES = {
    True: dict(  # negro
        bg="#0a0a0a", panel="#1a1a1a", field="#111111", fg="#f2f2f2",
        muted="#8f8f8f", accent="#f2f2f2", accent_fg="#000000",
        accent_hover="#ffffff", border="#2c2c2c", select="#3a3a3a", check="#cfcfcf",
    ),
    False: dict(  # claro
        bg="#f4f4f4", panel="#e1e1e1", field="#ffffff", fg="#111111",
        muted="#666666", accent="#111111", accent_fg="#ffffff",
        accent_hover="#333333", border="#c4c4c4", select="#cfcfcf", check="#bdbdbd",
    ),
}


def title_bar_dark(win, on):
    """Barra de título oscura/clara en Windows 10/11 (en otros sistemas se ignora)."""
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        for attr in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(ctypes.c_int(1 if on else 0)),
                ctypes.sizeof(ctypes.c_int))
    except Exception:  # noqa: BLE001
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.set_icon()
        cfg = load_config()
        self.ui = cfg.get("ui") if cfg.get("ui") in ("es", "en") else "es"
        self.dark = _bool(cfg.get("dark"), True)
        keys = [k for k, _, _ in LANG_DEFS]
        self.cfg_lang = keys.index(cfg["lang"]) if cfg.get("lang") in keys else 0
        self.cfg_kind = cfg.get("kind") if cfg.get("kind") in (0, 1) else 0
        self.cfg = cfg
        self.cfg_lead = self._margin(cfg.get("lead"), 0.10)
        self.cfg_tail = self._margin(cfg.get("tail"), 0.15)
        self.last_dir = cfg.get("last_dir") if os.path.isdir(str(cfg.get("last_dir"))) else None

        self.fit_window()
        self.audio_path = None
        self.busy = False
        self.cancelled = False
        self.proc = None
        self.stage = None
        self.pct = None
        self.t0 = 0.0
        self.bar_mode = "idle"
        self.combos = []
        self.build()
        self.apply_theme()
        self.retranslate()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def set_icon(self):
        """Icono de la ventana y de la barra de tareas (Windows)."""
        if os.name != "nt":
            return
        for base in (RES_DIR, APP_DIR):
            ico = os.path.join(base, "assets", "icon.ico")
            if os.path.isfile(ico):
                try:
                    self.iconbitmap(default=ico)
                except tk.TclError:
                    pass
                return

    def fit_window(self):
        """Tamaño razonable para pantallas pequeñas, centrado y por encima de la barra de tareas."""
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(840, int(sw * 0.9))
        h = max(min(700, sh - 160), 540)       # deja sitio a la barra de título y de tareas
        x = max((sw - w) // 2, 0)
        y = max((sh - h) // 2 - 30, 0)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(min(700, w), min(540, h))

    @staticmethod
    def _margin(v, default):
        ok = isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 5
        return float(v) if ok else default

    def tr(self, key, **kw):
        s = TXT[self.ui][key]
        return s.format(**kw) if kw else s

    # ---------------- construcción ----------------
    def build(self):
        cfg = self.cfg

        # Barra inferior primero: el botón Empezar siempre queda visible
        bottom = ttk.Frame(self, padding=14)
        bottom.pack(side="bottom", fill="x")
        row = ttk.Frame(bottom)
        row.pack(fill="x")
        self.start_btn = ttk.Button(row, style="Accent.TButton", command=self.start)
        self.start_btn.pack(side="left")
        self.cancel_btn = ttk.Button(row, style="Cancel.TButton", command=self.cancel)
        self.bar = ttk.Progressbar(bottom, mode="determinate", maximum=100)
        self.bar.pack(fill="x", pady=(12, 6))
        self.status = ttk.Label(bottom, text="", style="Muted.TLabel")
        self.status.pack(anchor="w")

        # Aviso de requisitos (solo se muestra si falta algo)
        self.setup_frame = ttk.Frame(self, padding=(14, 10, 14, 0))
        self.setup_label = ttk.Label(self.setup_frame, text="", style="Warn.TLabel",
                                     wraplength=600, justify="left")
        self.setup_label.pack(side="left", fill="x", expand=True)
        self.install_btn = ttk.Button(self.setup_frame, command=self.install_deps)

        # Audio (izquierda) + modo oscuro e idioma de la interfaz (derecha)
        self.top = ttk.Frame(self, padding=(14, 14, 14, 4))
        self.top.pack(fill="x")
        left = ttk.Frame(self.top)
        left.pack(side="left", anchor="n")
        pick_row = ttk.Frame(left)
        pick_row.pack(anchor="w")
        self.pick_btn = ttk.Button(pick_row, command=self.pick_audio)
        self.pick_btn.pack(side="left")
        self.audio_label = ttk.Label(pick_row, text="", style="Muted.TLabel")
        self.audio_label.pack(side="left", padx=12)
        self.formats_label = ttk.Label(left, text="", style="Small.TLabel",
                                       wraplength=430, justify="left")
        self.formats_label.pack(anchor="w", pady=(8, 0))

        right = ttk.Frame(self.top)
        right.pack(side="right", anchor="n")
        self.theme_btn = ttk.Button(right, command=self.toggle_theme)
        self.theme_btn.pack(fill="x")
        row2 = ttk.Frame(right)
        row2.pack(fill="x", pady=(8, 0))
        self.ui_lang_label = ttk.Label(row2, text="")
        self.ui_lang_label.pack(side="left", padx=(0, 8))
        self.ui_var = tk.StringVar(value="English" if self.ui == "en" else "Español")
        self.ui_combo = self.combo(row2, self.ui_var, ["Español", "English"], 9, readonly=True)
        self.ui_combo.pack(side="left")
        self.ui_combo.bind("<<ComboboxSelected>>", self.on_ui_lang)

        # Opciones de alineación
        opts = ttk.Frame(self, padding=(14, 10, 14, 6))
        opts.pack(fill="x")
        self.lyrics_lang_label = ttk.Label(opts, text="")
        self.lyrics_lang_label.pack(side="left")
        self.lang_var = tk.StringVar()
        self.lang_combo = self.combo(opts, self.lang_var, [], 18, readonly=True)
        self.lang_combo.config(values=[LANG_NAMES[self.ui][k] for k, _, _ in LANG_DEFS])
        self.lang_combo.current(self.cfg_lang)
        self.lang_combo.pack(side="left", padx=(6, 18))
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self.update_n_state())
        self.iso_var = tk.BooleanVar(value=_bool(cfg.get("iso"), False))
        self.iso_cb = ttk.Checkbutton(opts, variable=self.iso_var)
        self.iso_cb.pack(side="left")

        # Formatos
        fmt = ttk.Frame(self, padding=(14, 4))
        fmt.pack(fill="x")
        self.export_label = ttk.Label(fmt, text="")
        self.export_label.pack(side="left")
        self.srt_var = tk.BooleanVar(value=_bool(cfg.get("srt"), False))
        self.ass_var = tk.BooleanVar(value=_bool(cfg.get("ass"), True))
        ttk.Checkbutton(fmt, text=".ass (karaoke)", variable=self.ass_var
                        ).pack(side="left", padx=8)
        ttk.Checkbutton(fmt, text=".srt", variable=self.srt_var
                        ).pack(side="left", padx=(0, 18))

        # Desfase de tiempos (no se guarda: depende de cada canción)
        tim = ttk.Frame(self, padding=(14, 4))
        tim.pack(fill="x")
        self.offset_label = ttk.Label(tim, text="")
        self.offset_label.pack(side="left")
        self.offset_var = tk.StringVar(value="0.00")
        self.offset_spin = ttk.Spinbox(tim, textvariable=self.offset_var, from_=-60.0,
                                       to=60.0, increment=0.05, format="%.2f", width=8,
                                       font=(FONT, 12))
        self.offset_spin.pack(side="left", padx=8)
        self.offset_hint = ttk.Label(tim, text="", style="Small.TLabel")
        self.offset_hint.pack(side="left")

        # Márgenes de cada línea: empezar antes / terminar después (sí se guardan)
        pad = ttk.Frame(self, padding=(14, 4))
        pad.pack(fill="x")
        self.lead_label = ttk.Label(pad, text="")
        self.lead_label.pack(side="left")
        self.lead_var = tk.StringVar(value=f"{self.cfg_lead:.2f}")
        ttk.Spinbox(pad, textvariable=self.lead_var, from_=0.0, to=5.0, increment=0.05,
                    format="%.2f", width=6, font=(FONT, 12)).pack(side="left", padx=(8, 22))
        self.tail_label = ttk.Label(pad, text="")
        self.tail_label.pack(side="left")
        self.tail_var = tk.StringVar(value=f"{self.cfg_tail:.2f}")
        ttk.Spinbox(pad, textvariable=self.tail_var, from_=0.0, to=5.0, increment=0.05,
                    format="%.2f", width=6, font=(FONT, 12)).pack(side="left", padx=8)

        # Opciones de romaji (solo se activan con «Japonés (romaji)»)
        rom = ttk.Frame(self, padding=(14, 2))
        rom.pack(fill="x")
        self.n_var = tk.BooleanVar(value=_bool(cfg.get("n"), False))
        self.n_cb = ttk.Checkbutton(rom, variable=self.n_var)
        self.n_cb.pack(side="left", padx=(0, 18))
        self.t_var = tk.BooleanVar(value=_bool(cfg.get("t"), False))
        self.t_cb = ttk.Checkbutton(rom, variable=self.t_var)
        self.t_cb.pack(side="left", padx=(0, 18))
        self.rom_hint = ttk.Label(rom, text="", style="Small.TLabel")
        self.rom_hint.pack(side="left")

        # Opciones ASS
        ass = ttk.Frame(self, padding=(14, 4))
        ass.pack(fill="x")
        self.style_label = ttk.Label(ass, text="")
        self.style_label.pack(side="left")
        style0 = cfg.get("style") if isinstance(cfg.get("style"), str) and cfg.get("style").strip() \
            else "OP Romanji"
        self.style_var = tk.StringVar(value=style0)
        ttk.Entry(ass, textvariable=self.style_var, width=18,
                  font=(FONT, 12)).pack(side="left", padx=(6, 18))
        self.kind_label = ttk.Label(ass, text="")
        self.kind_label.pack(side="left")
        self.kind_var = tk.StringVar()
        self.kind_combo = self.combo(ass, self.kind_var, [], 20, readonly=True)
        self.kind_combo.config(values=[self.tr("kind_comment"), self.tr("kind_dialogue")])
        self.kind_combo.current(self.cfg_kind)
        self.kind_combo.pack(side="left", padx=6)

        # Letra
        self.lyrics_label = ttk.Label(self, text="", padding=(14, 10, 14, 4))
        self.lyrics_label.pack(anchor="w")
        box = ttk.Frame(self, padding=(14, 0, 14, 0))
        box.pack(fill="both", expand=True)
        self.text = tk.Text(box, wrap="word", font=(FONT, 14), relief="flat",
                            padx=12, pady=10, borderwidth=0, highlightthickness=1,
                            undo=True)
        sb = ttk.Scrollbar(box, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def combo(self, parent, var, values, width, readonly=False):
        c = ttk.Combobox(parent, textvariable=var, values=values, width=width,
                         font=(FONT, 12), state="readonly" if readonly else "normal")
        self.combos.append(c)
        return c

    # ---------------- configuración guardada ----------------
    def settings(self):
        return {
            "dark": self.dark,
            "ui": self.ui,
            "lang": self.current_lang()[0],
            "iso": self.iso_var.get(),
            "ass": self.ass_var.get(),
            "srt": self.srt_var.get(),
            "n": self.n_var.get(),
            "t": self.t_var.get(),
            "lead": self.safe_margin(self.lead_var, 0.10),
            "tail": self.safe_margin(self.tail_var, 0.15),
            "style": self.style_var.get().strip() or "OP Romanji",
            "kind": max(self.kind_combo.current(), 0),
            "last_dir": self.last_dir,
        }

    @staticmethod
    def safe_margin(var, default):
        try:
            return parse_margin(var.get())
        except ValueError:
            return default

    def save_settings(self):
        save_config(self.settings())

    def on_close(self):
        self.save_settings()
        p = self.proc
        if p is not None and p.poll() is None:
            try:
                p.kill()
            except OSError:
                pass
        self.destroy()

    # ---------------- idioma de la interfaz ----------------
    def on_ui_lang(self, _event=None):
        self.ui = "en" if self.ui_var.get() == "English" else "es"
        self.retranslate()
        self.save_settings()

    def retranslate(self):
        T = self.tr
        self.title(T("title"))
        self.pick_btn.config(text=T("pick_audio"))
        if not self.audio_path:
            self.audio_label.config(text=T("no_file"))
        self.ui_lang_label.config(text=T("ui_lang"))
        self.lyrics_lang_label.config(text=T("lyrics_lang"))
        self.iso_cb.config(text=T("isolate"))
        self.export_label.config(text=T("export"))
        self.offset_label.config(text=T("offset"))
        self.offset_hint.config(text=T("offset_hint"))
        self.lead_label.config(text=T("lead"))
        self.tail_label.config(text=T("tail"))
        self.n_cb.config(text=T("n_cb"))
        self.t_cb.config(text=T("t_cb"))
        self.formats_label.config(
            text=T("formats", list=", ".join(e.upper() for e in AUDIO_EXTS)))
        self.style_label.config(text=T("style"))
        self.kind_label.config(text=T("line_type"))
        self.lyrics_label.config(text=T("lyrics_label"))
        self.start_btn.config(text=T("start"))
        self.cancel_btn.config(text=T("cancel"))
        self.install_btn.config(text=T("install_stable"))

        idx = max(self.lang_combo.current(), 0)
        self.lang_combo.config(values=[LANG_NAMES[self.ui][k] for k, _, _ in LANG_DEFS])
        self.lang_combo.current(idx)

        idx = max(self.kind_combo.current(), 0)
        self.kind_combo.config(values=[T("kind_comment"), T("kind_dialogue")])
        self.kind_combo.current(idx)

        self.theme_btn.config(text=T("theme_on") if self.dark else T("theme_off"))
        self.update_n_state()
        self.check_requirements()
        if self.busy:
            self.refresh_progress()
        else:
            self.status.config(text=T("ready"))

    def current_lang(self):
        i = max(self.lang_combo.current(), 0)
        return LANG_DEFS[i]          # (clave, código Whisper, modo)

    def update_n_state(self):
        usable = self.current_lang()[2] in ("latin", "romaji")
        for cb in (self.n_cb, self.t_cb):
            cb.state(["!disabled"] if usable else ["disabled"])
        self.rom_hint.config(text="" if usable else self.tr("rom_off"))

    # ---------------- tema ----------------
    def apply_theme(self):
        t = THEMES[self.dark]
        self.configure(bg=t["bg"])
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=t["bg"], foreground=t["fg"], fieldbackground=t["field"],
                    bordercolor=t["border"], lightcolor=t["panel"], darkcolor=t["panel"],
                    troughcolor=t["panel"], font=(FONT, 12))
        s.configure("TFrame", background=t["bg"])
        s.configure("TLabel", background=t["bg"], foreground=t["fg"])
        s.configure("Muted.TLabel", foreground=t["muted"])
        s.configure("Small.TLabel", foreground=t["muted"], font=(FONT, 10))
        s.configure("Warn.TLabel", foreground="#e5a000" if self.dark else "#a05a00")
        s.configure("TButton", background=t["panel"], foreground=t["fg"],
                    padding=(14, 8), borderwidth=0, focusthickness=0)
        s.map("TButton", background=[("active", t["select"]), ("disabled", t["panel"])],
              foreground=[("disabled", t["muted"])])
        s.configure("Accent.TButton", background=t["accent"], foreground=t["accent_fg"],
                    font=(FONT, 12, "bold"), padding=(24, 8))
        s.map("Accent.TButton",
              background=[("active", t["accent_hover"]), ("disabled", t["panel"])],
              foreground=[("disabled", t["muted"])])
        s.configure("Cancel.TButton", background=t["panel"], foreground=t["fg"],
                    font=(FONT, 12, "bold"), padding=(20, 8), borderwidth=0)
        s.map("Cancel.TButton", background=[("active", t["select"]), ("disabled", t["bg"])],
              foreground=[("disabled", t["muted"])])
        s.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])
        s.map("TCheckbutton", background=[("active", t["bg"])],
              foreground=[("disabled", t["muted"])],
              indicatorcolor=[("selected", t["check"]), ("!selected", t["field"])])
        s.configure("TEntry", fieldbackground=t["field"], foreground=t["fg"],
                    insertcolor=t["fg"], padding=4)
        s.configure("TSpinbox", fieldbackground=t["field"], background=t["panel"],
                    foreground=t["fg"], arrowcolor=t["fg"], insertcolor=t["fg"], padding=4)
        s.configure("TCombobox", fieldbackground=t["field"], background=t["panel"],
                    foreground=t["fg"], arrowcolor=t["fg"], selectbackground=t["field"],
                    selectforeground=t["fg"], padding=4)
        s.map("TCombobox", fieldbackground=[("readonly", t["field"])],
              foreground=[("readonly", t["fg"])],
              selectbackground=[("readonly", t["field"])],
              selectforeground=[("readonly", t["fg"])])
        s.configure("Horizontal.TProgressbar", background=t["accent"],
                    troughcolor=t["panel"], borderwidth=0)
        s.configure("Vertical.TScrollbar", background=t["panel"], troughcolor=t["bg"],
                    arrowcolor=t["fg"], borderwidth=0)

        self.text.configure(bg=t["field"], fg=t["fg"], insertbackground=t["fg"],
                            selectbackground=t["select"], selectforeground=t["fg"],
                            highlightbackground=t["border"], highlightcolor=t["muted"])
        for c in self.combos:
            try:
                pop = self.tk.eval(f"ttk::combobox::PopdownWindow {c}")
                self.tk.eval(
                    f"{pop}.f.l configure -background {t['field']} -foreground {t['fg']} "
                    f"-selectbackground {t['select']} -selectforeground {t['fg']} "
                    f"-font {{{FONT} 12}}")
            except tk.TclError:
                pass
        title_bar_dark(self, self.dark)

    def toggle_theme(self):
        self.dark = not self.dark
        self.apply_theme()
        self.theme_btn.config(text=self.tr("theme_on") if self.dark else self.tr("theme_off"))
        self.save_settings()

    # ---------------- barra de progreso y estado ----------------
    def bar_indeterminate(self):
        if self.bar_mode != "ind":
            self.bar.stop()
            self.bar.config(mode="indeterminate")
            self.bar.start(12)
            self.bar_mode = "ind"

    def bar_determinate(self, pct):
        if self.bar_mode != "det":
            self.bar.stop()
            self.bar.config(mode="determinate", maximum=100)
            self.bar_mode = "det"
        self.bar["value"] = pct

    def bar_reset(self):
        self.bar.stop()
        self.bar.config(mode="determinate", maximum=100)
        self.bar["value"] = 0
        self.bar_mode = "idle"

    def set_busy(self, on):
        self.busy = on
        if on:
            self.t0 = time.time()
            self.start_btn.state(["disabled"])
            self.cancel_btn.pack(side="left", padx=(10, 0))
            self.cancel_btn.state(["!disabled"])
            self.tick()
        else:
            self.start_btn.state(["!disabled"])
            self.cancel_btn.pack_forget()
            self.bar_reset()

    def set_stage(self, key, **kw):
        """Se puede llamar desde otro hilo."""
        self.stage = (key, kw)
        self.pct = None
        self.after(0, self.refresh_progress)

    def set_pct(self, pct):
        self.pct = pct
        self.after(0, self.refresh_progress)

    def refresh_progress(self):
        if not self.busy or not self.stage:
            return
        key, kw = self.stage
        text = self.tr("st_" + key, **kw)
        if self.pct is not None:
            text += f" {self.pct:.0f}%"
            self.bar_determinate(self.pct)
        else:
            self.bar_indeterminate()
        sec = int(time.time() - self.t0)
        text += f"  ·  {sec // 60:02d}:{sec % 60:02d}"
        self.status.config(text=text)

    def tick(self):
        if self.busy:
            self.refresh_progress()
            self.after(500, self.tick)

    def finish(self, status, error=None):
        self.proc = None
        self.set_busy(False)
        self.status.config(text=status)
        if error:
            messagebox.showerror(self.tr("error"), error)

    # ---------------- requisitos ----------------
    def check_requirements(self):
        problems = []
        need_install = not FROZEN and not have("stable_whisper")   # en el .exe ya viene incluido
        if need_install:
            problems.append(self.tr("need_stable"))
        if shutil.which("ffmpeg") is None:
            problems.append(self.tr("need_ffmpeg"))
        if problems:
            self.setup_label.config(text="\n".join(problems))
            self.setup_frame.pack(fill="x", before=self.top)
            if need_install:
                self.install_btn.pack(side="right", padx=(10, 0))
            else:
                self.install_btn.pack_forget()
        else:
            self.setup_frame.pack_forget()

    def install_deps(self, package="stable-ts"):
        self.cancelled = False
        self.install_btn.state(["disabled"])
        self.set_busy(True)
        self.set_stage("installing", pkg=package)
        threading.Thread(target=self.install_worker, args=(package,), daemon=True).start()

    def install_worker(self, package):
        cmd = [python_exe(), "-m", "pip", "install", package]
        ok, out = False, ""
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            out, _ = self.proc.communicate()
            ok = self.proc.returncode == 0
        except Exception as e:  # noqa: BLE001
            out = f"{type(e).__name__}: {e}"

        def done():
            self.install_btn.state(["!disabled"])
            if self.cancelled:
                self.finish(self.tr("cancelled"))
            elif ok:
                self.finish(self.tr("installed", pkg=package))
            else:
                self.finish(self.tr("install_fail", pkg=package),
                            self.tr("install_fail_body", cmd=" ".join(cmd),
                                    out=(out or "")[-1500:]))
            self.check_requirements()
        self.after(0, done)

    # ---------------- acciones ----------------
    def pick_audio(self):
        types_ = [(self.tr("ft_audio"), " ".join(f"*.{e}" for e in AUDIO_EXTS)),
                  (self.tr("ft_all"), "*.*")]
        p = filedialog.askopenfilename(title=self.tr("dialog_title"), filetypes=types_,
                                       initialdir=self.last_dir or None)
        if p:
            self.audio_path = p
            self.last_dir = os.path.dirname(p)
            self.audio_label.config(text=os.path.basename(p), style="TLabel")

    def cancel(self):
        if not self.busy:
            return
        self.cancelled = True
        self.cancel_btn.state(["disabled"])
        p = self.proc
        if p is not None and p.poll() is None:
            try:
                p.terminate()
            except OSError:
                pass

    def start(self):
        lyrics = unicodedata.normalize("NFC", self.text.get("1.0", "end")).strip()
        if not self.audio_path or not lyrics:
            messagebox.showwarning(self.tr("missing_title"), self.tr("missing_body"))
            return
        if not (self.srt_var.get() or self.ass_var.get()):
            messagebox.showwarning(self.tr("fmt_title"), self.tr("fmt_body"))
            return
        try:
            offset = parse_offset(self.offset_var.get())
        except ValueError:
            messagebox.showwarning(self.tr("offset_bad_title"), self.tr("offset_bad_body"))
            return
        try:
            lead = parse_margin(self.lead_var.get())
            tail = parse_margin(self.tail_var.get())
        except ValueError:
            messagebox.showwarning(self.tr("pad_bad_title"), self.tr("pad_bad_body"))
            return
        if self.iso_var.get() and not have("demucs"):
            if messagebox.askyesno(self.tr("demucs_title"), self.tr("demucs_ask")):
                self.install_deps("demucs")
            return

        self.save_settings()
        _key, code, mode = self.current_lang()
        self.cancelled = False
        self.set_busy(True)
        self.set_stage("loading")
        opts = dict(
            audio=self.audio_path, lyrics=lyrics, code=code, mode=mode,
            iso=self.iso_var.get(), want_srt=self.srt_var.get(),
            want_ass=self.ass_var.get(), n_sola=self.n_var.get(),
            t_sola=self.t_var.get(),
            style=self.style_var.get().strip() or "Default",
            kind=["Comment", "Dialogue"][max(self.kind_combo.current(), 0)],
            offset=offset, lead=lead, tail=tail,
        )
        threading.Thread(target=self.worker, kwargs=opts, daemon=True).start()

    def child_error(self, err, log):
        if err:
            kind = err.get("kind")
            if kind == "stable_whisper":
                return self.tr("dep_stable")
            if kind == "demucs":
                return self.tr("dep_demucs", cmd=f'"{python_exe()}" -m pip install demucs')
            return err.get("msg") or self.tr("proc_fail")
        return self.tr("proc_fail") + "\n\n" + "\n".join(list(log)[-8:])

    def worker(self, audio, lyrics, code, mode, iso, want_srt, want_ass, n_sola, t_sola,
               style, kind, offset, lead, tail):
        tmp = tempfile.mkdtemp(prefix="karaoke_sync_")
        status, error = "", None
        try:
            args_p = os.path.join(tmp, "args.json")
            out_p = os.path.join(tmp, "result.json")
            with open(args_p, "w", encoding="utf-8") as f:
                json.dump(dict(audio=audio, lyrics=lyrics, code=code, iso=iso, out=out_p),
                          f, ensure_ascii=False)
            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
            self.proc = subprocess.Popen(
                child_command(args_p),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding="utf-8", errors="replace", env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

            err, log = None, deque(maxlen=30)
            for line in self.proc.stdout:
                line = line.rstrip("\r\n")
                if line.startswith(MARK):
                    try:
                        msg = json.loads(line[len(MARK):])
                    except ValueError:
                        continue
                    t = msg.get("t")
                    if t == "stage":
                        self.set_stage(msg.get("key", "aligning"))
                    elif t == "progress":
                        self.set_pct(float(msg.get("pct", 0)))
                    elif t == "error":
                        err = msg
                elif line.strip():
                    log.append(line)
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
            rc = self.proc.returncode

            if self.cancelled:
                status = self.tr("cancelled")
            elif err or rc != 0 or not os.path.exists(out_p):
                status = self.tr("error_status")
                error = self.child_error(err, log)
            else:
                self.set_stage("writing")
                with open(out_p, encoding="utf-8") as f:
                    segs = json.load(f)
                result = types.SimpleNamespace(segments=[
                    types.SimpleNamespace(words=[
                        types.SimpleNamespace(word=w, start=s, end=e) for w, s, e in seg])
                    for seg in segs])
                lines = build_lines(result, lyrics, mode, n_sola, t_sola)
                lines = apply_offset(apply_padding(lines, lead, tail), offset)
                exts = [e for e, on in ((".ass", want_ass), (".srt", want_srt)) if on]
                base = free_base(os.path.splitext(audio)[0], exts)
                if want_ass:
                    write_ass(lines, base + ".ass", style, kind)
                if want_srt:
                    write_srt(lines, base + ".srt")
                sec = int(time.time() - self.t0)
                status = self.tr("done", time=f"{sec // 60:02d}:{sec % 60:02d}",
                                 name=os.path.basename(base), exts=", ".join(exts))
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            status = self.tr("error_status")
            error = f"{type(e).__name__}: {e}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.after(0, lambda s=status, er=error: self.finish(s, er))


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    prepare_environment()
    if len(sys.argv) >= 3 and sys.argv[1] == "--align":
        run_child(sys.argv[2])
    else:
        App().mainloop()

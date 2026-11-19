# Sincronizador de karaoke

Programa de escritorio para **Windows** que toma una canción y su letra y genera automáticamente
los tiempos del karaoke **separados por sílabas**, en formato `.ass` (con etiquetas `\k`) y/o `.srt`.

Ejemplo de una línea generada:

```
{\k50}ki{\k20}t{\k55}ta {\k40}shin{\k50}ji{\k30}tsu {\k40}no {\k27}ta{\k53}bi
```

Los tiempos los calcula [Whisper](https://github.com/openai/whisper) (a través de
[stable-ts](https://github.com/jianfch/stable-ts)) y, si quieres, antes se aísla la voz con
[Demucs](https://github.com/facebookresearch/demucs). El resultado se puede abrir directamente
en Aegisub o en cualquier reproductor/editor que soporte `.ass`.

<!-- Cuando tengas una captura de pantalla, guárdala como docs/captura.png y quita los
     símbolos de comentario de la línea siguiente:
![Captura del programa](docs/captura.png)
-->

## Video tutorial

🎬 **[Ver el video tutorial]([https://PEGA-AQUI-EL-ENLACE-DE-TU-VIDEO](https://youtu.be/mCUtOeKxY_A))**

## Qué hace

1. Eliges un audio (MP3, AAC, FLAC, OPUS, M4A, OGG, WAV, WMA, MP4 o WEBM).
2. Pegas la letra, un verso por línea.
3. Eliges el idioma de la letra.
4. Pulsas **Empezar** y obtienes el `.ass` y/o el `.srt` junto al audio.

### Idiomas de la letra y cómo separa las sílabas

| Idioma | Separación en sílabas | Ejemplo |
|---|---|---|
| Español, Inglés, Portugués, Francés | Cada vocal es una sílaba | `can ci ón` |
| Japonés (romaji) | Cada vocal es una sílaba; la «n» se pega a la anterior | `a ri ga to u`, `shin ji tsu` |
| Japonés (kanji) | Un carácter por sílaba; `ゃゅょ`, `っ` y `ー` se pegan al anterior | `夏 の 気 配` |
| Chino (kanji) | Un carácter por sílaba | `我 爱 你` |
| Chino (pinyin) | Sílabas de pinyin (acepta tonos y el apóstrofo `xi'an`) | `ni hao`, `zhong guo` |
| Coreano (hangul) | Un bloque por sílaba | `사 랑 해 요` |

> Para letras en romaji usa **Japonés (romaji)**. En las opciones de kanji los tiempos son por
> carácter; el programa no calcula lecturas (furigana).

### Opciones del programa

| Opción | Para qué sirve |
|---|---|
| **Aislar voz (demucs)** | Quita la música antes de alinear. Mejora la precisión si hay mucho instrumental, pero tarda más. |
| **Exportar `.ass` / `.srt`** | Elige uno o ambos formatos. |
| **Desfase de tiempos (s)** | Mueve todo el karaoke a la vez. Positivo = retrasa, negativo = adelanta (por ejemplo `+0.15`). |
| **Empezar antes (s)** | Adelanta el inicio de cada línea. Compensa que Whisper suele marcar el inicio algo tarde. Por defecto `0.10`. |
| **Terminar después (s)** | Retrasa el final de cada línea. Compensa que Whisper suele marcar el final algo pronto. Por defecto `0.15`. |
| **Separar la «n»** | `unmei` → `u n me i` en vez de `un me i`. |
| **Separar la «t» doble** | `kitta` → `ki t ta` en vez de `kit ta`. |
| **Estilo ASS** | Nombre del estilo que se escribe en el archivo (por defecto `OP Romanji`). |
| **Tipo de línea** | `Comment` (como en las plantillas de Aegisub) o `Dialogue` (visible directamente en un reproductor). |
| **Cancelar** | Detiene el proceso en cualquier momento. |
| **Modo oscuro / idioma de la interfaz** | Tema oscuro o claro, y la interfaz en español o inglés. |

Los márgenes no hacen que una línea invada a la vecina: si el hueco entre dos líneas es pequeño,
se reparte entre las dos. La configuración (tema, idioma, casillas, estilo, márgenes...) se guarda
en `%APPDATA%\KaraokeSync\config.json`. El desfase no se guarda, porque depende de cada canción.

### Archivos que genera

- Se guardan **junto al audio**, con su mismo nombre: `cancion.ass`, `cancion.srt`.
- Si ya existen, no se sobrescriben: `cancion (2).ass`, `cancion (3).ass`...
- **`.ass`**: resolución 1920x1080, un `\k` por sílaba. Las sílabas de una misma palabra van juntas
  y las palabras separadas por un espacio. La suma de los `\k` es exactamente la duración de la línea.
- **`.srt`**: una entrada por verso, con las sílabas separadas por espacios (`A ri ga to`).
  El `.srt` no guarda resolución, porque es solo texto con tiempos.

## Qué necesita y qué se instala

| Componente | Para qué | Cómo se instala |
|---|---|---|
| **Python 3.9 o superior** | Ejecutar el programa | Manual: [python.org](https://www.python.org) (marca *Add python.exe to PATH*) |
| **ffmpeg** | Leer los distintos formatos de audio | Manual: `winget install ffmpeg` |
| **stable-ts** (incluye PyTorch y Whisper) | Calcular los tiempos de la letra | Automático con `install.bat` |
| **demucs** | Aislar la voz (opcional) | Automático con `install.bat` |
| **Modelos de Whisper (`small`, unos 460 MB) y de Demucs** | Que funcionen las dos librerías anteriores | Se descargan solos **la primera vez** que se usan (hace falta internet ese primer uso) |

Reserva varios GB de espacio libre: PyTorch y los modelos ocupan bastante. Funciona solo con la
CPU; con una tarjeta NVIDIA puedes instalar antes la versión de PyTorch con CUDA desde
[pytorch.org](https://pytorch.org) para que la alineación sea mucho más rápida.

## Instalación (Windows)

1. Instala **Python** y **ffmpeg** (ver tabla de arriba).
2. Descarga el proyecto: botón verde **Code → Download ZIP** y descomprímelo en una carpeta fija
   (por ejemplo `C:\Programas\karaoke-sync`), o usa `git clone`:
   ```
   git clone https://github.com/TU-USUARIO/karaoke-sync.git
   ```
3. Haz doble clic en **`install.bat`**. Crea un entorno virtual dentro de la carpeta, instala las
   dependencias (puede tardar varios minutos) y deja un **acceso directo con icono** en el
   Escritorio y en el menú Inicio.
4. Abre el programa con ese acceso directo (también sirve `run.bat`).

Puedes mover el acceso directo donde quieras o anclarlo a la barra de tareas, pero **la carpeta del
proyecto debe quedarse donde está**. Si pierdes el acceso directo, ejecuta
`crear_acceso_directo.bat`.

## Cómo usarlo, paso a paso

1. Abre el programa y pulsa **Elegir audio…**.
2. Elige el **idioma de la letra**.
3. Pega la **letra** en el cuadro grande, **un verso por línea**.
4. (Opcional) Marca **Aislar voz**, ajusta el desfase o los márgenes, el estilo ASS y las opciones
   de romaji.
5. Pulsa **Empezar**. Abajo verás la etapa (cargando el modelo, alineando…), el porcentaje y el
   tiempo transcurrido.
6. Cuando termine, busca los archivos junto al audio y ábrelos en Aegisub o en tu editor.

### Consejos

- La letra debe corresponder al audio: si pegas otra versión o partes que no suenan, la alineación
  se desfasa.
- La alineación automática no es perfecta. Si todo sale un poco corrido, usa el **desfase**; si el
  inicio o el final de cada línea queda justo, sube los márgenes de 0.05 en 0.05.
- La primera vez tarda más porque descarga el modelo. Las siguientes son mucho más rápidas.

## Preguntas frecuentes

**Me dice que falta ffmpeg.**
Instálalo con `winget install ffmpeg` y reinicia el programa (y la ventana de comandos).

**`install.bat` dice que no encuentra Python.**
Instala Python desde python.org y marca *Add python.exe to PATH* durante la instalación.

**Windows muestra «Windows protegió su PC» al abrir un `.bat`.**
Puede pasar con archivos descargados de internet. Pulsa *Más información → Ejecutar de todas formas*.
Los `.bat` son texto plano; puedes abrirlos con el Bloc de notas para ver qué hacen.

**Aparece un error por falta de `demucs`.**
Instálalo con `.venv\Scripts\python.exe -m pip install demucs` (desde la carpeta del proyecto) o
desmarca **Aislar voz**.

**Tarda mucho.**
Funciona con la CPU; los audios largos o aislar la voz alargan el proceso. Con una tarjeta NVIDIA y
PyTorch con CUDA va mucho más rápido.

**Los tiempos no son perfectos.**
Es una limitación de la alineación automática. Ajusta el desfase y los márgenes y termina de
pulirlo en Aegisub.

## Opcional: ejecutable independiente y compilación automática

Para uso personal basta con la instalación de arriba. Si quieres un `.exe` que no necesite instalar
nada (lo que incluye PyTorch, Whisper y Demucs, por lo que pesa del orden de 1 GB), el repositorio
trae la configuración para construirlo:

```
build\build_windows.bat
```

Genera `dist\KaraokeSync\KaraokeSync.exe`. Para crear además un instalador, compila
`build\installer.iss` con [Inno Setup](https://jrsoftware.org/isinfo.php).

También hay un flujo de GitHub Actions (`.github/workflows/build-windows.yml`) que construye el
instalador y una versión portable al subir una etiqueta de versión:

```
git tag v1.0.0
git push origin v1.0.0
```

> **Aviso:** esta parte es experimental. Empaquetar PyTorch con Whisper y Demucs suele requerir
> ajustes, y las versiones muy recientes de PyTorch pueden chocar con Demucs. Si la compilación
> falla, la instalación con `install.bat` sigue funcionando.

## Limitaciones

- Pensado para Windows; no está probado en otros sistemas.
- La alineación automática puede requerir ajustes manuales.
- En kanji/hanzi/hangul los tiempos son por carácter; no se calculan lecturas.
- El audio necesita ffmpeg y, la primera vez, conexión a internet para descargar los modelos.

## Créditos y licencia

Basado en [Whisper](https://github.com/openai/whisper) (OpenAI), [stable-ts](https://github.com/jianfch/stable-ts)
y [Demucs](https://github.com/facebookresearch/demucs) (Meta). Código bajo licencia MIT (ver `LICENSE`).

---

## English summary

**Karaoke Sync** is a Windows desktop tool that aligns song lyrics with audio and exports
**syllable-level karaoke subtitles**: `.ass` (1920x1080, `\k` tags) and/or `.srt`.

- **How it works:** Whisper (through stable-ts) computes the timings; optionally Demucs isolates the
  vocals first. Lyrics are split into syllables according to the chosen language.
- **Lyrics languages:** Spanish, English, Portuguese, French, Japanese (kanji / romaji),
  Chinese (hanzi / pinyin) and Korean (hangul).
- **Audio formats:** MP3, AAC, FLAC, OPUS, M4A, OGG, WAV, WMA, MP4, WEBM.
- **Tuning:** global time offset, per-line "start earlier / end later" margins, romaji options
  (split «n», split double «t»), ASS style name and line type (`Comment` / `Dialogue`).
- **Interface:** dark/light mode, Spanish/English UI, progress with a cancel button, saved settings.

**Requirements:** Python 3.9+, ffmpeg (`winget install ffmpeg`), and — installed automatically by
`install.bat` — stable-ts (with PyTorch and Whisper) and Demucs. Whisper/Demucs models are downloaded
on first use (internet needed once).

**Install:** download the repository, run `install.bat` (creates a virtual environment and a desktop
shortcut with an icon), then open the program from the shortcut. Keep the project folder where it is.
Output files are saved next to the audio file and never overwrite previous results.

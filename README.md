# 🧛 The Dracula — YouTube Downloader CLI

```
  ██████╗ ██████╗  █████╗  ██████╗██╗   ██╗██╗      █████╗ 
  ██╔══██╗██╔══██╗██╔══██╗██╔════╝██║   ██║██║     ██╔══██╗
  ██║  ██║██████╔╝███████║██║     ██║   ██║██║     ███████║
  ██║  ██║██╔══██╗██╔══██║██║     ██║   ██║██║     ██╔══██║
  ██████╔╝██║  ██║██║  ██║╚██████╗╚██████╔╝███████╗██║  ██║
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
  ╔══════════════════════════════════════════════════════════╗
  ║   🧛 The Dracula  ·  YouTube Downloader CLI  v1.0.4    ║
  ║      Powered by yt-dlp  ·  Rising from the dark...     ║
  ╚══════════════════════════════════════════════════════════╝
```

> A powerful, dark-themed YouTube Downloader CLI built with Python and yt-dlp.  
> Download videos, audio, and full playlists — all from the terminal.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎬 Video Download | Download any YouTube video with quality selector |
| 🎵 Audio Only | Extract audio as MP3, M4A, WAV, FLAC, OPUS |
| 📋 Playlist | Download entire playlists (video or audio) |
| 📊 Format Lister | View all available formats/qualities for a URL |
| 🎨 Rich TUI | Coloured progress bars, ASCII art header |
| 🖥️ Interactive | Menu-driven interactive mode (no args needed) |

---

## 📦 Installation & Update

### 1. Install via PyPI (Recommended)

To install the latest version of **The Dracula** globally from PyPI, run:
```bash
pip install dracula-dl
```
> [!NOTE]
> Unlike `npm` which uses `@latest` to install the latest package version, Python's `pip` installs the latest version by default.

### 2. Upgrade to the Latest Version

To upgrade an existing installation to the latest version, run:
```bash
pip install --upgrade dracula-dl
```
> [!NOTE]
> `pip` does not have a separate `upgrade` subcommand; instead, it uses the `--upgrade` (or `-U`) flag to fetch the latest version.

### 3. Install from Source (Local Development)

If you are running or developing from the source repository:
```bash
pip install -r requirements.txt
```

### 2. Install FFmpeg (required for merging video+audio and audio extraction)

**Windows** (via winget):
```powershell
winget install --id=Gyan.FFmpeg -e
```

**Windows** (via Chocolatey):
```powershell
choco install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
```

---

## 🚀 Usage

### Interactive Mode (recommended for beginners)

If you installed via **pip**, just run:
```bash
dracula
```

If you are running directly from the **source code**:
```bash
python dracula.py
```

You'll get a full interactive TUI menu to guide you.

---

### Command Line Mode

#### Download a Video

```bash
# Best quality (default)
python dracula.py video -u "https://youtube.com/watch?v=..."

# Specific quality
python dracula.py video -u "https://youtube.com/watch?v=..." -q 1080p
python dracula.py video -u "https://youtube.com/watch?v=..." -q 720p
python dracula.py video -u "https://youtube.com/watch?v=..." -q 4k

# Specific format ID (from formats command)
python dracula.py video -u "https://youtube.com/watch?v=..." -f 137

# Custom output directory
python dracula.py video -u "https://youtube.com/watch?v=..." -q 1080p -o "C:\Videos"
```

**Quality Options:** `best` | `4k` | `1440p` | `1080p` | `720p` | `480p` | `360p` | `worst`

---

#### Download Audio Only

```bash
# Default: MP3 at 192kbps
python dracula.py audio -u "https://youtube.com/watch?v=..."

# High quality MP3
python dracula.py audio -u "https://youtube.com/watch?v=..." -f mp3 -b 320

# FLAC lossless
python dracula.py audio -u "https://youtube.com/watch?v=..." -f flac

# M4A format
python dracula.py audio -u "https://youtube.com/watch?v=..." -f m4a -b 256
```

**Format Options:** `mp3` | `m4a` | `wav` | `flac` | `opus` | `aac`  
**Bitrate Options:** `128` | `192` | `256` | `320`

---

#### Download a Playlist

```bash
# Full playlist at 720p
python dracula.py playlist -u "https://youtube.com/playlist?list=..."

# Full playlist at 1080p
python dracula.py playlist -u "https://youtube.com/playlist?list=..." -q 1080p

# Playlist as audio only (MP3)
python dracula.py playlist -u "https://youtube.com/playlist?list=..." --audio-only

# Playlist as FLAC audio
python dracula.py playlist -u "https://youtube.com/playlist?list=..." --audio-only -f flac

# Download items 5 through 10 only
python dracula.py playlist -u "https://youtube.com/playlist?list=..." --start 5 --end 10
```

---

#### List Available Formats

```bash
python dracula.py formats -u "https://youtube.com/watch?v=..."
```

This shows a full table of all format IDs, resolutions, codecs, and file sizes.

---

## 📁 Output Location

By default, files are saved to:

```
~/Downloads/Dracula/
```

Playlists are saved in a subfolder named after the playlist:

```
~/Downloads/Dracula/<Playlist Title>/01 - Video Title.mp4
~/Downloads/Dracula/<Playlist Title>/02 - Video Title.mp4
```

Use `-o <path>` to change the output directory for any command.

---

## 🧛 The Dracula Commands Summary

If installed via **pip**:
```bash
dracula                                 # Interactive menu
dracula video    -u URL                 # Download video
dracula audio    -u URL                 # Download audio only
dracula playlist -u URL                 # Download playlist
dracula formats  -u URL                 # List formats
```

If running from the **source code**:
```bash
python dracula.py                       # Interactive menu
python dracula.py video    -u URL       # Download video
python dracula.py audio    -u URL       # Download audio only
python dracula.py playlist -u URL       # Download playlist
python dracula.py formats  -u URL       # List formats
```

---

## ⚙️ Full Option Reference

### `video` command
| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--url` | `-u` | required | YouTube video URL |
| `--quality` | `-q` | `best` | Quality: best/4k/1440p/1080p/720p/480p/360p/worst |
| `--format-id` | `-f` | — | Specific yt-dlp format ID |
| `--output` | `-o` | `~/Downloads/Dracula` | Output directory |

### `audio` command
| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--url` | `-u` | required | YouTube video URL |
| `--format` | `-f` | `mp3` | Audio format: mp3/m4a/wav/flac/opus/aac |
| `--bitrate` | `-b` | `192` | Bitrate in kbps: 128/192/256/320 |
| `--output` | `-o` | `~/Downloads/Dracula` | Output directory |

### `playlist` command
| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--url` | `-u` | required | Playlist URL |
| `--quality` | `-q` | `720p` | Video quality |
| `--audio-only` | — | off | Download audio only |
| `--format` | `-f` | `mp3` | Audio format (with --audio-only) |
| `--start` | — | — | Start at item number |
| `--end` | — | — | End at item number |
| `--output` | `-o` | `~/Downloads/Dracula` | Output directory |

---

## 🔧 Requirements

- Python 3.10+
- [yt-dlp](https://github.com/AJAYMYTH/dracula-dlp)
- [colorama](https://pypi.org/project/colorama/)
- [FFmpeg](https://ffmpeg.org/) *(required for audio extraction and video merging)*

---

## 📜 License

MIT — Free to use, modify, and distribute.

---

*🧛 The Dracula rises on PyPI — and the world shall download in darkness.*

---

> Made with ❤️ by [Ajaymyth](https://github.com/AJAYMYTH)  
> 📧 javaliajayakumar8574@gmail.com

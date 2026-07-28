# 🧛 The Dracula — YouTube Downloader CLI

```
  ██████╗ ██████╗  █████╗  ██████╗██╗   ██╗██╗      █████╗ 
  ██╔══██╗██╔══██╗██╔══██╗██╔════╝██║   ██║██║     ██╔══██╗
  ██║  ██║██████╔╝███████║██║     ██║   ██║██║     ███████║
  ██║  ██║██╔══██╗██╔══██║██║     ██║   ██║██║     ██╔══██║
  ██████╔╝██║  ██║██║  ██║╚██████╗╚██████╔╝███████╗██║  ██║
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
  ╔══════════════════════════════════════════════════════════╗
  ║   🧛 The Dracula  ·  YouTube Downloader CLI  v1.1.2    ║
  ║      Powered by yt-dlp  ·  Rising from the dark...     ║
  ╚══════════════════════════════════════════════════════════╝
```

> A powerful, dark-themed YouTube Downloader CLI built with Python and yt-dlp.  
> Download videos, audio, playlists, and batch URLs — all from the terminal.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎬 Video Download | Download any YouTube video with quality selector (360p to 4K), subtitles, and thumbnails |
| 🎵 Audio Only | Extract audio as MP3, M4A, WAV, FLAC, OPUS with configurable bitrates (128-320kbps) |
| 📋 Playlist | Download entire playlists with item range selection and failed item retry (`--retry-failed`) |
| 📦 Batch Downloads | Sequential download from text files (`urls.txt`) or multiple `-u` flags |
| ⚙️ Persistent Config | Custom default directory, quality, and bitrates saved in `~/.config/dracula/config.toml` |
| 📜 History Logging | Append-only download history log in `~/.config/dracula/history.jsonl` |
| 📊 Format Lister | View all available formats, resolutions, codecs, and file sizes for a URL |
| 🎨 Rich TUI & CLI | Menu-driven TUI, live progress bars, summary tables, red error panels, and shell completion |

---

## 📦 Installation & Update

### 1. Install via PyPI (Recommended)

To install the latest version of **The Dracula** globally from PyPI, run:
```bash
pip install dracula-dl
```

### 2. Upgrade to the Latest Version

To upgrade an existing installation to the latest version:
```bash
pip install --upgrade dracula-dl
```

### 3. Install from Source (Local Development)

If you are running or developing from the source repository:
```bash
git clone https://github.com/AJAYMYTH/dracula-dl.git
cd dracula-dl
pip install -r requirements.txt
```

### 4. Install FFmpeg (required for merging video+audio and audio extraction)

**Windows** (via winget):
```powershell
winget install --id=Gyan.FFmpeg -e
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
dracula video -u "https://youtube.com/watch?v=..."

# Specific quality with subtitles and thumbnail
dracula video -u "URL" -q 1080p --subs en --embed-thumbnail

# Embed subtitles into MP4 container
dracula video -u "URL" -q 4k --embed-subs --subs en,es

# Speed limit and dry-run simulation
dracula video -u "URL" --limit-rate 2M --dry-run
```

**Quality Options:** `best` | `4k` | `1440p` | `1080p` | `720p` | `480p` | `360p` | `worst`

---

#### Download Audio Only

```bash
# Default: MP3 at 192kbps
dracula audio -u "https://youtube.com/watch?v=..."

# High quality MP3 with embedded album art
dracula audio -u "URL" -f mp3 -b 320 --embed-thumbnail

# FLAC lossless
dracula audio -u "URL" -f flac
```

**Format Options:** `mp3` | `m4a` | `wav` | `flac` | `opus` | `aac`  
**Bitrate Options:** `128` | `192` | `256` | `320`

---

#### Download a Playlist

```bash
# Full playlist at 720p
dracula playlist -u "https://youtube.com/playlist?list=..."

# Playlist as audio only (MP3)
dracula playlist -u "URL" --audio-only -f mp3 -b 320

# Download items 5 through 10 only
dracula playlist -u "URL" --start 5 --end 10

# Retry only previously failed items in history
dracula playlist -u "URL" --retry-failed
```

---

#### Batch Download

```bash
# Batch download from text file (urls.txt)
dracula batch -i urls.txt -q 1080p

# Batch download multiple URLs directly
dracula batch -u "URL1" -u "URL2" -q 720p
```

---

#### View Download History & Setup Shell Completion

```bash
# View 50 recent download records
dracula history -n 50

# Display bash/zsh shell completion setup
dracula completion
```

---

## 📁 Output Location & Configuration

By default, files are saved to:
```
~/Downloads/Dracula/
```

Playlists are saved in a subfolder named after the playlist:
```
~/Downloads/Dracula/<Playlist Title>/01 - Video Title.mp4
```

Persistent configuration is saved to:
```
~/.config/dracula/config.toml
```

Append-only download logs are saved to:
```
~/.config/dracula/history.jsonl
```

---

## 🔧 Requirements

- Python 3.10+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [colorama](https://pypi.org/project/colorama/)
- [rich](https://pypi.org/project/rich/)
- [FFmpeg](https://ffmpeg.org/) *(required for audio extraction and video merging)*

---

## 📜 License

MIT — Free to use, modify, and distribute.

---

> Made with ❤️ by [Ajaymyth](https://github.com/AJAYMYTH)

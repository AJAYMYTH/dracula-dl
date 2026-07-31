#!/usr/bin/env python3
"""
tui.py — Rich TUI for The Dracula YouTube Downloader
Arrow-key menus · Live progress panels · Styled input forms · History & Config screens
"""

import os
import sys
import time
import threading
from pathlib import Path

import questionary
from questionary import Style as QStyle
from rich import box
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn, DownloadColumn, Progress, SpinnerColumn,
    TaskProgressColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn
)
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule
from rich.padding import Padding

# Import Config & History modules
try:
    from dracula_dl.config import load_config, save_config, DEFAULT_CONFIG
    from dracula_dl.history import add_history_entry, read_history, log_debug
except ImportError:
    try:
        from config import load_config, save_config, DEFAULT_CONFIG
        from history import add_history_entry, read_history, log_debug
    except ImportError:
        def load_config(): return {}
        def save_config(cfg): return False
        DEFAULT_CONFIG = {"output_dir": str(Path.home() / "Downloads" / "Dracula")}
        def add_history_entry(*args, **kwargs): pass
        def read_history(limit=50): return [], 0
        def log_debug(msg, exception=None): pass

try:
    from dracula_dl import __version__
except ImportError:
    __version__ = "1.1.2"

console = Console(force_terminal=True, highlight=False)

# ─────────────────────────────────────────────────────────────
#  THEME — Dracula colour palette
# ─────────────────────────────────────────────────────────────

DRACULA_STYLE = QStyle([
    ("qmark",        "fg:#ff5555 bold"),
    ("question",     "fg:#f8f8f2 bold"),
    ("answer",       "fg:#50fa7b bold"),
    ("pointer",      "fg:#ff5555 bold"),
    ("highlighted",  "fg:#ff5555 bold"),
    ("selected",     "fg:#50fa7b"),
    ("separator",    "fg:#6272a4"),
    ("instruction",  "fg:#6272a4 italic"),
    ("text",         "fg:#f8f8f2"),
    ("disabled",     "fg:#6272a4 italic"),
])

C_RED    = "bold red"
C_PINK   = "bold magenta"
C_GREEN  = "bold green"
C_CYAN   = "bold cyan"
C_YELLOW = "bold yellow"
C_WHITE  = "bold white"
C_DIM    = "dim white"
C_PURPLE = "bold purple"

# ─────────────────────────────────────────────────────────────
#  ASCII LOGO
# ─────────────────────────────────────────────────────────────

LOGO_LINES = [
    "  ██████╗ ██████╗  █████╗  ██████╗██╗   ██╗██╗      █████╗ ",
    "  ██╔══██╗██╔══██╗██╔══██╗██╔════╝██║   ██║██║     ██╔══██╗",
    "  ██║  ██║██████╔╝███████║██║     ██║   ██║██║     ███████║",
    "  ██║  ██║██╔══██╗██╔══██║██║     ██║   ██║██║     ██╔══██║",
    "  ██████╔╝██║  ██║██║  ██║╚██████╗╚██████╔╝███████╗██║  ██║",
    "  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝",
]

TAGLINE = f"🧛  The Dark Lord of Downloaders  ·  v{__version__}  ·  Powered by yt-dlp"


def render_logo() -> Panel:
    logo_text = Text()
    colors = ["red", "bright_red", "red1", "dark_red", "red", "bright_red"]
    for i, line in enumerate(LOGO_LINES):
        logo_text.append(line + "\n", style=f"bold {colors[i % len(colors)]}")

    logo_text.append("\n")
    logo_text.append_text(Text(TAGLINE, style="bold magenta", justify="center"))

    return Panel(
        Align.center(logo_text),
        border_style="red",
        box=box.DOUBLE_EDGE,
        padding=(0, 2),
    )


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header():
    clear()
    console.print(render_logo())
    console.print()


def section_panel(title: str, subtitle: str = "") -> Panel:
    t = Text(title, style=C_RED, justify="center")
    if subtitle:
        t.append(f"\n{subtitle}", style=C_DIM)
    return Panel(t, border_style="dim red", box=box.ROUNDED, padding=(0, 4))


def info(msg):  console.print(f"  [cyan]ℹ[/cyan]  {msg}")
def ok(msg):    console.print(f"  [bold green]✔[/bold green]  {msg}")
def warn(msg):  console.print(f"  [yellow]⚠[/yellow]  {msg}")
def err(msg):   console.print(f"  [bold red]✘[/bold red]  {msg}")
def sep():      console.print(Rule(style="dim red"))


def ask(message: str, default: str = "") -> str:
    suffix = f" ({default})" if default else ""
    val = questionary.text(
        f"{message}{suffix} ›",
        style=DRACULA_STYLE,
        qmark="🧛 ",
    ).ask()
    if val is None:
        raise KeyboardInterrupt
    return val.strip() if val.strip() else default


def ask_select(message: str, choices: list, default: str = None) -> str:
    print()
    kwargs = {
        "message": message,
        "choices": choices,
        "style": DRACULA_STYLE,
        "use_indicator": True,
        "qmark": "🧛 ",
        "instruction": " (↑↓ navigate, Enter select)",
    }
    if default and default in choices:
        kwargs["default"] = default
    ans = questionary.select(**kwargs).ask()
    if ans is None:
        raise KeyboardInterrupt
    return ans


def ask_confirm(message: str, default: bool = False) -> bool:
    ans = questionary.confirm(
        message,
        default=default,
        style=DRACULA_STYLE,
        qmark="🧛 ",
    ).ask()
    if ans is None:
        raise KeyboardInterrupt
    return ans


def get_default_dir() -> str:
    cfg = load_config()
    p_str = cfg.get("output_dir") or str(Path.home() / "Downloads" / "Dracula")
    p = Path(p_str)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def cleanup_leftovers(output_dir: str):
    if not output_dir:
        return
    try:
        if "%(" in output_dir or any(ext in output_dir for ext in ['.mp4', '.mp3', '.mkv', '.m4a', '.wav', '.flac', '.opus', '.aac']):
            output_dir = os.path.dirname(output_dir)
            if "%(" in output_dir:
                output_dir = output_dir.split("%(")[0]
                output_dir = os.path.dirname(output_dir)

        output_dir = os.path.abspath(output_dir)
        if not os.path.isdir(output_dir):
            return

        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.part') or file.endswith('.ytdl'):
                    file_path = os.path.join(root, file)
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        log_debug(f"Cleanup error removing {file_path}", e)
    except Exception as e:
        log_debug("Cleanup leftovers top-level error", e)


# ─────────────────────────────────────────────────────────────
#  RICH PROGRESS DOWNLOAD
# ─────────────────────────────────────────────────────────────

_progress_ref   = None
_task_id_ref    = None
_dl_lock        = threading.Lock()


def _make_progress() -> Progress:
    return Progress(
        SpinnerColumn(spinner_name="dots", style="bold red"),
        TextColumn("[bold red]{task.description}"),
        BarColumn(bar_width=38, style="red", complete_style="bright_red", finished_style="bold green"),
        TaskProgressColumn(style="bold yellow"),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        DownloadColumn(),
        console=console,
        expand=True,
    )


def _yt_hook(d):
    global _progress_ref, _task_id_ref

    if _progress_ref is None or _task_id_ref is None:
        return

    status = d.get("status", "")

    if status == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        current = d.get("downloaded_bytes", 0)

        with _dl_lock:
            if total > 0:
                _progress_ref.update(_task_id_ref, completed=current, total=total)
            else:
                _progress_ref.update(_task_id_ref, advance=0)

    elif status == "finished":
        fname = Path(d.get("filename", "")).name
        with _dl_lock:
            _progress_ref.update(
                _task_id_ref,
                completed=_progress_ref.tasks[_task_id_ref].total or 100,
                description=f"[green]✔ {fname[:40]}",
            )


def _do_download(ydl_opts: dict, urls: list, title: str, category: str = "video", quality_meta: str = "default") -> dict:
    global _progress_ref, _task_id_ref

    try:
        import yt_dlp
    except ImportError:
        err("yt-dlp not available")
        return {'status': 'failed'}

    prog = _make_progress()
    task = prog.add_task(f"[red]{title[:45]}", total=None)

    _progress_ref = prog
    _task_id_ref  = task

    ydl_opts["progress_hooks"] = [_yt_hook]
    ydl_opts.setdefault("quiet", True)
    ydl_opts.setdefault("no_warnings", True)
    ydl_opts["noprogress"] = True
    ydl_opts["no_color"] = True
    ydl_opts.setdefault("retries", 10)
    ydl_opts.setdefault("fragment_retries", 10)
    ydl_opts.setdefault("file_access_retries", 5)
    ydl_opts.setdefault("socket_timeout", 30)
    ydl_opts.setdefault("http_chunk_size", 10 * 1024 * 1024)
    ydl_opts.setdefault("continuedl", True)

    console.print()
    sep()
    console.print(Panel(f"[bold red]⬇  Downloading:[/bold red] [white]{title}[/white]", border_style="red", box=box.ROUNDED))

    download_error = None
    with Live(prog, console=console, refresh_per_second=8, transient=False):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(urls)
        except Exception as e:
            download_error = str(e)
            log_debug(f"TUI download error for {urls}", e)
        finally:
            cleanup_leftovers(ydl_opts.get("outtmpl", ""))

    _progress_ref = None
    _task_id_ref  = None

    outtmpl_val = ydl_opts.get("outtmpl", "")
    if isinstance(outtmpl_val, dict):
        outtmpl_val = outtmpl_val.get("default", "")
    save_dir = str(outtmpl_val).replace("%(title)s.%(ext)s", "").rstrip(os.sep)

    if download_error:
        sep()
        panel_content = f"[bold white]{download_error}[/bold white]\n\n[dim cyan]💡 Hint: Check the URL, your internet connection, or try inspecting formats.[/dim cyan]"
        console.print(Panel(panel_content, title="[bold red]🧛 Download Failed[/bold red]", border_style="red", box=box.ROUNDED))
        console.print()
        add_history_entry(title, urls[0] if urls else "", category, quality_meta, save_dir, status="failed", error=download_error)
        return {'title': title, 'format': quality_meta, 'size': 'Unknown', 'status': 'failed'}

    sep()
    console.print(
        Panel(
            "[bold green]✔  Download complete![/bold green]\n"
            f"[dim]Saved to:[/dim] [cyan]{save_dir}[/cyan]",
            border_style="green", box=box.ROUNDED
        )
    )
    console.print()
    add_history_entry(title, urls[0] if urls else "", category, quality_meta, save_dir, status="success")
    return {'title': title, 'format': quality_meta, 'size': 'Done', 'status': 'success'}


def _quality_fmt(quality: str) -> str:
    q = (quality or "").lower()
    if "4k" in q or "2160" in q:
        return "bestvideo[height<=2160]+bestaudio/best"
    elif "1440" in q:
        return "bestvideo[height<=1440]+bestaudio/best"
    elif "1080" in q:
        return "bestvideo[height<=1080]+bestaudio/best"
    elif "720" in q:
        return "bestvideo[height<=720]+bestaudio/best"
    elif "480" in q:
        return "bestvideo[height<=480]+bestaudio/best"
    elif "360" in q:
        return "bestvideo[height<=360]+bestaudio/best"
    elif "worst" in q:
        return "worstvideo+worstaudio/worst"
    return "bestvideo+bestaudio/best"


# ─────────────────────────────────────────────────────────────
#  SCREEN: VIDEO DOWNLOAD
# ─────────────────────────────────────────────────────────────

def screen_video():
    header()
    console.print(section_panel("🎬  Download Video", "Single YouTube video with quality control"))
    console.print()

    url = ask("Paste YouTube URL")
    if not url:
        warn("No URL entered."); _back_prompt(); return

    cfg = load_config()
    quality = ask_select("Select video quality:", [
        "Best available",
        "4K  (2160p)",
        "1440p",
        "1080p FullHD",
        "720p  HD",
        "480p",
        "360p",
        "Worst (smallest)",
    ])

    out_dir = ask("Output folder", get_default_dir())
    embed_thumb = ask_confirm("Embed thumbnail?", default=False)
    sub_choice = ask_confirm("Download subtitles?", default=False)
    subs_lang = None
    use_auto_subs = False
    embed_subs = False
    if sub_choice:
        subs_lang = ask("Subtitle language codes (comma separated, e.g. en,es)", default="en")
        use_auto_subs = ask_confirm("Include auto-generated subtitles?", default=True)
        embed_subs = ask_confirm("Embed subtitles into video?", default=True)

    info("Fetching video info…")
    title = _get_title(url)

    opts = {
        "format": _quality_fmt(quality),
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "merge_output_format": "mp4",
    }
    if embed_thumb:
        opts["writethumbnail"] = True
        opts.setdefault("postprocessors", []).append({'key': 'EmbedThumbnail'})
    if subs_lang:
        opts["writesubtitles"] = True
        opts["subtitleslangs"] = [s.strip() for s in subs_lang.split(',') if s.strip()]
        opts["subtitlesformat"] = "srt/ass/best"
        if use_auto_subs:
            opts["writeautomaticsub"] = True
        if embed_subs:
            # Convert subs to srt first, then embed — order matters
            opts.setdefault("postprocessors", []).append({
                'key': 'FFmpegSubtitlesConvertor',
                'format': 'srt',
            })
            opts["postprocessors"].append({'key': 'FFmpegEmbedSubtitle'})

    _do_download(opts, [url], title or url, category="video", quality_meta=quality)
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: AUDIO DOWNLOAD
# ─────────────────────────────────────────────────────────────

def screen_audio():
    header()
    console.print(section_panel("🎵  Download Audio Only", "Extract audio in MP3 / FLAC / WAV / M4A / OPUS"))
    console.print()

    url = ask("Paste YouTube URL")
    if not url:
        warn("No URL entered."); _back_prompt(); return

    cfg = load_config()
    fmt = ask_select("Select audio format:", [
        "mp3   (Most compatible)",
        "m4a   (AAC audio)",
        "flac  (Lossless)",
        "wav   (Uncompressed)",
        "opus  (Best efficiency)",
    ]).split()[0]

    bitrate = ask_select("Select audio bitrate:", [
        "320  (Highest quality)",
        "256  (High quality)",
        "192  (Standard default)",
        "128  (Compact file size)",
    ]).split()[0]

    out_dir = ask("Output folder", get_default_dir())
    embed_thumb = ask_confirm("Embed thumbnail as cover art?", default=True)

    info("Fetching track info…")
    title = _get_title(url)

    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": fmt,
            "preferredquality": bitrate,
        }],
    }
    if embed_thumb:
        opts["writethumbnail"] = True
        opts.setdefault("postprocessors", []).append({'key': 'EmbedThumbnail'})

    _do_download(opts, [url], title or url, category=f"audio ({fmt})", quality_meta=f"{bitrate}k")
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: PLAYLIST DOWNLOAD
# ─────────────────────────────────────────────────────────────

def screen_playlist():
    header()
    console.print(section_panel("📋  Download Playlist", "Download full YouTube playlists sequentially"))
    console.print()

    url = ask("Paste Playlist URL")
    if not url:
        warn("No URL entered."); _back_prompt(); return

    mode = ask_select("Download mode:", [
        "Video (Full videos)",
        "Audio only (Extract MP3/M4A)",
    ])
    audio_only = "Audio" in mode

    out_dir = ask("Output folder", get_default_dir())

    cfg = load_config()
    quality = cfg.get("default_quality", "720p")
    audio_fmt = cfg.get("default_audio_format", "mp3")
    audio_bitrate = cfg.get("default_audio_bitrate", "192")

    if audio_only:
        audio_fmt = ask_select("Audio format:", ["mp3", "m4a", "flac", "wav", "opus"])
        audio_bitrate = ask_select("Audio bitrate:", ["320", "256", "192", "128"])
    else:
        quality = ask_select("Video quality:", ["Best available", "1080p FullHD", "720p  HD", "480p", "Worst"])

    embed_thumb = ask_confirm("Embed thumbnail?", default=False)

    start_idx = ask("Start item index (press enter for 1)", default="1")
    end_idx = ask("End item index (press enter for all)", default="")

    info("Fetching playlist info…")
    pl_title = _get_playlist_title(url)

    outtmpl = os.path.join(out_dir, "%(playlist_title)s", "%(playlist_index)s - %(title)s.%(ext)s")

    opts = {
        "outtmpl": outtmpl,
        "ignoreerrors": True,
    }

    if start_idx.isdigit():
        opts["playliststart"] = int(start_idx)
    if end_idx.isdigit():
        opts["playlistend"] = int(end_idx)

    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_fmt,
            "preferredquality": audio_bitrate,
        }]
    else:
        opts["format"] = _quality_fmt(quality)
        opts["merge_output_format"] = "mp4"

    if embed_thumb:
        opts["writethumbnail"] = True
        opts.setdefault("postprocessors", []).append({'key': 'EmbedThumbnail'})

    _do_download(opts, [url], f"Playlist: {pl_title}", category="playlist", quality_meta=audio_bitrate if audio_only else quality)
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: BATCH DOWNLOAD
# ─────────────────────────────────────────────────────────────

def screen_batch():
    header()
    console.print(section_panel("📦  Batch Download", "Download multiple URLs from text file or manual list"))
    console.print()

    input_mode = ask_select("Choose batch input method:", [
        "1. Load from text file (urls.txt)",
        "2. Enter URLs manually",
    ])

    url_list = []
    if "text file" in input_mode:
        file_path = ask("Path to URLs file", default="urls.txt")
        p = Path(file_path)
        if not p.exists():
            err(f"File not found: {file_path}")
            _back_prompt()
            return
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    url_list.append(line)
    else:
        raw_urls = ask("Enter URLs separated by space or comma")
        url_list = [u.strip() for u in raw_urls.replace(',', ' ').split() if u.strip()]

    if not url_list:
        warn("No URLs provided.")
        _back_prompt()
        return

    out_dir = ask("Output folder", get_default_dir())
    mode = ask_select("Download mode:", ["Video", "Audio only"])
    audio_only = mode == "Audio only"
    embed_thumb = ask_confirm("Embed thumbnail?", default=False)

    summary_items = []
    total = len(url_list)

    for idx, target_url in enumerate(url_list, 1):
        console.print(f"\n  [bold magenta][{idx}/{total}][/bold magenta] [cyan]{target_url}[/cyan]")
        title = _get_title(target_url) or target_url
        if audio_only:
            opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
                "postprocessors": [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            }
        else:
            opts = {
                "format": "bestvideo+bestaudio/best",
                "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
                "merge_output_format": "mp4",
            }
        if embed_thumb:
            opts["writethumbnail"] = True
            opts.setdefault("postprocessors", []).append({'key': 'EmbedThumbnail'})

        res = _do_download(opts, [target_url], title, category="batch", quality_meta="default")
        summary_items.append(res)

    # Display summary table
    table = Table(title="Batch Download Summary", box=box.ROUNDED, border_style="magenta", header_style="bold magenta")
    table.add_column("#", style="dim")
    table.add_column("Title", style="bold white")
    table.add_column("Status", style="bold")
    for i, item in enumerate(summary_items, 1):
        st = "[green]✔ Done[/green]" if item.get('status') == 'success' else "[red]✘ Failed[/red]"
        table.add_row(str(i), item.get('title', 'Unknown')[:40], st)
    console.print()
    console.print(table)
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: DOWNLOAD HISTORY
# ─────────────────────────────────────────────────────────────

def screen_history():
    header()
    console.print(section_panel("📜  Recent Download History", "Log of recent video and audio downloads"))
    console.print()

    entries, total = read_history(limit=50)
    if not entries:
        info("No download history recorded yet.")
        _back_prompt()
        return

    table = Table(title=f"Recent Downloads ({len(entries)} shown / {total} total)", box=box.ROUNDED, border_style="magenta", header_style="bold magenta")
    table.add_column("Timestamp", style="dim", justify="left")
    table.add_column("Title", style="bold white")
    table.add_column("Format / Quality", style="cyan")
    table.add_column("Status", style="bold")

    for e in entries:
        st = "[green]✔ Success[/green]" if e.get('status') == 'success' else f"[red]✘ {e.get('status')}[/red]"
        table.add_row(
            e.get('timestamp', 'N/A'),
            e.get('title', 'Unknown')[:40],
            f"{e.get('format','')} ({e.get('quality_or_bitrate','')})",
            st
        )

    console.print(table)
    if total > len(entries):
        info(f"Log contains {total - len(entries)} older entries in ~/.config/dracula/history.jsonl")
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: CONFIG SETTINGS
# ─────────────────────────────────────────────────────────────

def screen_config():
    header()
    console.print(section_panel("⚙  Configuration Settings", "View and edit ~/.config/dracula/config.toml defaults"))
    console.print()

    cfg = load_config()

    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="bold cyan", no_wrap=True)
    grid.add_column(style="bold white")

    grid.add_row("Output Directory", cfg.get("output_dir", "default"))
    grid.add_row("Default Quality", cfg.get("default_quality", "720p"))
    grid.add_row("Default Audio Format", cfg.get("default_audio_format", "mp3"))
    grid.add_row("Default Audio Bitrate", cfg.get("default_audio_bitrate", "192"))

    console.print(Panel(grid, title="[bold red]Current Config[/bold red]", border_style="red", box=box.ROUNDED, padding=(1, 4)))
    console.print()

    if ask_confirm("Would you like to edit config settings?", default=False):
        new_dir = ask("Default Output Directory", cfg.get("output_dir", str(Path.home() / "Downloads" / "Dracula")))
        new_q = ask_select("Default Video Quality:", ["720p", "1080p", "4k", "best", "360p"], default=cfg.get("default_quality", "720p"))
        new_af = ask_select("Default Audio Format:", ["mp3", "m4a", "flac", "wav", "opus"], default=cfg.get("default_audio_format", "mp3"))
        new_ab = ask_select("Default Audio Bitrate (kbps):", ["192", "320", "256", "128"], default=cfg.get("default_audio_bitrate", "192"))

        updated = {
            "output_dir": new_dir,
            "default_quality": new_q,
            "default_audio_format": new_af,
            "default_audio_bitrate": new_ab,
        }
        if save_config(updated):
            ok("Configuration saved successfully!")
        else:
            err("Failed to save configuration file.")

    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: LIST FORMATS
# ─────────────────────────────────────────────────────────────

def screen_formats():
    header()
    console.print(section_panel("📊  Inspect Available Formats", "Browse raw video & audio streams from yt-dlp"))
    console.print()

    url = ask("Paste YouTube URL")
    if not url:
        warn("No URL entered."); _back_prompt(); return

    info("Fetching format manifest…")

    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as e:
        log_debug(f"Formats screen error for {url}", e)
        err(f"Could not fetch info: {e}")
        _back_prompt()
        return

    formats = data.get("formats", [])
    if not formats:
        warn("No format information found."); _back_prompt(); return

    title = data.get("title", "Unknown Video")
    views = data.get("view_count")
    views_str = f"{views:,}" if isinstance(views, int) else "N/A"

    console.print()
    console.print(f"  [bold white]Title:[/bold white]    [cyan]{title}[/cyan]")
    console.print(f"  [bold white]Channel:[/bold white]  {data.get('uploader','N/A')}")
    console.print(f"  [bold white]Views:[/bold white]    {views_str}")
    console.print()

    table = Table(box=box.ROUNDED, border_style="red", header_style="bold magenta", expand=True)
    table.add_column("ID",         style="bold red",  no_wrap=True)
    table.add_column("EXT",        style="cyan",      no_wrap=True)
    table.add_column("RESOLUTION", style="bold white")
    table.add_column("FPS",        style="yellow")
    table.add_column("VCODEC",     style="dim white")
    table.add_column("ACODEC",     style="dim white")
    table.add_column("SIZE",       style="green",     justify="right")

    for f in formats:
        fid  = str(f.get("format_id", ""))
        ext  = str(f.get("ext", ""))
        res  = f.get("resolution") or (f"{f.get('width','?')}x{f.get('height','?')}" if f.get("width") else "audio only")
        fps  = str(f.get("fps", "")) if f.get("fps") else ""
        vco  = str(f.get("vcodec", "none"))[:18]
        aco  = str(f.get("acodec", "none"))[:16]
        size = f.get("filesize") or f.get("filesize_approx")
        sz_str = f"{size/1024/1024:.1f} MB" if size else "?"

        if vco == "none":
            v_style = "[yellow]" + res + "[/yellow]"
        elif aco == "none":
            v_style = "[cyan]" + res + "[/cyan]"
        else:
            v_style = "[white]" + res + "[/white]"

        table.add_row(fid, ext, v_style, fps, vco, aco, sz_str)

    console.print(table)
    console.print()
    console.print("  [cyan]Cyan[/cyan] = Video-only  [yellow]Yellow[/yellow] = Audio-only  [white]White[/white] = Combined (video+audio)")
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: ABOUT
# ─────────────────────────────────────────────────────────────

def screen_about():
    header()

    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="bold red", no_wrap=True)
    grid.add_column(style="bold white")

    try:
        import yt_dlp.version as yv
        ytdlp_ver = getattr(yv, "__version__", "unknown")
    except Exception:
        ytdlp_ver = "unknown"

    import platform, shutil
    ffmpeg_v = "Not found"
    if shutil.which("ffmpeg"):
        try:
            import subprocess
            out = subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT, text=True)
            ffmpeg_v = out.splitlines()[0].split("version")[1].split()[0]
        except Exception:
            ffmpeg_v = "Found"

    grid.add_row("Tool", "🧛 The Dracula YouTube Downloader")
    grid.add_row("Version", __version__)
    grid.add_row("yt-dlp", ytdlp_ver)
    grid.add_row("FFmpeg", ffmpeg_v)
    grid.add_row("Python", platform.python_version())
    grid.add_row("OS", platform.system() + " " + platform.release())
    grid.add_row("Default Dir", get_default_dir())

    console.print(Panel(grid, title="[bold red]About The Dracula[/bold red]", border_style="red", box=box.DOUBLE_EDGE, padding=(1, 4)))
    console.print()
    console.print(Padding("[dim]The Dracula rises from the dark to download your videos.\nMIT License · Free to use, modify, distribute.[/dim]", (0, 4)))
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  HELPERS & TITLE FETCHERS
# ─────────────────────────────────────────────────────────────

def _get_title(url: str) -> str:
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            data = ydl.extract_info(url, download=False)
            return data.get("title", "")
    except Exception:
        return ""


def _get_playlist_title(url: str) -> str:
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": True}) as ydl:
            data = ydl.extract_info(url, download=False)
            return data.get("title", data.get("playlist_title", "Playlist"))
    except Exception:
        return "Playlist"


def _back_prompt():
    console.print()
    questionary.press_any_key_to_continue(
        "  Press any key to return to main menu…",
        style=DRACULA_STYLE,
    ).ask()


# ─────────────────────────────────────────────────────────────
#  MAIN MENU
# ─────────────────────────────────────────────────────────────

MENU_CHOICES = [
    questionary.Choice("  🎬   Download Video           Single video with quality selector", "video"),
    questionary.Choice("  🎵   Download Audio Only       MP3 / FLAC / WAV / M4A / OPUS", "audio"),
    questionary.Choice("  📋   Download Playlist         Full playlist — video or audio", "playlist"),
    questionary.Choice("  📦   Batch Download            Download multiple URLs from file/list", "batch"),
    questionary.Choice("  📜   Download History          View recent download log", "history"),
    questionary.Choice("  📊   List Formats              Browse all available formats", "formats"),
    questionary.Choice("  ⚙   Config / Settings         Edit default options & output folder", "config"),
    questionary.Choice("  ℹ    About / System Info", "about"),
    questionary.Separator("  ─────────────────────────────"),
    questionary.Choice("  ✖    Exit", "exit"),
]


def launch_tui():
    """Entry point — launches the full TUI main loop."""
    while True:
        header()

        import shutil
        ffmpeg_ok = bool(shutil.which("ffmpeg"))
        status_items = [
            "[bold green]● FFmpeg[/bold green]" if ffmpeg_ok else "[bold red]○ FFmpeg missing[/bold red]",
            "[bold green]● yt-dlp[/bold green]",
            f"[dim]{get_default_dir()}[/dim]",
        ]
        status_row = "    ".join(status_items)
        console.print(Panel(status_row, border_style="dim red", box=box.ROUNDED, padding=(0, 2)))
        console.print()

        choice = questionary.select(
            "  What do you want to do?",
            choices=MENU_CHOICES,
            style=DRACULA_STYLE,
            use_indicator=True,
            qmark="",
            instruction=" (↑↓ to move  Enter to select)",
        ).ask()

        if choice is None or choice == "exit":
            clear()
            console.print(
                Panel(
                    Align.center(
                        Text("🧛  The Dracula sleeps…\nUntil darkness falls again.", style="bold red", justify="center")
                    ),
                    border_style="red", box=box.DOUBLE_EDGE, padding=(1, 6)
                )
            )
            console.print()
            sys.exit(0)

        elif choice == "video":
            screen_video()
        elif choice == "audio":
            screen_audio()
        elif choice == "playlist":
            screen_playlist()
        elif choice == "batch":
            screen_batch()
        elif choice == "history":
            screen_history()
        elif choice == "formats":
            screen_formats()
        elif choice == "config":
            screen_config()
        elif choice == "about":
            screen_about()


def run_tui():
    launch_tui()


if __name__ == "__main__":
    launch_tui()

#!/usr/bin/env python3
"""
tui.py — Rich TUI for The Dracula YouTube Downloader
Arrow-key menus · Live progress panels · Styled input forms
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
from rich.progress import (BarColumn, DownloadColumn, Progress,
                           SpinnerColumn, TaskProgressColumn,
                           TextColumn, TimeRemainingColumn,
                           TransferSpeedColumn)
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule
from rich.padding import Padding

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

TAGLINE = "🧛  The Dark Lord of Downloaders  ·  v1.0.4  ·  Powered by yt-dlp"


def render_logo() -> Panel:
    logo_text = Text()
    colors = ["red", "bright_red", "red1", "dark_red", "red", "bright_red"]
    for i, line in enumerate(LOGO_LINES):
        logo_text.append(line + "\n", style=f"bold {colors[i % len(colors)]}")

    tag = Text(TAGLINE, style="bold magenta", justify="center")
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


def ask_select(message: str, choices: list) -> str:
    print()
    ans = questionary.select(
        message,
        choices=choices,
        style=DRACULA_STYLE,
        use_indicator=True,
        qmark="🧛 ",
        instruction=" (↑↓ navigate, Enter select)",
    ).ask()
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
    p = Path.home() / "Downloads" / "Dracula"
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def cleanup_leftovers(output_dir: str):
    """Scan the output directory and remove any leftover .part or .ytdl files."""
    if not output_dir:
        return
    try:
        # If output_dir is actually a file template (like from outtmpl)
        if "%(" in output_dir or any(ext in output_dir for ext in ['.mp4', '.mp3', '.mkv', '.m4a', '.wav', '.flac', '.opus', '.aac']):
            # It's a template or file path. Let's get the directory
            output_dir = os.path.dirname(output_dir)
            if "%(" in output_dir:
                # If there's a format placeholder in directory path, split it
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
                    except Exception:
                        pass
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
#  RICH PROGRESS DOWNLOAD
# ─────────────────────────────────────────────────────────────

_progress_ref   = None
_task_id_ref    = None
_live_ref       = None
_dl_lock        = threading.Lock()


def _make_progress() -> Progress:
    return Progress(
        SpinnerColumn(spinner_name="dots", style="bold red"),
        TextColumn("[bold red]{task.description}"),
        BarColumn(bar_width=38, style="red", complete_style="bright_red",
                  finished_style="bold green"),
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
        total   = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        current = d.get("downloaded_bytes", 0)

        try:
            pct_str = d.get("_percent_str", "0%").strip().replace("%", "")
            pct     = float(pct_str)
        except Exception:
            pct = 0.0

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


# ─────────────────────────────────────────────────────────────
#  CORE DOWNLOAD WRAPPERS (call yt_dlp directly)
# ─────────────────────────────────────────────────────────────

def _do_download(ydl_opts: dict, urls: list, title: str):
    global _progress_ref, _task_id_ref

    try:
        import yt_dlp
    except ImportError:
        err("yt-dlp not available"); return

    prog = _make_progress()
    task = prog.add_task(f"[red]{title[:45]}", total=None)

    _progress_ref = prog
    _task_id_ref  = task

    ydl_opts["progress_hooks"] = [_yt_hook]
    ydl_opts.setdefault("quiet", True)
    ydl_opts.setdefault("no_warnings", True)
    ydl_opts["noprogress"]        = True
    ydl_opts["no_color"]          = True
    # ── Resilience against network hiccups ────────────────────
    ydl_opts.setdefault("retries",          10)   # retry full download up to 10×
    ydl_opts.setdefault("fragment_retries", 10)   # retry each fragment up to 10×
    ydl_opts.setdefault("file_access_retries", 5) # retry file ops (Windows locks)
    ydl_opts.setdefault("socket_timeout",   30)   # seconds before a read times out
    ydl_opts.setdefault("http_chunk_size",  10 * 1024 * 1024)  # 10 MB chunks

    console.print()
    sep()
    console.print(
        Panel(f"[bold red]⬇  Downloading:[/bold red] [white]{title}[/white]",
              border_style="red", box=box.ROUNDED)
    )

    download_error = None
    with Live(prog, console=console, refresh_per_second=8, transient=False):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(urls)
        except yt_dlp.utils.DownloadError as e:
            download_error = str(e)
        finally:
            cleanup_leftovers(ydl_opts.get("outtmpl", ""))

    _progress_ref = None
    _task_id_ref  = None

    # Print result AFTER Live context has closed (prevents broken lines)
    if download_error:
        sep()
        err(f"Download error: {download_error}")
        console.print()
        return

    sep()
    console.print(
        Panel(
            "[bold green]✔  Download complete![/bold green]\n"
            f"[dim]Saved to:[/dim] [cyan]{ydl_opts.get('outtmpl','').replace('%(title)s.%(ext)s','').rstrip(os.sep)}[/cyan]",
            border_style="green", box=box.ROUNDED
        )
    )
    console.print()


def _quality_fmt(quality: str) -> str:
    qmap = {
        "4K  (2160p)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
        "1440p"      : "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
        "1080p FullHD": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p  HD"   : "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p"       : "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "360p"       : "bestvideo[height<=360]+bestaudio/best[height<=360]",
        "Best available": "bestvideo+bestaudio/best",
        "Worst (smallest)": "worstvideo+worstaudio/worst",
        # plain keys used by CLI
        "4k"   : "bestvideo[height<=2160]+bestaudio/best",
        "1440p": "bestvideo[height<=1440]+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best",
        "720p" : "bestvideo[height<=720]+bestaudio/best",
        "480p" : "bestvideo[height<=480]+bestaudio/best",
        "360p" : "bestvideo[height<=360]+bestaudio/best",
        "best" : "bestvideo+bestaudio/best",
        "worst": "worstvideo+worstaudio/worst",
    }
    return qmap.get(quality, "bestvideo+bestaudio/best")


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

    # quality selector
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

    # optional custom format id (disabled per user request)
    fmt_id = None

    # fetch title
    info("Fetching video info…")
    title = _get_title(url)

    opts = {
        "format": fmt_id if fmt_id else _quality_fmt(quality),
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "merge_output_format": "mp4",
    }
    _do_download(opts, [url], title or url)
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: AUDIO DOWNLOAD
# ─────────────────────────────────────────────────────────────

def screen_audio():
    header()
    console.print(section_panel("🎵  Download Audio Only", "Extract audio in your preferred format"))
    console.print()

    url = ask("Paste YouTube URL")
    if not url:
        warn("No URL entered."); _back_prompt(); return

    audio_fmt = ask_select("Select audio format:", [
        "mp3  — Universal, compressed",
        "m4a  — Apple / AAC",
        "flac — Lossless",
        "wav  — Uncompressed PCM",
        "opus — Best size/quality ratio",
        "aac  — Raw AAC",
    ])
    fmt_code = audio_fmt.split("—")[0].strip().split()[0]  # 'mp3', 'm4a' etc.

    bitrate = ask_select("Select bitrate (kbps):", [
        "320  — Highest quality",
        "256",
        "192  — Recommended",
        "128  — Smallest file",
    ])
    brate = bitrate.split()[0]

    out_dir = ask("Output folder", get_default_dir())

    info("Fetching video info…")
    title = _get_title(url)

    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": fmt_code,
            "preferredquality": brate,
        }],
    }
    _do_download(opts, [url], title or url)
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: PLAYLIST DOWNLOAD
# ─────────────────────────────────────────────────────────────

def screen_playlist():
    header()
    console.print(section_panel("📋  Download Playlist", "Download full playlists — video or audio"))
    console.print()

    url = ask("Paste YouTube Playlist URL")
    if not url:
        warn("No URL entered."); _back_prompt(); return

    mode = ask_select("Download mode:", [
        "🎬  Video — download as MP4",
        "🎵  Audio only — extract audio",
    ])
    audio_only = mode.startswith("🎵")

    if audio_only:
        audio_fmt = ask_select("Select audio format:", [
            "mp3", "m4a", "flac", "wav", "opus", "aac"
        ])
        quality = "best"
    else:
        quality = ask_select("Select video quality:", [
            "Best available",
            "1080p FullHD",
            "720p  HD",
            "480p",
            "360p",
            "4K  (2160p)",
            "Worst (smallest)",
        ])
        audio_fmt = "mp3"

    console.print()
    info("Playlist item range (leave blank to download all):")
    start_str = ask("Start at item #", "")
    end_str   = ask("End at item #",   "")

    out_dir = ask("Output folder", get_default_dir())

    template = os.path.join(out_dir, "%(playlist_title)s",
                            "%(playlist_index)s - %(title)s.%(ext)s")

    opts: dict = {
        "outtmpl": template,
        "ignoreerrors": True,
    }

    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_fmt,
            "preferredquality": "192",
        }]
    else:
        opts["format"] = _quality_fmt(quality)
        opts["merge_output_format"] = "mp4"

    if start_str.isdigit():
        opts["playliststart"] = int(start_str)
    if end_str.isdigit():
        opts["playlistend"] = int(end_str)

    info("Fetching playlist info…")
    playlist_title = _get_playlist_title(url)

    _do_download(opts, [url], playlist_title or "Playlist")
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: LIST FORMATS
# ─────────────────────────────────────────────────────────────

def screen_formats():
    header()
    console.print(section_panel("📊  Available Formats", "Browse all formats for a video"))
    console.print()

    url = ask("Paste YouTube URL")
    if not url:
        warn("No URL entered."); _back_prompt(); return

    info("Fetching format list…")

    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                                "skip_download": True}) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as e:
        err(f"Could not fetch info: {e}"); _back_prompt(); return

    if not data:
        err("No data returned."); _back_prompt(); return

    console.print()

    # video metadata panel
    meta = Table.grid(padding=(0, 2))
    meta.add_column(style="bold cyan", no_wrap=True)
    meta.add_column(style="white")
    meta.add_row("Title",    data.get("title", "N/A"))
    meta.add_row("Channel",  data.get("uploader", "N/A"))
    meta.add_row("Duration", data.get("duration_string", "N/A"))
    views = data.get("view_count")
    meta.add_row("Views",    f"{views:,}" if isinstance(views, int) else str(views or "N/A"))
    console.print(Panel(meta, title="[bold red]Video Info[/bold red]",
                        border_style="red", box=box.ROUNDED))
    console.print()

    # formats table
    table = Table(
        title="[bold red]Available Formats[/bold red]",
        box=box.SIMPLE_HEAD,
        border_style="dim red",
        header_style="bold red",
        show_lines=False,
        expand=True,
    )
    table.add_column("ID",         style="bold cyan",   no_wrap=True, width=12)
    table.add_column("EXT",        style="bold white",  no_wrap=True, width=6)
    table.add_column("RESOLUTION", style="bold yellow", no_wrap=True, width=14)
    table.add_column("FPS",        style="white",       no_wrap=True, width=5)
    table.add_column("VCODEC",     style="dim white",   width=18)
    table.add_column("ACODEC",     style="dim white",   width=16)
    table.add_column("SIZE",       style="green",       no_wrap=True, width=10, justify="right")

    for f in data.get("formats", []):
        fid  = str(f.get("format_id", ""))
        ext  = str(f.get("ext", ""))
        res  = f.get("resolution") or (
            f"{f.get('width','?')}x{f.get('height','?')}" if f.get("width") else "audio only"
        )
        fps  = str(f.get("fps", "")) if f.get("fps") else ""
        vco  = str(f.get("vcodec", "none"))
        aco  = str(f.get("acodec", "none"))
        fs   = f.get("filesize") or f.get("filesize_approx")
        size = f"{fs/1024/1024:.1f} MB" if fs else "?"

        if vco == "none":
            row_style = "yellow"
        elif aco == "none":
            row_style = "cyan"
        else:
            row_style = "white"

        table.add_row(fid, ext, str(res), fps, vco[:17], aco[:15], size,
                      style=row_style)

    console.print(table)
    console.print()
    console.print(
        "  [cyan]Cyan[/cyan] = Video-only  "
        "[yellow]Yellow[/yellow] = Audio-only  "
        "[white]White[/white] = Combined (video+audio)"
    )
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  SCREEN: SETTINGS / ABOUT
# ─────────────────────────────────────────────────────────────

def screen_about():
    header()

    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="bold red",   no_wrap=True)
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
            out = subprocess.check_output(["ffmpeg", "-version"],
                                          stderr=subprocess.STDOUT, text=True)
            ffmpeg_v = out.splitlines()[0].split("version")[1].split()[0]
        except Exception:
            ffmpeg_v = "Found"

    grid.add_row("Tool",         "🧛 The Dracula YouTube Downloader")
    grid.add_row("Version",      "1.0.4")
    grid.add_row("yt-dlp",       ytdlp_ver)
    grid.add_row("FFmpeg",       ffmpeg_v)
    grid.add_row("Python",       platform.python_version())
    grid.add_row("OS",           platform.system() + " " + platform.release())
    grid.add_row("Default Dir",  get_default_dir())

    console.print(Panel(
        grid,
        title="[bold red]About The Dracula[/bold red]",
        border_style="red", box=box.DOUBLE_EDGE, padding=(1, 4)
    ))
    console.print()
    console.print(Padding(
        "[dim]The Dracula rises from the dark to download your videos.\n"
        "MIT License · Free to use, modify, distribute.[/dim]",
        (0, 4)
    ))
    _back_prompt()


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def _get_title(url: str) -> str:
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                                "skip_download": True}) as ydl:
            data = ydl.extract_info(url, download=False)
            return data.get("title", "")
    except Exception:
        return ""


def _get_playlist_title(url: str) -> str:
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                                "skip_download": True,
                                "extract_flat": True}) as ydl:
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
    questionary.Choice("  🎵   Download Audio Only       MP3 / FLAC / WAV / M4A / OPUS",   "audio"),
    questionary.Choice("  📋   Download Playlist         Full playlist — video or audio",   "playlist"),
    questionary.Choice("  📊   List Formats              Browse all available formats",     "formats"),
    questionary.Choice("  ℹ    About / System Info",                                       "about"),
    questionary.Separator("  ─────────────────────────────"),
    questionary.Choice("  ✖    Exit",                                                      "exit"),
]


def run_tui():
    """Entry point — launches the full TUI main loop."""
    while True:
        header()

        # Status bar
        import shutil
        ffmpeg_ok = bool(shutil.which("ffmpeg"))
        status_items = [
            f"[bold green]● FFmpeg[/bold green]" if ffmpeg_ok else "[bold red]○ FFmpeg missing[/bold red]",
            f"[bold green]● yt-dlp[/bold green]",
            f"[dim]{get_default_dir()}[/dim]",
        ]
        status_row = "    ".join(status_items)
        console.print(Panel(status_row, border_style="dim red",
                            box=box.ROUNDED, padding=(0, 2)))
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
                        Text("🧛  The Dracula sleeps…\nUntil darkness falls again.",
                             style="bold red", justify="center")
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
        elif choice == "formats":
            screen_formats()
        elif choice == "about":
            screen_about()


# ─────────────────────────────────────────────────────────────
#  STANDALONE TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_tui()

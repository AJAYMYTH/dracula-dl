#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════╗
║                     THE DRACULA DOWNLOADER                           ║
║                  YouTube Download CLI Tool                            ║
╚═══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import re
import argparse
from pathlib import Path
from urllib.parse import urlparse

# ── Run dependency & FFmpeg checks BEFORE anything else ──────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from dracula_dl import setup_check as _sc
except ImportError:
    try:
        import setup_check as _sc
    except Exception as _sc_err:
        print(f"[WARN] Could not load setup_check: {_sc_err}")
        _sc = None

# Now safe to import yt_dlp
try:
    import yt_dlp
except ImportError:
    print("[FATAL] yt-dlp is not available even after setup_check. "
          "Please run: pip install yt-dlp")
    sys.exit(1)

try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    COLORAMA = True
except ImportError:
    COLORAMA = False
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = WHITE = BLUE = ""
    class Style:
        BRIGHT = RESET_ALL = DIM = ""
    class Back:
        BLACK = ""

# Import Rich components
try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import (
        Progress, SpinnerColumn, TextColumn, BarColumn,
        TaskProgressColumn, TransferSpeedColumn, TimeRemainingColumn
    )
    rich_console = Console(force_terminal=True, highlight=False)
    RICH_AVAILABLE = True
except ImportError:
    rich_console = None
    RICH_AVAILABLE = False

# Import TUI
try:
    from dracula_dl import tui as _tui
except ImportError:
    try:
        import tui as _tui
    except Exception as _tui_err:
        _tui = None

# Import Config and History modules
try:
    from dracula_dl.config import load_config, save_config, get_config_dir
    from dracula_dl.history import add_history_entry, read_history, log_debug
except ImportError:
    try:
        from config import load_config, save_config, get_config_dir
        from history import add_history_entry, read_history, log_debug
    except ImportError:
        def load_config(): return {}
        def save_config(cfg): return False
        def get_config_dir(): return Path.home() / ".config" / "dracula"
        def add_history_entry(*args, **kwargs): pass
        def read_history(limit=50): return [], 0
        def log_debug(msg, exception=None): pass

try:
    from dracula_dl import __version__
except ImportError:
    try:
        from __init__ import __version__
    except ImportError:
        __version__ = "1.1.2"

# ─────────────────────────────────────────────
#  ASCII ART HEADER
# ─────────────────────────────────────────────

DRACULA_LOGO = r"""
{}{}
  ██████╗ ██████╗  █████╗  ██████╗██╗   ██╗██╗      █████╗ 
  ██╔══██╗██╔══██╗██╔══██╗██╔════╝██║   ██║██║     ██╔══██╗
  ██║  ██║██████╔╝███████║██║     ██║   ██║██║     ███████║
  ██║  ██║██╔══██╗██╔══██║██║     ██║   ██║██║     ██╔══██║
  ██████╔╝██║  ██║██║  ██║╚██████╗╚██████╔╝███████╗██║  ██║
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
{}
  ╔══════════════════════════════════════════════════════════╗
  ║   🧛 The Dracula  ·  YouTube Downloader CLI  v{:<8} ║
  ║      Powered by yt-dlp  ·  Rising from the dark...     ║
  ╚══════════════════════════════════════════════════════════╝
{}
""".format(
    Fore.RED + Style.BRIGHT,
    Fore.MAGENTA,
    Fore.CYAN + Style.BRIGHT,
    __version__,
    Style.RESET_ALL
)

SEPARATOR = Fore.RED + "  " + "═" * 58 + Style.RESET_ALL


# ─────────────────────────────────────────────
#  RICH PROGRESS & HOOK
# ─────────────────────────────────────────────

_current_progress = None
_current_task_id = None


def get_progress_hook():
    """Returns a progress hook that updates Rich progress if available."""
    def hook(d):
        global _current_progress, _current_task_id
        status = d.get('status')
        if status == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            if _current_progress and _current_task_id is not None:
                if total > 0:
                    _current_progress.update(_current_task_id, total=total, completed=downloaded)
                else:
                    _current_progress.update(_current_task_id, completed=downloaded)
            else:
                percent = d.get('_percent_str', '?%').strip()
                speed = d.get('_speed_str', '?').strip()
                eta = d.get('_eta_str', '?').strip()
                line = f"\r  {Fore.CYAN}Downloading:{Style.RESET_ALL} {percent} at {speed} (ETA: {eta})"
                print(line, end='', flush=True)

        elif status == 'finished':
            if not _current_progress:
                print(f"\n  {Fore.GREEN}✔  Download complete → {Style.BRIGHT}{d.get('filename','')}{Style.RESET_ALL}")

        elif status == 'error':
            if not _current_progress:
                print(f"\n  {Fore.RED}✘  Error downloading: {d.get('filename','')}{Style.RESET_ALL}")

    return hook


# ─────────────────────────────────────────────
#  HELPERS & VALIDATION
# ─────────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    """Validate whether input is a well-formed HTTP/HTTPS URL."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ('http', 'https') and parsed.netloc)
    except Exception:
        return False


def format_count(val) -> str:
    """Safely format view count / integer with thousands separators."""
    if val is None:
        return "N/A"
    try:
        return f"{int(val):,}"
    except (ValueError, TypeError):
        return str(val)


def format_bytes(size) -> str:
    """Format bytes into readable string."""
    if not size:
        return "Unknown"
    try:
        size = float(size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except Exception:
        return "Unknown"


def parse_rate(rate_str: str) -> int | None:
    """Parse human readable rate limit string (e.g. '500k', '2m') to bytes/sec."""
    if not rate_str:
        return None
    rate_str = rate_str.strip().lower()
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([kmg])?b?$', rate_str)
    if not match:
        try:
            return int(rate_str)
        except ValueError:
            return None
    val = float(match.group(1))
    unit = match.group(2)
    if unit == 'k':
        val *= 1024
    elif unit == 'm':
        val *= 1024 * 1024
    elif unit == 'g':
        val *= 1024 * 1024 * 1024
    return int(val)


def print_header():
    print(DRACULA_LOGO)


def print_separator():
    print(SEPARATOR)


def print_info(msg):
    print(f"  {Fore.CYAN}ℹ  {Style.RESET_ALL}{msg}")


def print_success(msg):
    print(f"  {Fore.GREEN}✔  {Style.RESET_ALL}{msg}")


def print_warn(msg):
    print(f"  {Fore.YELLOW}⚠  {Style.RESET_ALL}{msg}")


def print_error(msg, fatal: bool = True):
    print(f"  {Fore.RED}✘  {Style.RESET_ALL}{msg}")
    if fatal:
        sys.exit(1)


def print_section(title):
    print(f"\n  {Fore.MAGENTA}{Style.BRIGHT}{title}{Style.RESET_ALL}")
    print(f"  {Fore.RED}{'─' * 50}{Style.RESET_ALL}")



def print_error_panel(error_msg: str, hint: str = None):
    """Render DownloadError inside a styled Rich Panel with actionable hint."""
    hint_text = hint or "Check the URL, your internet connection, or run 'dracula formats <url>' to inspect available streams."
    if RICH_AVAILABLE and rich_console:
        panel_content = f"[bold white]{error_msg}[/bold white]\n\n[dim cyan]💡 Hint: {hint_text}[/dim cyan]"
        panel = Panel(
            panel_content,
            title="[bold red]🧛 Download Failed[/bold red]",
            border_style="red",
            expand=False
        )
        rich_console.print(panel)
    else:
        print(f"\n  {Fore.RED}✘  Error: {error_msg}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}💡 Hint: {hint_text}{Style.RESET_ALL}\n")


def print_summary_table(summary_items: list[dict], title: str = "Download Summary"):
    """Render post-download summary table for playlist/batch runs."""
    if not summary_items:
        return

    if RICH_AVAILABLE and rich_console:
        table = Table(title=title, box=box.ROUNDED, border_style="magenta", header_style="bold magenta")
        table.add_column("#", style="dim", justify="right")
        table.add_column("Title", style="bold white")
        table.add_column("Format", style="cyan")
        table.add_column("Size", style="yellow")
        table.add_column("Status", style="bold")

        for idx, item in enumerate(summary_items, 1):
            st = item.get('status')
            if st == 'success':
                status_str = "[green]✔ Done[/green]"
            elif st == 'dry-run':
                status_str = "[cyan]Dry-Run[/cyan]"
            else:
                status_str = "[red]✘ Failed[/red]"
            table.add_row(
                str(idx),
                item.get('title', 'Unknown')[:40],
                item.get('format', 'N/A'),
                item.get('size', 'Unknown'),
                status_str
            )
        rich_console.print()
        rich_console.print(table)
        rich_console.print()
    else:
        print_section(title)
        for idx, item in enumerate(summary_items, 1):
            st = item.get('status')
            status_mark = f"{Fore.GREEN}✔ Done{Style.RESET_ALL}" if st == 'success' else (f"{Fore.CYAN}Dry-Run{Style.RESET_ALL}" if st == 'dry-run' else f"{Fore.RED}✘ Failed{Style.RESET_ALL}")
            print(f"  {idx}. {item.get('title','Unknown')[:35]:<35} | {item.get('format','N/A'):<8} | {status_mark}")


def get_output_dir() -> str:
    """Return configured or default download directory."""
    config = load_config()
    out_dir = config.get("output_dir") or str(Path.home() / "Downloads" / "Dracula")
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def cleanup_leftovers(output_dir: str):
    """Scan output directory and remove leftover .part/.ytdl files, logging exceptions."""
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
                        log_debug(f"Failed to remove leftover file: {file_path}", e)
    except Exception as e:
        log_debug(f"Error during cleanup_leftovers for directory: {output_dir}", e)


# ─────────────────────────────────────────────
#  FETCH VIDEO INFO & FORMATS
# ─────────────────────────────────────────────

def fetch_info(url: str) -> dict | None:
    if not is_valid_url(url):
        print_warn(f"Invalid URL structure: '{url}'")
        return None

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        log_debug(f"fetch_info failed for {url}", e)
        print_error_panel(str(e), "Failed to fetch metadata. Verify the URL is accessible.")
        return None


def display_formats(info: dict):
    formats = info.get('formats', [])
    if not formats:
        print_warn("No format info available.")
        return

    print_section("Available Formats")
    print(f"  {Fore.WHITE}{Style.BRIGHT}"
          f"{'ID':<12} {'EXT':<6} {'RESOLUTION':<14} {'FPS':<6} {'VCODEC':<18} {'ACODEC':<16} {'SIZE':>10}"
          f"{Style.RESET_ALL}")
    print(f"  {Fore.RED}{'─'*82}{Style.RESET_ALL}")

    for f in formats:
        fid   = str(f.get('format_id', ''))[:11]
        ext   = str(f.get('ext', ''))[:5]
        res   = f.get('resolution') or (
            f"{f.get('width','?')}x{f.get('height','?')}" if f.get('width') else 'audio only'
        )
        fps   = str(f.get('fps', ''))[:5] if f.get('fps') else ''
        vco   = str(f.get('vcodec', 'none'))[:17]
        aco   = str(f.get('acodec', 'none'))[:15]
        fsize = f.get('filesize') or f.get('filesize_approx')
        size_str = f"{fsize/1024/1024:.1f}M" if fsize else '?'

        if vco == 'none':
            row_color = Fore.YELLOW
        elif aco == 'none':
            row_color = Fore.CYAN
        else:
            row_color = Fore.WHITE

        print(f"  {row_color}"
              f"{fid:<12} {ext:<6} {str(res):<14} {fps:<6} {vco:<18} {aco:<16} {size_str:>10}"
              f"{Style.RESET_ALL}")

    print(f"\n  {Fore.YELLOW}Legend:{Style.RESET_ALL} "
          f"{Fore.CYAN}Cyan{Style.RESET_ALL}=Video-only  "
          f"{Fore.YELLOW}Yellow{Style.RESET_ALL}=Audio-only  "
          f"{Fore.WHITE}White{Style.RESET_ALL}=Combined")


# ─────────────────────────────────────────────
#  BASE OPTIONS BUILDER
# ─────────────────────────────────────────────

def build_base_opts(
    output_dir: str,
    extra: dict = None,
    subs: str = None,
    auto_subs: bool = False,
    embed_subs: bool = False,
    embed_thumbnail: bool = False,
    limit_rate: str = None,
    dry_run: bool = False
) -> dict:

    template = os.path.join(output_dir, '%(title)s.%(ext)s')
    opts = {
        'outtmpl': template,
        'progress_hooks': [get_progress_hook()],
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'retries': 10,
        'fragment_retries': 10,
        'file_access_retries': 5,
        'socket_timeout': 30,
        'http_chunk_size': 10 * 1024 * 1024,
        'continuedl': True,  # Resume-awareness
    }

    # Dry-run
    if dry_run:
        opts['skip_download'] = True

    # Rate limit
    if limit_rate:
        rate_bytes = parse_rate(limit_rate)
        if rate_bytes:
            opts['ratelimit'] = rate_bytes

    # Subtitles
    if subs or auto_subs:
        opts['writesubtitles'] = True
        if auto_subs:
            opts['writeautomaticsub'] = True
        if subs:
            opts['subtitleslangs'] = [lang.strip() for lang in subs.split(',') if lang.strip()]

        if embed_subs:
            opts.setdefault('postprocessors', []).append({'key': 'FFmpegEmbedSubtitle'})

    # Thumbnail embedding
    if embed_thumbnail:
        opts['writethumbnail'] = True
        opts.setdefault('postprocessors', []).append({'key': 'EmbedThumbnail'})

    if extra:
        opts.update(extra)

    return opts


# ─────────────────────────────────────────────
#  DOWNLOAD HANDLERS
# ─────────────────────────────────────────────

def download_video(
    url: str,
    output_dir: str = None,
    format_id: str = None,
    quality: str = 'best',
    subs: str = None,
    auto_subs: bool = False,
    embed_subs: bool = False,
    embed_thumbnail: bool = False,
    limit_rate: str = None,
    dry_run: bool = False
) -> dict:

    if not is_valid_url(url):
        print_error(f"Invalid or malformed URL: '{url}'. Must start with http:// or https://")

    config = load_config()
    output_dir = output_dir or config.get("output_dir") or get_output_dir()
    quality = quality or config.get("default_quality", "720p")

    print_section("Video Download")
    print_info(f"URL     : {url}")
    print_info(f"Saving  : {output_dir}")

    quality_map = {
        '4k': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
        '1440p': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
        'best': 'bestvideo+bestaudio/best',
        'worst': 'worstvideo+worstaudio/worst',
    }

    fmt = format_id if format_id else quality_map.get(quality, quality_map['best'])
    print_info(f"Format  : {format_id or quality}")

    opts = build_base_opts(
        output_dir,
        extra={'format': fmt, 'merge_output_format': 'mp4'},
        subs=subs,
        auto_subs=auto_subs,
        embed_subs=embed_subs,
        embed_thumbnail=embed_thumbnail,
        limit_rate=limit_rate,
        dry_run=dry_run
    )

    print_separator()

    global _current_progress, _current_task_id
    title = "Unknown Video"
    file_size = "Unknown"
    status = "failed"
    err_msg = None

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as meta_ydl:
            info = meta_ydl.extract_info(url, download=False)
            if info:
                title = info.get('title', title)
                file_size = format_bytes(info.get('filesize') or info.get('filesize_approx'))

        if dry_run:
            print_info(f"[DRY-RUN] Would download: '{title}' ({file_size})")
            add_history_entry(title, url, f"video ({quality})", quality, output_dir, status="dry-run")
            return {'title': title, 'format': quality, 'size': file_size, 'status': 'dry-run'}

        if RICH_AVAILABLE and rich_console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=30, style="dim white", complete_style="red"),
                TaskProgressColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=rich_console
            ) as progress:
                _current_progress = progress
                _current_task_id = progress.add_task(f"[cyan]Downloading: {title[:30]}", total=None)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                _current_progress = None
                _current_task_id = None
        else:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

        print_success("Download complete!")
        status = "success"
        add_history_entry(title, url, "video", quality, output_dir, status="success")

    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e)
        log_debug(f"Download failed for {url}", e)
        print_error_panel(err_msg)
        add_history_entry(title, url, "video", quality, output_dir, status="failed", error=err_msg)
        print_error(f"Download failed: {err_msg}", fatal=True)
    except Exception as e:
        err_msg = str(e)
        log_debug(f"Unexpected download exception for {url}", e)
        print_error_panel(err_msg)
        add_history_entry(title, url, "video", quality, output_dir, status="failed", error=err_msg)
        print_error(f"Error: {err_msg}", fatal=True)
    finally:
        _current_progress = None
        _current_task_id = None
        cleanup_leftovers(output_dir)

    return {'title': title, 'format': quality, 'size': file_size, 'status': status}


def download_audio(
    url: str,
    output_dir: str = None,
    audio_fmt: str = 'mp3',
    quality: str = '192',
    embed_thumbnail: bool = False,
    limit_rate: str = None,
    dry_run: bool = False
) -> dict:

    if not is_valid_url(url):
        print_error(f"Invalid or malformed URL: '{url}'. Must start with http:// or https://")

    config = load_config()
    output_dir = output_dir or config.get("output_dir") or get_output_dir()
    audio_fmt = audio_fmt or config.get("default_audio_format", "mp3")
    quality = quality or config.get("default_audio_bitrate", "192")

    print_section("Audio Download")
    print_info(f"URL     : {url}")
    print_info(f"Saving  : {output_dir}")
    print_info(f"Format  : {audio_fmt.upper()} @ {quality} kbps")

    postprocessors = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': audio_fmt,
        'preferredquality': quality,
    }]

    opts = build_base_opts(
        output_dir,
        extra={'format': 'bestaudio/best', 'postprocessors': postprocessors},
        embed_thumbnail=embed_thumbnail,
        limit_rate=limit_rate,
        dry_run=dry_run
    )

    print_separator()

    global _current_progress, _current_task_id
    title = "Unknown Audio"
    file_size = "Unknown"
    status = "failed"
    err_msg = None

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as meta_ydl:
            info = meta_ydl.extract_info(url, download=False)
            if info:
                title = info.get('title', title)
                file_size = format_bytes(info.get('filesize') or info.get('filesize_approx'))

        if dry_run:
            print_info(f"[DRY-RUN] Would download audio: '{title}' ({audio_fmt} {quality}k)")
            add_history_entry(title, url, f"audio ({audio_fmt})", f"{quality}k", output_dir, status="dry-run")
            return {'title': title, 'format': f"{audio_fmt} ({quality}k)", 'size': file_size, 'status': 'dry-run'}

        if RICH_AVAILABLE and rich_console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=30, style="dim white", complete_style="magenta"),
                TaskProgressColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=rich_console
            ) as progress:
                _current_progress = progress
                _current_task_id = progress.add_task(f"[magenta]Extracting Audio: {title[:30]}", total=None)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                _current_progress = None
                _current_task_id = None
        else:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

        print_success("Audio extraction complete!")
        status = "success"
        add_history_entry(title, url, f"audio ({audio_fmt})", f"{quality}k", output_dir, status="success")

    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e)
        log_debug(f"Audio download failed for {url}", e)
        print_error_panel(err_msg)
        add_history_entry(title, url, f"audio ({audio_fmt})", f"{quality}k", output_dir, status="failed", error=err_msg)
        print_error(f"Audio download failed: {err_msg}", fatal=True)
    except Exception as e:
        err_msg = str(e)
        log_debug(f"Unexpected audio exception for {url}", e)
        print_error_panel(err_msg)
        add_history_entry(title, url, f"audio ({audio_fmt})", f"{quality}k", output_dir, status="failed", error=err_msg)
        print_error(f"Error: {err_msg}", fatal=True)
    finally:
        _current_progress = None
        _current_task_id = None
        cleanup_leftovers(output_dir)

    return {'title': title, 'format': f"{audio_fmt} ({quality}k)", 'size': file_size, 'status': status}


def download_playlist(
    url: str,
    output_dir: str = None,
    quality: str = 'best',
    audio_only: bool = False,
    audio_fmt: str = 'mp3',
    audio_bitrate: str = '192',
    start: int = None,
    end: int = None,
    subs: str = None,
    auto_subs: bool = False,
    embed_subs: bool = False,
    embed_thumbnail: bool = False,
    limit_rate: str = None,
    dry_run: bool = False,
    retry_failed: bool = False
) -> list[dict]:

    if not is_valid_url(url):
        print_error(f"Invalid or malformed URL: '{url}'. Must start with http:// or https://")

    config = load_config()
    output_dir = output_dir or config.get("output_dir") or get_output_dir()

    print_section("Playlist Download")
    print_info(f"URL       : {url}")
    print_info(f"Saving    : {output_dir}")

    # If --retry-failed is passed, gather failed entries from history
    urls_to_download = [url]
    if retry_failed:
        history_entries, _ = read_history(limit=200)
        failed_urls = [e.get('url') for e in history_entries if e.get('status') == 'failed' and e.get('url')]
        if failed_urls:
            print_info(f"Retrying {len(failed_urls)} previously failed download(s)...")
            urls_to_download = failed_urls
        else:
            print_info("No recent failed downloads found in history log. Downloading playlist normally.")

    template = os.path.join(output_dir, '%(playlist_title)s', '%(playlist_index)s - %(title)s.%(ext)s')

    quality_map = {
        '4k': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
        '1440p': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
        'best': 'bestvideo+bestaudio/best',
        'worst': 'worstvideo+worstaudio/worst',
    }

    extra_opts = {
        'outtmpl': template,
        'ignoreerrors': True,
    }

    if audio_only:
        print_info(f"Mode      : Audio only ({audio_fmt.upper()} @ {audio_bitrate}k)")
        extra_opts['format'] = 'bestaudio/best'
        extra_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_fmt,
            'preferredquality': audio_bitrate,
        }]
    else:
        print_info(f"Quality   : {quality}")
        extra_opts['format'] = quality_map.get(quality, quality_map['best'])
        extra_opts['merge_output_format'] = 'mp4'

    if start:
        extra_opts['playliststart'] = start
        print_info(f"Start at  : item {start}")
    if end:
        extra_opts['playlistend'] = end
        print_info(f"End at    : item {end}")

    opts = build_base_opts(
        output_dir,
        extra=extra_opts,
        subs=subs,
        auto_subs=auto_subs,
        embed_subs=embed_subs,
        embed_thumbnail=embed_thumbnail,
        limit_rate=limit_rate,
        dry_run=dry_run
    )

    print_separator()

    summary_items = []

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            for target_url in urls_to_download:
                res = ydl.extract_info(target_url, download=not dry_run)
                if res:
                    entries = res.get('entries') if 'entries' in res else [res]
                    for entry in (entries or []):
                        if entry:
                            item_title = entry.get('title', 'Unknown Item')
                            item_size = format_bytes(entry.get('filesize') or entry.get('filesize_approx'))
                            summary_items.append({
                                'title': item_title,
                                'format': 'audio' if audio_only else quality,
                                'size': item_size,
                                'status': 'dry-run' if dry_run else 'success'
                            })
                            add_history_entry(
                                item_title,
                                entry.get('webpage_url', target_url),
                                'audio' if audio_only else 'video',
                                audio_bitrate if audio_only else quality,
                                output_dir,
                                status='dry-run' if dry_run else 'success'
                            )

        print_success("Playlist processing complete!")
        print_summary_table(summary_items, title="Playlist Download Summary")

    except yt_dlp.utils.DownloadError as e:
        log_debug(f"Playlist download error for {url}", e)
        print_error_panel(str(e))
        print_error(f"Playlist download error: {e}", fatal=True)
    except Exception as e:
        log_debug(f"Unexpected playlist exception for {url}", e)
        print_error_panel(str(e))
        print_error(f"Error: {e}", fatal=True)
    finally:
        cleanup_leftovers(output_dir)

    return summary_items


def download_batch(
    input_file: str = None,
    urls: list[str] = None,
    output_dir: str = None,
    quality: str = 'best',
    audio_only: bool = False,
    audio_fmt: str = 'mp3',
    audio_bitrate: str = '192',
    subs: str = None,
    auto_subs: bool = False,
    embed_subs: bool = False,
    embed_thumbnail: bool = False,
    limit_rate: str = None,
    dry_run: bool = False
) -> list[dict]:

    url_list = []
    if input_file:
        path = Path(input_file)
        if not path.exists():
            print_error(f"Batch file not found: '{input_file}'")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if is_valid_url(line):
                        url_list.append(line)
                    else:
                        print_warn(f"Skipping invalid URL in batch file: '{line}'")

    if urls:
        for u in urls:
            if is_valid_url(u):
                url_list.append(u)
            else:
                print_warn(f"Skipping invalid URL argument: '{u}'")

    if not url_list:
        print_error("No valid URLs provided for batch processing.")

    config = load_config()
    output_dir = output_dir or config.get("output_dir") or get_output_dir()

    print_section(f"Batch Download ({len(url_list)} items)")
    print_info(f"Saving to : {output_dir}")

    summary_items = []
    total = len(url_list)

    for idx, target_url in enumerate(url_list, 1):
        print(f"\n  {Fore.MAGENTA}{Style.BRIGHT}[{idx}/{total}]{Style.RESET_ALL} {Fore.CYAN}{target_url}{Style.RESET_ALL}")
        try:
            if audio_only:
                res = download_audio(
                    target_url,
                    output_dir=output_dir,
                    audio_fmt=audio_fmt,
                    quality=audio_bitrate,
                    embed_thumbnail=embed_thumbnail,
                    limit_rate=limit_rate,
                    dry_run=dry_run
                )
            else:
                res = download_video(
                    target_url,
                    output_dir=output_dir,
                    quality=quality,
                    subs=subs,
                    auto_subs=auto_subs,
                    embed_subs=embed_subs,
                    embed_thumbnail=embed_thumbnail,
                    limit_rate=limit_rate,
                    dry_run=dry_run
                )
            summary_items.append(res)
        except SystemExit:
            summary_items.append({
                'title': target_url,
                'format': 'audio' if audio_only else quality,
                'size': 'Unknown',
                'status': 'failed'
            })
            continue
        except Exception as e:
            log_debug(f"Batch item failed: {target_url}", e)
            summary_items.append({
                'title': target_url,
                'format': 'audio' if audio_only else quality,
                'size': 'Unknown',
                'status': 'failed'
            })

    print_summary_table(summary_items, title="Batch Download Summary")
    return summary_items


# ─────────────────────────────────────────────
#  HISTORY & COMPLETION HELPERS
# ─────────────────────────────────────────────

def display_history(limit: int = 50):
    entries, total = read_history(limit=limit)
    print_section("Download History Log")

    if not entries:
        print_info("No download history recorded yet.")
        return

    if RICH_AVAILABLE and rich_console:
        table = Table(title=f"Recent Downloads (Showing {len(entries)} of {total})", box=box.ROUNDED, border_style="magenta", header_style="bold magenta")
        table.add_column("Timestamp", style="dim", justify="left")
        table.add_column("Title", style="bold white")
        table.add_column("Format / Quality", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("URL", style="dim blue")

        for e in entries:
            st = "[green]✔ Success[/green]" if e.get('status') == 'success' else f"[red]✘ {e.get('status')}[/red]"
            table.add_row(
                e.get('timestamp', 'N/A'),
                e.get('title', 'Unknown')[:35],
                f"{e.get('format','')} ({e.get('quality_or_bitrate','')})",
                st,
                e.get('url', '')[:30]
            )
        rich_console.print(table)
    else:
        print(f"  Showing {len(entries)} of {total} entries:\n")
        for e in entries:
            st = f"{Fore.GREEN}✔{Style.RESET_ALL}" if e.get('status') == 'success' else f"{Fore.RED}✘{Style.RESET_ALL}"
            print(f"  [{e.get('timestamp','')}] {st} {e.get('title','')[:40]} | {e.get('format','')} ({e.get('quality_or_bitrate','')})")

    if total > len(entries):
        print_info(f"Log contains {total - len(entries)} older records in ~/.config/dracula/history.jsonl")


def display_completion():
    print_section("Shell Completion Setup")
    print_info("To enable auto-completion for Dracula CLI in bash/zsh:")
    print("\n  1. Install argcomplete: pip install argcomplete")
    print("  2. Add to your ~/.bashrc or ~/.zshrc:")
    print("     eval \"$(register-python-argcomplete dracula)\"")
    print("\n  Alternatively, use alias dracula='python -m dracula_dl.cli'")


# ─────────────────────────────────────────────
#  INTERACTIVE MODE
# ─────────────────────────────────────────────

def prompt(msg, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"  {Fore.CYAN}?{Style.RESET_ALL} {msg}{suffix}: ").strip()
    return val if val else default


def interactive_mode():
    if _sc:
        _sc.run_checks(verbose=True)

    print_header()
    print_separator()
    print(f"\n  {Fore.MAGENTA}{Style.BRIGHT}Welcome to The Dracula Interactive Mode{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}The dark lord of downloaders rises…{Style.RESET_ALL}\n")

    cfg = load_config()
    out_dir = cfg.get("output_dir") or get_output_dir()

    print("  Choose download mode:")
    print(f"    {Fore.CYAN}1{Style.RESET_ALL}. Single Video")
    print(f"    {Fore.CYAN}2{Style.RESET_ALL}. Audio Only (MP3/M4A/etc.)")
    print(f"    {Fore.CYAN}3{Style.RESET_ALL}. Full Playlist")
    print(f"    {Fore.CYAN}4{Style.RESET_ALL}. Batch File / Multi-URL")
    print(f"    {Fore.CYAN}5{Style.RESET_ALL}. Inspect Formats")
    print(f"    {Fore.CYAN}6{Style.RESET_ALL}. View Recent Download History")
    print(f"    {Fore.CYAN}7{Style.RESET_ALL}. Rich TUI Mode")
    print(f"    {Fore.CYAN}8{Style.RESET_ALL}. Exit\n")

    choice = prompt("Select an option (1-8)", default="1")

    if choice == '1':
        url = prompt("Enter video URL")
        if not is_valid_url(url):
            print_error("Invalid URL entered.")
        quality = prompt("Quality (best, 1080p, 720p, 480p, worst)", default=cfg.get("default_quality", "720p"))
        dest = prompt("Save to directory", default=out_dir)
        embed_thumb = prompt("Embed thumbnail? (y/n)", default="n").lower() == 'y'
        download_video(url, output_dir=dest, quality=quality, embed_thumbnail=embed_thumb)

    elif choice == '2':
        url = prompt("Enter video URL")
        if not is_valid_url(url):
            print_error("Invalid URL entered.")
        fmt = prompt("Audio format (mp3, m4a, wav, flac, opus)", default=cfg.get("default_audio_format", "mp3"))
        bitrate = prompt("Bitrate kbps (128, 192, 256, 320)", default=cfg.get("default_audio_bitrate", "192"))
        dest = prompt("Save to directory", default=out_dir)
        embed_thumb = prompt("Embed thumbnail? (y/n)", default="n").lower() == 'y'
        download_audio(url, output_dir=dest, audio_fmt=fmt, quality=bitrate, embed_thumbnail=embed_thumb)

    elif choice == '3':
        url = prompt("Enter playlist URL")
        if not is_valid_url(url):
            print_error("Invalid URL entered.")
        mode = prompt("Audio only? (y/n)", default="n").lower()
        audio_only = mode == 'y'
        fmt = cfg.get("default_audio_format", "mp3")
        bitrate = cfg.get("default_audio_bitrate", "192")
        quality = cfg.get("default_quality", "720p")
        if audio_only:
            fmt = prompt("Audio format", default=fmt)
            bitrate = prompt("Audio bitrate", default=bitrate)
        else:
            quality = prompt("Quality", default=quality)
        dest = prompt("Save to directory", default=out_dir)
        download_playlist(url, output_dir=dest, quality=quality, audio_only=audio_only, audio_fmt=fmt, audio_bitrate=bitrate)

    elif choice == '4':
        batch_file = prompt("Enter path to URLs text file")
        dest = prompt("Save to directory", default=out_dir)
        download_batch(input_file=batch_file, output_dir=dest)

    elif choice == '5':
        url = prompt("Enter video URL")
        info = fetch_info(url)
        if info:
            print_info(f"Title    : {info.get('title','N/A')}")
            print_info(f"Channel  : {info.get('uploader','N/A')}")
            print_info(f"Duration : {info.get('duration_string','N/A')}")
            print_info(f"Views    : {format_count(info.get('view_count'))}")
            display_formats(info)

    elif choice == '6':
        display_history()

    elif choice == '7':
        if _tui:
            _tui.launch_tui()
        else:
            print_error("Rich TUI module unavailable. Install dependencies: pip install rich questionary")

    elif choice == '8':
        print("\n  🧛 Farewell... until the night falls again.\n")
        sys.exit(0)


# ─────────────────────────────────────────────
#  MAIN CLI ENTRY POINT
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) == 1:
        if _tui:
            _tui.launch_tui()
        else:
            interactive_mode()
        return

    config = load_config()

    parser = argparse.ArgumentParser(
        prog="dracula",
        description="🧛 The Dracula — Powerful YouTube Downloader CLI powered by yt-dlp",
        epilog="Run 'dracula' without arguments to enter interactive mode."
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s v{__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Shared common arguments
    def add_common_download_args(p):
        p.add_argument("-o", "--output", help="Output directory", default=config.get("output_dir"))
        p.add_argument("--embed-thumbnail", action="store_true", help="Embed thumbnail into output file")
        p.add_argument("--limit-rate", help="Maximum download speed limit (e.g. 500k, 2m)")
        p.add_argument("--dry-run", "--simulate", action="store_true", help="Simulate download without saving files")

    # 1. video
    p_video = subparsers.add_parser("video", help="Download a single video")
    p_video.add_argument("-u", "--url", required=True, help="YouTube video URL")
    p_video.add_argument("-q", "--quality", choices=["best", "worst", "4k", "1440p", "1080p", "720p", "480p", "360p"],
                         default=config.get("default_quality", "720p"), help="Video quality")
    p_video.add_argument("-f", "--format-id", help="Specific format ID (from 'dracula formats')")
    p_video.add_argument("--subs", help="Comma-separated subtitle language codes (e.g. en,es)")
    p_video.add_argument("--auto-subs", action="store_true", help="Download auto-generated subtitles")
    p_video.add_argument("--embed-subs", action="store_true", help="Embed subtitles into video container")
    add_common_download_args(p_video)

    # 2. audio
    p_audio = subparsers.add_parser("audio", help="Download audio only (extract MP3/M4A/etc.)")
    p_audio.add_argument("-u", "--url", required=True, help="YouTube video URL")
    p_audio.add_argument("-f", "--format", choices=["mp3", "m4a", "wav", "flac", "opus", "aac"],
                         default=config.get("default_audio_format", "mp3"), help="Audio format")
    p_audio.add_argument("-b", "--bitrate", choices=["128", "192", "256", "320"],
                         default=config.get("default_audio_bitrate", "192"), help="Audio bitrate kbps")
    add_common_download_args(p_audio)

    # 3. playlist
    p_play = subparsers.add_parser("playlist", help="Download an entire YouTube playlist")
    p_play.add_argument("-u", "--url", required=True, help="YouTube playlist URL")
    p_play.add_argument("-q", "--quality", choices=["best", "worst", "4k", "1440p", "1080p", "720p", "480p", "360p"],
                        default=config.get("default_quality", "720p"), help="Video quality")
    p_play.add_argument("--audio-only", action="store_true", help="Download audio only")
    p_play.add_argument("-f", "--format", choices=["mp3", "m4a", "wav", "flac", "opus", "aac"],
                        default=config.get("default_audio_format", "mp3"), help="Audio format when --audio-only")
    p_play.add_argument("-b", "--bitrate", choices=["128", "192", "256", "320"],
                        default=config.get("default_audio_bitrate", "192"), help="Audio bitrate kbps when --audio-only")
    p_play.add_argument("--start", type=int, help="Start at playlist item #")
    p_play.add_argument("--end", type=int, help="End at playlist item #")
    p_play.add_argument("--subs", help="Comma-separated subtitle language codes")
    p_play.add_argument("--auto-subs", action="store_true", help="Download auto-generated subtitles")
    p_play.add_argument("--embed-subs", action="store_true", help="Embed subtitles")
    p_play.add_argument("--retry-failed", action="store_true", help="Re-attempt only items that failed previously")
    add_common_download_args(p_play)

    # 4. batch
    p_batch = subparsers.add_parser("batch", help="Download multiple URLs from a text file or flags")
    p_batch.add_argument("-i", "--input-file", help="Path to text file containing URLs (one per line)")
    p_batch.add_argument("-u", "--url", action="append", help="Target URL (can be repeated for multiple URLs)")
    p_batch.add_argument("-q", "--quality", choices=["best", "worst", "4k", "1440p", "1080p", "720p", "480p", "360p"],
                         default=config.get("default_quality", "720p"), help="Video quality")
    p_batch.add_argument("--audio-only", action="store_true", help="Download audio only")
    p_batch.add_argument("-f", "--format", choices=["mp3", "m4a", "wav", "flac", "opus", "aac"],
                         default=config.get("default_audio_format", "mp3"), help="Audio format")
    p_batch.add_argument("-b", "--bitrate", choices=["128", "192", "256", "320"],
                         default=config.get("default_audio_bitrate", "192"), help="Audio bitrate kbps")
    p_batch.add_argument("--subs", help="Comma-separated subtitle language codes")
    p_batch.add_argument("--auto-subs", action="store_true", help="Download auto-generated subtitles")
    p_batch.add_argument("--embed-subs", action="store_true", help="Embed subtitles")
    add_common_download_args(p_batch)

    # 5. formats
    p_fmt = subparsers.add_parser("formats", help="List all available formats for a video")
    p_fmt.add_argument("-u", "--url", required=True, help="YouTube video URL")

    # 6. history
    p_hist = subparsers.add_parser("history", help="Show recent download history")
    p_hist.add_argument("-n", "--limit", type=int, default=50, help="Number of records to show (default: 50)")

    # 7. tui
    subparsers.add_parser("tui", help="Launch the Dracula Rich TUI interactive interface")

    # 8. completion
    subparsers.add_parser("completion", help="Show shell completion setup instructions")

    args = parser.parse_args()

    out = getattr(args, 'output', None) or config.get("output_dir") or get_output_dir()

    if args.command == 'video':
        download_video(
            args.url,
            output_dir=out,
            format_id=args.format_id,
            quality=args.quality,
            subs=args.subs,
            auto_subs=args.auto_subs,
            embed_subs=args.embed_subs,
            embed_thumbnail=args.embed_thumbnail,
            limit_rate=args.limit_rate,
            dry_run=args.dry_run
        )

    elif args.command == 'audio':
        download_audio(
            args.url,
            output_dir=out,
            audio_fmt=args.format,
            quality=args.bitrate,
            embed_thumbnail=args.embed_thumbnail,
            limit_rate=args.limit_rate,
            dry_run=args.dry_run
        )

    elif args.command == 'playlist':
        download_playlist(
            args.url,
            output_dir=out,
            quality=args.quality,
            audio_only=args.audio_only,
            audio_fmt=args.format,
            audio_bitrate=args.bitrate,
            start=args.start,
            end=args.end,
            subs=args.subs,
            auto_subs=args.auto_subs,
            embed_subs=args.embed_subs,
            embed_thumbnail=args.embed_thumbnail,
            limit_rate=args.limit_rate,
            dry_run=args.dry_run,
            retry_failed=args.retry_failed
        )

    elif args.command == 'batch':
        download_batch(
            input_file=args.input_file,
            urls=args.url,
            output_dir=out,
            quality=args.quality,
            audio_only=args.audio_only,
            audio_fmt=args.format,
            audio_bitrate=args.bitrate,
            subs=args.subs,
            auto_subs=args.auto_subs,
            embed_subs=args.embed_subs,
            embed_thumbnail=args.embed_thumbnail,
            limit_rate=args.limit_rate,
            dry_run=args.dry_run
        )

    elif args.command == 'formats':
        print_info("Fetching available formats…")
        info = fetch_info(args.url)
        if info:
            print_info(f"Title    : {info.get('title','N/A')}")
            print_info(f"Channel  : {info.get('uploader','N/A')}")
            print_info(f"Duration : {info.get('duration_string','N/A')}")
            print_info(f"Views    : {format_count(info.get('view_count'))}")
            display_formats(info)

    elif args.command == 'history':
        display_history(limit=args.limit)

    elif args.command == 'tui':
        if _tui:
            _tui.launch_tui()
        else:
            print_error("TUI module not available.")

    elif args.command == 'completion':
        display_completion()

    else:
        if _tui:
            _tui.launch_tui()
        else:
            parser.print_help()


if __name__ == '__main__':
    main()

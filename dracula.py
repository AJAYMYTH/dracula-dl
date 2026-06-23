#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════╗
║                     THE DRACULA DOWNLOADER                           ║
║                  YouTube Download CLI Tool                            ║
╚═══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import argparse
from pathlib import Path

# ── Run dependency & FFmpeg checks BEFORE anything else ──────────────
# setup_check lives in the same directory; add it to sys.path.
sys.path.insert(0, str(Path(__file__).parent))
try:
    import setup_check as _sc
except Exception as _sc_err:
    print(f"[WARN] Could not load setup_check: {_sc_err}")
    _sc = None

# Now safe to import yt_dlp (setup_check already installed it if missing)
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

# Import TUI (requires rich + questionary — installed by setup_check above)
try:
    import tui as _tui
except Exception as _tui_err:
    _tui = None

try:
    from dracula_dl import __version__
except ImportError:
    try:
        from __init__ import __version__
    except ImportError:
        __version__ = "1.0.4"

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
  ║   🧛 The Dracula  ·  YouTube Downloader CLI  v1.0.4    ║
  ║      Powered by yt-dlp  ·  Rising from the dark...     ║
  ╚══════════════════════════════════════════════════════════╝
{}
""".format(
    Fore.RED + Style.BRIGHT,
    Fore.MAGENTA,
    Fore.CYAN + Style.BRIGHT,
    Style.RESET_ALL
)

SEPARATOR = Fore.RED + "  " + "═" * 58 + Style.RESET_ALL


# ─────────────────────────────────────────────
#  PROGRESS HOOK
# ─────────────────────────────────────────────

def progress_hook(d):
    if d['status'] == 'downloading':
        percent    = d.get('_percent_str', '?%').strip()
        speed      = d.get('_speed_str', '?').strip()
        eta        = d.get('_eta_str', '?').strip()
        downloaded = d.get('_downloaded_bytes_str', '').strip()
        total      = d.get('_total_bytes_str', d.get('_total_bytes_estimate_str', '?')).strip()

        bar_width  = 30
        try:
            pct_val = float(percent.replace('%', ''))
            filled  = int(bar_width * pct_val / 100)
        except Exception:
            filled = 0

        bar = (Fore.RED + "█" * filled + Fore.WHITE + Style.DIM +
               "░" * (bar_width - filled) + Style.RESET_ALL)

        line = (
            f"\r  {Fore.CYAN}[{bar}{Fore.CYAN}]{Style.RESET_ALL} "
            f"{Fore.YELLOW}{percent:>6}{Style.RESET_ALL}  "
            f"{Fore.GREEN}↓ {speed:<12}{Style.RESET_ALL}  "
            f"{Fore.MAGENTA}ETA {eta:<8}{Style.RESET_ALL}  "
            f"{Fore.WHITE}{downloaded} / {total}{Style.RESET_ALL}"
        )
        sys.stdout.write(line)
        sys.stdout.flush()

    elif d['status'] == 'finished':
        print(f"\n  {Fore.GREEN}✔  Download complete → {Style.BRIGHT}{d.get('filename','')}{Style.RESET_ALL}")

    elif d['status'] == 'error':
        print(f"\n  {Fore.RED}✘  Error downloading: {d.get('filename','')}{Style.RESET_ALL}")


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def print_header():
    print(DRACULA_LOGO)

def print_separator():
    print(SEPARATOR)

def print_info(msg):
    print(f"  {Fore.CYAN}ℹ  {Style.RESET_ALL}{msg}")

def print_success(msg):
    print(f"  {Fore.GREEN}✔  {Style.RESET_ALL}{msg}")

def print_error(msg):
    print(f"  {Fore.RED}✘  {Style.RESET_ALL}{msg}")

def print_warn(msg):
    print(f"  {Fore.YELLOW}⚠  {Style.RESET_ALL}{msg}")

def print_section(title):
    print(f"\n  {Fore.MAGENTA}{Style.BRIGHT}{title}{Style.RESET_ALL}")
    print(f"  {Fore.RED}{'─' * 50}{Style.RESET_ALL}")


def get_output_dir():
    """Return the download directory, defaulting to ~/Downloads/Dracula."""
    path = Path.home() / "Downloads" / "Dracula"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


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


# ─────────────────────────────────────────────
#  FETCH VIDEO INFO
# ─────────────────────────────────────────────

def fetch_info(url: str) -> dict | None:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        print_error(f"Could not fetch info: {e}")
        return None


def display_formats(info: dict):
    """Print a neat table of available video formats."""
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

        # colour rows
        if vco == 'none':
            row_color = Fore.YELLOW          # audio only
        elif aco == 'none':
            row_color = Fore.CYAN            # video only
        else:
            row_color = Fore.WHITE           # combined

        print(f"  {row_color}"
              f"{fid:<12} {ext:<6} {str(res):<14} {fps:<6} {vco:<18} {aco:<16} {size_str:>10}"
              f"{Style.RESET_ALL}")

    print(f"\n  {Fore.YELLOW}Legend:{Style.RESET_ALL} "
          f"{Fore.CYAN}Cyan{Style.RESET_ALL}=Video-only  "
          f"{Fore.YELLOW}Yellow{Style.RESET_ALL}=Audio-only  "
          f"{Fore.WHITE}White{Style.RESET_ALL}=Combined")


# ─────────────────────────────────────────────
#  DOWNLOAD FUNCTIONS
# ─────────────────────────────────────────────

def build_base_opts(output_dir: str, extra: dict = None) -> dict:
    template = os.path.join(output_dir, '%(title)s.%(ext)s')
    opts = {
        'outtmpl':          template,
        'progress_hooks':   [progress_hook],
        'quiet':            True,
        'no_warnings':      True,
        'noprogress':       True,
        # ── Resilience against network hiccups ────────────────────
        'retries':             10,
        'fragment_retries':    10,
        'file_access_retries': 5,
        'socket_timeout':      30,
        'http_chunk_size':     10 * 1024 * 1024,  # 10 MB
    }
    if extra:
        opts.update(extra)
    return opts


def download_video(url: str, output_dir: str, format_id: str = None, quality: str = 'best'):
    """Download a single video with optional quality / format selection."""
    print_section("Video Download")
    print_info(f"URL     : {url}")
    print_info(f"Saving  : {output_dir}")

    if format_id:
        fmt = format_id
        print_info(f"Format  : {format_id}")
    else:
        quality_map = {
            '4k'   : 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
            '1440p': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            '720p' : 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            '480p' : 'bestvideo[height<=480]+bestaudio/best[height<=480]',
            '360p' : 'bestvideo[height<=360]+bestaudio/best[height<=360]',
            'best' : 'bestvideo+bestaudio/best',
            'worst': 'worstvideo+worstaudio/worst',
        }
        fmt = quality_map.get(quality, quality_map['best'])
        print_info(f"Quality : {quality}")

    opts = build_base_opts(output_dir, {
        'format': fmt,
        'merge_output_format': 'mp4',
    })

    print_separator()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        print_success("Done!")
    except yt_dlp.utils.DownloadError as e:
        print_error(str(e))
    finally:
        cleanup_leftovers(output_dir)


def download_audio(url: str, output_dir: str, audio_fmt: str = 'mp3', quality: str = '192'):
    """Download audio only."""
    print_section("Audio Download")
    print_info(f"URL     : {url}")
    print_info(f"Format  : {audio_fmt.upper()}")
    print_info(f"Quality : {quality}k")
    print_info(f"Saving  : {output_dir}")

    postprocessors = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': audio_fmt,
        'preferredquality': quality,
    }]

    template = os.path.join(output_dir, '%(title)s.%(ext)s')
    opts = {
        'format':           'bestaudio/best',
        'outtmpl':          template,
        'postprocessors':   postprocessors,
        'progress_hooks':   [progress_hook],
        'quiet':            True,
        'no_warnings':      True,
        'noprogress':       True,
        # ── Resilience against network hiccups ────────────────────
        'retries':             10,
        'fragment_retries':    10,
        'file_access_retries': 5,
        'socket_timeout':      30,
        'http_chunk_size':     10 * 1024 * 1024,  # 10 MB
    }

    print_separator()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        print_success("Done!")
    except yt_dlp.utils.DownloadError as e:
        print_error(str(e))
    finally:
        cleanup_leftovers(output_dir)


def download_playlist(url: str, output_dir: str, quality: str = 'best',
                      audio_only: bool = False, audio_fmt: str = 'mp3',
                      start: int = None, end: int = None):
    """Download a full playlist."""
    print_section("Playlist Download")
    print_info(f"URL       : {url}")
    print_info(f"Saving    : {output_dir}")

    # numbered sub-folder template
    template = os.path.join(output_dir, '%(playlist_title)s',
                            '%(playlist_index)s - %(title)s.%(ext)s')

    quality_map = {
        '4k'   : 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
        '1440p': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720p' : 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480p' : 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        '360p' : 'bestvideo[height<=360]+bestaudio/best[height<=360]',
        'best' : 'bestvideo+bestaudio/best',
        'worst': 'worstvideo+worstaudio/worst',
    }

    opts = {
        'outtmpl':          template,
        'progress_hooks':   [progress_hook],
        'quiet':            True,
        'no_warnings':      True,
        'noprogress':       True,
        'ignoreerrors':     True,
        # ── Resilience against network hiccups ────────────────────
        'retries':             10,
        'fragment_retries':    10,
        'file_access_retries': 5,
        'socket_timeout':      30,
        'http_chunk_size':     10 * 1024 * 1024,  # 10 MB
    }

    if audio_only:
        print_info(f"Mode      : Audio only ({audio_fmt.upper()})")
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_fmt,
            'preferredquality': '192',
        }]
    else:
        print_info(f"Quality   : {quality}")
        opts['format'] = quality_map.get(quality, quality_map['best'])
        opts['merge_output_format'] = 'mp4'

    if start:
        opts['playliststart'] = start
        print_info(f"Start at  : item {start}")
    if end:
        opts['playlistend'] = end
        print_info(f"End at    : item {end}")

    print_separator()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        print_success("Playlist download complete!")
    except yt_dlp.utils.DownloadError as e:
        print_error(str(e))
    finally:
        cleanup_leftovers(output_dir)


# ─────────────────────────────────────────────
#  INTERACTIVE MODE
# ─────────────────────────────────────────────

def prompt(msg, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"  {Fore.CYAN}?{Style.RESET_ALL} {msg}{suffix}: ").strip()
    return val if val else default


def interactive_mode():
    # ── Dependency check every launch ────────────────────────────────
    if _sc:
        _sc.run_checks(verbose=True)

    print_header()
    print_separator()
    print(f"\n  {Fore.MAGENTA}{Style.BRIGHT}Welcome to The Dracula Interactive Mode{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}The dark lord of downloaders rises…{Style.RESET_ALL}\n")

    menu = f"""
  {Fore.RED}{Style.BRIGHT}Choose your fate:{Style.RESET_ALL}

  {Fore.CYAN}[1]{Style.RESET_ALL} Download Video        (with quality selector)
  {Fore.CYAN}[2]{Style.RESET_ALL} Download Audio Only   (mp3/m4a/wav/flac)
  {Fore.CYAN}[3]{Style.RESET_ALL} Download Playlist     (video or audio)
  {Fore.CYAN}[4]{Style.RESET_ALL} List Available Formats
  {Fore.CYAN}[5]{Style.RESET_ALL} Exit

"""
    print(menu)

    choice = prompt("Enter choice", "1")
    output_dir = prompt("Output directory", get_output_dir())

    if choice == '1':
        url = prompt("YouTube URL")
        if not url:
            print_error("No URL provided."); return

        quality_choices = "best / 4k / 1440p / 1080p / 720p / 480p / 360p / worst"
        quality = prompt(f"Quality ({quality_choices})", "best")
        fmt_id = prompt("Specific format ID? (leave blank to use quality)", "")
        download_video(url, output_dir, format_id=fmt_id or None, quality=quality)

    elif choice == '2':
        url = prompt("YouTube URL")
        if not url:
            print_error("No URL provided."); return
        afmt = prompt("Audio format (mp3/m4a/wav/flac/opus)", "mp3")
        aq = prompt("Audio quality kbps (128/192/256/320)", "192")
        download_audio(url, output_dir, audio_fmt=afmt, quality=aq)

    elif choice == '3':
        url = prompt("Playlist URL")
        if not url:
            print_error("No URL provided."); return
        ao = prompt("Audio only? (y/n)", "n").lower() == 'y'
        if ao:
            afmt = prompt("Audio format (mp3/m4a/wav/flac)", "mp3")
            quality = "best"
        else:
            quality_choices = "best / 4k / 1440p / 1080p / 720p / 480p / 360p / worst"
            quality = prompt(f"Quality ({quality_choices})", "720p")
            afmt = "mp3"
        start_item = prompt("Start from item # (leave blank = 1)", "")
        end_item   = prompt("End at item #    (leave blank = all)", "")
        start = int(start_item) if start_item and start_item.isdigit() else None
        end   = int(end_item)   if end_item   and end_item.isdigit()   else None
        download_playlist(url, output_dir, quality=quality,
                          audio_only=ao, audio_fmt=afmt,
                          start=start, end=end)

    elif choice == '4':
        url = prompt("YouTube URL")
        if not url:
            print_error("No URL provided."); return
        print_info("Fetching formats…")
        info = fetch_info(url)
        if info:
            print_info(f"Title : {info.get('title','N/A')}")
            print_info(f"Channel : {info.get('uploader','N/A')}")
            print_info(f"Duration : {info.get('duration_string','N/A')}")
            display_formats(info)

    elif choice == '5':
        print(f"\n  {Fore.RED}🧛 The Dracula sleeps… until next time.{Style.RESET_ALL}\n")
        sys.exit(0)

    else:
        print_error("Invalid choice.")


# ─────────────────────────────────────────────
#  CLI ARGUMENT PARSER
# ─────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog='dracula',
        description='🧛 The Dracula — YouTube Downloader CLI powered by yt-dlp',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python dracula.py                                  # interactive mode
  python dracula.py video -u URL -q 1080p
  python dracula.py audio -u URL -f mp3 -b 320
  python dracula.py playlist -u URL -q 720p
  python dracula.py playlist -u URL --audio-only -f mp3
  python dracula.py formats -u URL
"""
    )

    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')

    sub = parser.add_subparsers(dest='command', metavar='COMMAND')

    # ── video ──
    vp = sub.add_parser('video', help='Download a single video')
    vp.add_argument('-u', '--url',     required=True, help='YouTube video URL')
    vp.add_argument('-q', '--quality', default='best',
                    choices=['best','worst','4k','1440p','1080p','720p','480p','360p'],
                    help='Video quality (default: best)')
    vp.add_argument('-f', '--format-id', default=None,
                    help='Specific yt-dlp format ID (overrides --quality)')
    vp.add_argument('-o', '--output',  default=None, help='Output directory')

    # ── audio ──
    ap = sub.add_parser('audio', help='Download audio only')
    ap.add_argument('-u', '--url',    required=True, help='YouTube video URL')
    ap.add_argument('-f', '--format', default='mp3',
                    choices=['mp3','m4a','wav','flac','opus','aac'],
                    help='Audio format (default: mp3)')
    ap.add_argument('-b', '--bitrate', default='192',
                    choices=['128','192','256','320'],
                    help='Audio bitrate kbps (default: 192)')
    ap.add_argument('-o', '--output', default=None, help='Output directory')

    # ── playlist ──
    pp = sub.add_parser('playlist', help='Download a playlist')
    pp.add_argument('-u', '--url',     required=True, help='YouTube playlist URL')
    pp.add_argument('-q', '--quality', default='720p',
                    choices=['best','worst','4k','1440p','1080p','720p','480p','360p'],
                    help='Video quality (default: 720p)')
    pp.add_argument('--audio-only',   action='store_true', help='Download audio only')
    pp.add_argument('-f', '--format', default='mp3',
                    choices=['mp3','m4a','wav','flac','opus','aac'],
                    help='Audio format when --audio-only (default: mp3)')
    pp.add_argument('--start', type=int, default=None, help='Start at playlist item #')
    pp.add_argument('--end',   type=int, default=None, help='End at playlist item #')
    pp.add_argument('-o', '--output', default=None, help='Output directory')

    # ── formats ──
    fp = sub.add_parser('formats', help='List available formats for a URL')
    fp.add_argument('-u', '--url', required=True, help='YouTube video URL')

    return parser


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = build_parser()

    # ── No arguments → launch the rich TUI ───────────────────────────
    if len(sys.argv) == 1:
        # Run dependency checks silently then hand off to TUI
        if _sc:
            _sc.run_checks(verbose=True)
        if _tui:
            try:
                _tui.run_tui()
            except KeyboardInterrupt:
                print("\n  Goodbye! 🧛")
        else:
            # Fallback to old text interactive mode if TUI failed to load
            interactive_mode()
        return

    args = parser.parse_args()

    # ── Dependency check every launch (CLI mode) ──────────────────────
    if _sc:
        _sc.run_checks(verbose=True)

    # Always print the header for subcommands
    print_header()

    out = args.output if hasattr(args, 'output') and args.output else get_output_dir()

    if args.command == 'video':
        download_video(args.url, out,
                       format_id=args.format_id,
                       quality=args.quality)

    elif args.command == 'audio':
        download_audio(args.url, out,
                       audio_fmt=args.format,
                       quality=args.bitrate)

    elif args.command == 'playlist':
        download_playlist(args.url, out,
                          quality=args.quality,
                          audio_only=args.audio_only,
                          audio_fmt=args.format,
                          start=args.start,
                          end=args.end)

    elif args.command == 'formats':
        print_info("Fetching available formats…")
        info = fetch_info(args.url)
        if info:
            print_info(f"Title    : {info.get('title','N/A')}")
            print_info(f"Channel  : {info.get('uploader','N/A')}")
            print_info(f"Duration : {info.get('duration_string','N/A')}")
            print_info(f"Views    : {info.get('view_count','N/A'):,}" if isinstance(info.get('view_count'), int) else f"Views    : {info.get('view_count','N/A')}")
            display_formats(info)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()

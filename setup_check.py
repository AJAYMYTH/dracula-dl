#!/usr/bin/env python3
"""
setup_check.py — Auto dependency & FFmpeg installer for The Dracula CLI
Runs silently every launch, installs missing pieces automatically.
"""

import os
import sys
import shutil
import subprocess
import importlib
import importlib.util
import platform


# ─────────────────────────────────────────────────────────────
#  Minimal colour helpers (works before colorama is confirmed)
# ─────────────────────────────────────────────────────────────

def _c(code, text):
    """Wrap text in an ANSI escape code (always safe on modern terminals)."""
    return f"\033[{code}m{text}\033[0m"

def _red(t):     return _c("91;1", t)
def _green(t):   return _c("92;1", t)
def _yellow(t):  return _c("93;1", t)
def _cyan(t):    return _c("96;1", t)
def _magenta(t): return _c("95;1", t)
def _white(t):   return _c("97;1", t)
def _dim(t):     return _c("2", t)

OK    = _green("  ✔")
FAIL  = _red("  ✘")
WARN  = _yellow("  ⚠")
INFO  = _cyan("  ℹ")
ARROW = _magenta("  →")


def _print_banner():
    print(_red("  ╔══════════════════════════════════════════════════╗"))
    print(_red("  ║") + _magenta(" 🧛 The Dracula  ·  Dependency Check") + _red("              ║"))
    print(_red("  ╚══════════════════════════════════════════════════╝"))
    print()


# ─────────────────────────────────────────────────────────────
#  Python package checker / installer
# ─────────────────────────────────────────────────────────────

REQUIRED_PACKAGES = {
    "yt_dlp":    "yt-dlp",
    "colorama":  "colorama",
    "rich":      "rich",
    "questionary": "questionary",
}


def _check_python_packages() -> bool:
    """Check all required Python packages; install any that are missing."""
    print(f"{INFO} Checking Python packages…")
    all_ok = True

    for import_name, pip_name in REQUIRED_PACKAGES.items():
        spec = importlib.util.find_spec(import_name)
        if spec is not None:
            print(f"{OK}  {_white(pip_name)} is installed")
        else:
            print(f"{WARN} {_white(pip_name)} not found — installing…")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pip_name, "--quiet"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                # verify after install
                importlib.invalidate_caches()
                if importlib.util.find_spec(import_name):
                    print(f"{OK}  {_white(pip_name)} installed successfully")
                else:
                    print(f"{FAIL} {_white(pip_name)} install failed — please run: pip install {pip_name}")
                    all_ok = False
            except Exception as e:
                print(f"{FAIL} Could not install {pip_name}: {e}")
                all_ok = False

    return all_ok


# ─────────────────────────────────────────────────────────────
#  FFmpeg checker / auto-installer
# ─────────────────────────────────────────────────────────────

def _ffmpeg_in_path() -> bool:
    return shutil.which("ffmpeg") is not None


def _install_ffmpeg_windows() -> bool:
    """Try winget → scoop → chocolatey in order."""

    # 1. winget
    if shutil.which("winget"):
        print(f"{ARROW} Trying winget…")
        try:
            result = subprocess.run(
                ["winget", "install", "--id=Gyan.FFmpeg", "-e",
                 "--accept-package-agreements", "--accept-source-agreements",
                 "--silent"],
                capture_output=True, text=True, timeout=180
            )
            if result.returncode == 0 or "Successfully installed" in result.stdout:
                # winget may put ffmpeg in a new PATH — refresh env
                _refresh_windows_path()
                if _ffmpeg_in_path():
                    return True
                # if still not in PATH, try to locate and add manually
                if _locate_and_add_ffmpeg_windows():
                    return True
            print(f"{WARN} winget returned code {result.returncode}")
        except Exception as e:
            print(f"{WARN} winget failed: {e}")

    # 2. scoop
    if shutil.which("scoop"):
        print(f"{ARROW} Trying scoop…")
        try:
            result = subprocess.run(
                ["scoop", "install", "ffmpeg"],
                capture_output=True, text=True, timeout=180
            )
            _refresh_windows_path()
            if _ffmpeg_in_path():
                return True
        except Exception as e:
            print(f"{WARN} scoop failed: {e}")

    # 3. chocolatey
    if shutil.which("choco"):
        print(f"{ARROW} Trying chocolatey…")
        try:
            result = subprocess.run(
                ["choco", "install", "ffmpeg", "-y"],
                capture_output=True, text=True, timeout=180
            )
            _refresh_windows_path()
            if _ffmpeg_in_path():
                return True
        except Exception as e:
            print(f"{WARN} choco failed: {e}")

    # 4. yt-dlp built-in download as last resort
    return _install_ffmpeg_via_ytdlp()


def _refresh_windows_path():
    """Reload PATH from registry so newly installed tools become visible."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            sys_path = winreg.QueryValueEx(key, "Path")[0]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Environment") as key:
            try:
                usr_path = winreg.QueryValueEx(key, "Path")[0]
            except FileNotFoundError:
                usr_path = ""
        new_path = ";".join(filter(None, [sys_path, usr_path]))
        os.environ["PATH"] = new_path
    except Exception:
        pass


def _locate_and_add_ffmpeg_windows() -> bool:
    """Search common install paths for ffmpeg.exe and add to session PATH."""
    common = [
        os.path.expandvars(r"%ProgramFiles%\ffmpeg\bin"),
        os.path.expandvars(r"%ProgramFiles(x86)%\ffmpeg\bin"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"),
        os.path.expanduser(r"~\scoop\apps\ffmpeg\current\bin"),
        os.path.expanduser(r"~\AppData\Local\Programs\ffmpeg\bin"),
    ]
    for base in common:
        if os.path.isdir(base):
            # recurse one level to handle sub-dirs in WinGet packages
            for root, dirs, files in os.walk(base):
                if "ffmpeg.exe" in files:
                    os.environ["PATH"] = root + os.pathsep + os.environ["PATH"]
                    return shutil.which("ffmpeg") is not None
                # only go one level deep
                if root != base:
                    break
    return False


def _install_ffmpeg_via_ytdlp() -> bool:
    """
    Download a static FFmpeg build using yt-dlp's own downloader helper.
    Works on Windows without any package manager.
    """
    print(f"{ARROW} Attempting FFmpeg download via yt-dlp helper…")
    try:
        import yt_dlp.utils as ydl_utils
        # yt_dlp ≥ 2023 exposes a download helper
        from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
        pp = FFmpegPostProcessor(downloader=None)
        # Check if yt-dlp can locate ffmpeg itself
        pp.check_version()
        return True
    except Exception:
        pass

    # Fallback: download pre-built static binary from GitHub (gyan.dev)
    try:
        import urllib.request, zipfile, io
        url = (
            "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
            "ffmpeg-master-latest-win64-gpl.zip"
        )
        dest_dir = os.path.join(os.path.expanduser("~"), ".dracula", "ffmpeg")
        bin_dir  = os.path.join(dest_dir, "bin")

        if os.path.isfile(os.path.join(bin_dir, "ffmpeg.exe")):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
            return True

        print(f"{ARROW} Downloading FFmpeg static build (~70 MB)…")
        os.makedirs(dest_dir, exist_ok=True)

        with urllib.request.urlopen(url, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            data  = bytearray()
            chunk = 1024 * 256  # 256 KB
            downloaded = 0
            while True:
                block = resp.read(chunk)
                if not block:
                    break
                data.extend(block)
                downloaded += len(block)
                if total:
                    pct = downloaded / total * 100
                    bar = ("█" * int(pct / 3)).ljust(34, "░")
                    print(f"\r  [{_red(bar)}] {pct:5.1f}%", end="", flush=True)
            print()

        print(f"{ARROW} Extracting…")
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for member in zf.infolist():
                # only extract bin/ffmpeg.exe, bin/ffprobe.exe, bin/ffplay.exe
                if "/bin/ff" in member.filename.replace("\\", "/"):
                    member.filename = os.path.basename(member.filename)
                    os.makedirs(bin_dir, exist_ok=True)
                    zf.extract(member, bin_dir)

        os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
        return _ffmpeg_in_path()

    except Exception as e:
        print(f"{FAIL} Could not auto-download FFmpeg: {e}")
        return False


def _install_ffmpeg_macos() -> bool:
    if shutil.which("brew"):
        print(f"{ARROW} Installing via Homebrew…")
        try:
            subprocess.check_call(["brew", "install", "ffmpeg"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  timeout=300)
            return _ffmpeg_in_path()
        except Exception as e:
            print(f"{WARN} brew failed: {e}")
    if shutil.which("port"):
        print(f"{ARROW} Installing via MacPorts…")
        try:
            subprocess.check_call(["sudo", "port", "install", "ffmpeg"],
                                  timeout=300)
            return _ffmpeg_in_path()
        except Exception as e:
            print(f"{WARN} port failed: {e}")
    return False


def _install_ffmpeg_linux() -> bool:
    managers = [
        (["apt-get", "install", "-y", "ffmpeg"],  "apt-get"),
        (["apt",     "install", "-y", "ffmpeg"],  "apt"),
        (["dnf",     "install", "-y", "ffmpeg"],  "dnf"),
        (["yum",     "install", "-y", "ffmpeg"],  "yum"),
        (["pacman",  "-S", "--noconfirm", "ffmpeg"], "pacman"),
        (["zypper",  "install", "-y", "ffmpeg"],  "zypper"),
        (["snap",    "install", "ffmpeg"],         "snap"),
    ]
    for cmd, mgr in managers:
        if shutil.which(cmd[0]):
            print(f"{ARROW} Installing via {mgr}…")
            try:
                full_cmd = ["sudo"] + cmd if os.geteuid() != 0 else cmd
                subprocess.check_call(full_cmd,
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL,
                                      timeout=300)
                if _ffmpeg_in_path():
                    return True
            except Exception as e:
                print(f"{WARN} {mgr} failed: {e}")
    return False


def _check_ffmpeg() -> bool:
    print(f"\n{INFO} Checking FFmpeg…")

    if _ffmpeg_in_path():
        # get version string
        try:
            v = subprocess.check_output(
                ["ffmpeg", "-version"], stderr=subprocess.STDOUT, text=True
            ).splitlines()[0]
            print(f"{OK}  FFmpeg found — {_dim(v)}")
        except Exception:
            print(f"{OK}  FFmpeg found")
        return True

    print(f"{WARN} FFmpeg not found — required for audio extraction & video merging.")
    print(f"{ARROW} Attempting automatic installation…\n")

    system = platform.system()
    ok = False

    if system == "Windows":
        ok = _install_ffmpeg_windows()
    elif system == "Darwin":
        ok = _install_ffmpeg_macos()
    elif system == "Linux":
        ok = _install_ffmpeg_linux()
    else:
        print(f"{FAIL} Unsupported OS: {system}. Please install FFmpeg manually.")
        return False

    if ok:
        try:
            v = subprocess.check_output(
                ["ffmpeg", "-version"], stderr=subprocess.STDOUT, text=True
            ).splitlines()[0]
            print(f"\n{OK}  FFmpeg installed successfully — {_dim(v)}")
        except Exception:
            print(f"\n{OK}  FFmpeg installed successfully")
        return True
    else:
        print(f"\n{FAIL} Could not install FFmpeg automatically.")
        print(f"  {_yellow('Please install FFmpeg manually:')}")
        if system == "Windows":
            print(f"  {_dim('https://www.gyan.dev/ffmpeg/builds/')} or run:")
            print(f"  {_cyan('winget install --id=Gyan.FFmpeg -e')}")
        elif system == "Darwin":
            print(f"  {_cyan('brew install ffmpeg')}")
        else:
            print(f"  {_cyan('sudo apt install ffmpeg')} (Ubuntu/Debian)")
        return False


# ─────────────────────────────────────────────────────────────
#  yt-dlp version check (auto-update prompt)
# ─────────────────────────────────────────────────────────────

def _check_ytdlp_version():
    try:
        import yt_dlp.version as ytv
        ver = getattr(ytv, "__version__", "unknown")
        print(f"\n{INFO} yt-dlp version: {_dim(ver)}")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
#  PUBLIC ENTRY POINT — called from dracula.py at startup
# ─────────────────────────────────────────────────────────────

def run_checks(verbose: bool = True) -> bool:
    """
    Run all dependency checks.
    Returns True if everything is ready, False if critical deps are missing.
    """
    if verbose:
        _print_banner()

    py_ok  = _check_python_packages()
    ff_ok  = _check_ffmpeg()

    if verbose:
        _check_ytdlp_version()
        print()
        print(_red("  ═" * 30))
        if py_ok and ff_ok:
            print(f"\n{OK}  {_green('All systems go!')} 🧛 The Dracula rises…\n")
        else:
            missing = []
            if not py_ok: missing.append("Python packages")
            if not ff_ok: missing.append("FFmpeg")
            print(f"\n{WARN}  Some dependencies missing: {', '.join(missing)}")
            print(f"   Downloads may be limited. See messages above.\n")
        print(_red("  ═" * 30))
        print()

    return py_ok  # allow running even without ffmpeg (video-only streams still work)


if __name__ == "__main__":
    run_checks(verbose=True)

"""
config.py — Configuration file manager for The Dracula CLI & TUI.
Stores settings in ~/.config/dracula/config.toml
"""

import os
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

CONFIG_DIR = Path.home() / ".config" / "dracula"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = {
    "output_dir": str(Path.home() / "Downloads" / "Dracula"),
    "default_quality": "720p",
    "default_audio_format": "mp3",
    "default_audio_bitrate": "192",
}


def get_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> dict:
    """Load configuration from config.toml, returning defaults for missing keys."""
    config = DEFAULT_CONFIG.copy()
    if not CONFIG_FILE.exists():
        return config

    try:
        if tomllib:
            with open(CONFIG_FILE, "rb") as f:
                data = tomllib.load(f)
                if isinstance(data, dict):
                    settings = data.get("settings", data)
                    for k, v in settings.items():
                        if k in config:
                            config[k] = str(v)
        else:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"\'')
                        if k in config:
                            config[k] = v
    except Exception as e:
        log_debug_silent(f"Failed to load config from {CONFIG_FILE}: {e}")

    if "output_dir" in config:
        config["output_dir"] = os.path.normpath(config["output_dir"])

    return config


def save_config(new_config: dict) -> bool:
    """Save updated settings dictionary to config.toml."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        merged = DEFAULT_CONFIG.copy()
        merged.update({k: str(v) for k, v in new_config.items() if k in DEFAULT_CONFIG})

        # Normalize path with forward slashes to avoid TOML invalid escape sequences on Windows
        clean_dir = str(Path(merged["output_dir"])).replace("\\", "/")

        content = [
            "# 🧛 The Dracula Downloader Configuration",
            "[settings]",
            f'output_dir = "{clean_dir}"',
            f'default_quality = "{merged["default_quality"]}"',
            f'default_audio_format = "{merged["default_audio_format"]}"',
            f'default_audio_bitrate = "{merged["default_audio_bitrate"]}"',
            "",
        ]
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        return True
    except Exception as e:
        log_debug_silent(f"Failed to save config to {CONFIG_FILE}: {e}")
        return False


def log_debug_silent(msg: str):
    try:
        debug_log = CONFIG_DIR / "debug.log"
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(debug_log, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass

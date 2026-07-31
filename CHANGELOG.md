# Changelog

All notable changes to **The Dracula YouTube Downloader (`dracula-dl`)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.3] - 2026-07-31

### 🐛 Bug Fixes
* **Subtitle Embedding Fixed**: Fixed critical bug where `opts.update(extra)` overwrote the subtitle/thumbnail postprocessors list, causing `FFmpegEmbedSubtitle` and `EmbedThumbnail` to be silently dropped.
* **Subtitle Format Conversion**: Added `FFmpegSubtitlesConvertor` (to srt) before `FFmpegEmbedSubtitle` and set `subtitlesformat` to `srt/ass/best` for reliable MP4/MKV embedding. Previously, vtt/json3 subs caused silent embedding failures.
* **`--embed-subs` Without `--subs`**: Using `--embed-subs` alone now auto-enables auto-generated subtitle download instead of silently doing nothing.
* **TUI Auto-Generated Subtitles**: Added "Include auto-generated subtitles?" prompt and `writeautomaticsub` support to the TUI, so users get subtitles even when no manual subs are available.

---

## [1.1.2] - 2026-07-28

### 🐛 Bug Fixes & Improvements
* **Config Preference Persistence**: Fixed Windows TOML path escape decoding errors (`TOMLDecodeError`) when saving `output_dir` in `config.toml`.
* **Prompt Defaults**: Integrated saved user preferences as default pre-selected options in TUI prompts.
* **Red & Black Shimmer Logo**: Added CSS text shimmer animation (`.dracula-logo-shimmer`) to Dracula brand logo on documentation site and enhanced ASCII logo styling in TUI.
* **Automated Test Suite**: Added complete unit test suite in `tests/test_dracula.py`.

---

## [1.1.1] - 2026-07-28

### ⚡ Improvements
* **Default TUI Launcher**: Running `dracula` without arguments now launches the Rich + Questionary interactive TUI directly instead of falling back to text prompt mode.

---

## [1.1.0] - 2026-07-28

### 🚀 New Features

* **Persistent TOML Configuration Manager (`dracula_dl/config.py`)**:
  * Settings automatically persist in `~/.config/dracula/config.toml`.
  * Customizable defaults for download folder (`output_dir`), video quality (`default_quality`), audio format (`default_audio_format`), and bitrate (`default_audio_bitrate`).
  * New CLI command: `dracula config [--show] [--set KEY=VALUE] [--reset]`.

* **Download History & Debug Logging (`dracula_dl/history.py`)**:
  * Every completed download is recorded in structured JSONL format at `~/.config/dracula/history.jsonl`.
  * Silent error diagnostics and debugging messages captured at `~/.config/dracula/debug.log`.
  * New CLI command: `dracula history [--limit N] [--clear] [--search QUERY]`.

* **Batch URL Downloads**:
  * Download multiple URLs in a single command using `--batch-file <path_to_urls.txt>`.
  * Support for pasting multiple newline-separated URLs directly in CLI and TUI prompts.

* **Subtitles & Thumbnail Embedding**:
  * New CLI options `--subtitles` / `--sub-lang` (e.g. `--sub-lang en,es`) to download subtitles.
  * Embed subtitles directly into video containers using `--embed-subs`.
  * Extract cover artwork with `--thumbnail` or embed album art directly into MP3/M4A/MKV files with `--embed-thumbnail`.

* **Enhanced Interactive TUI (`dracula_dl/tui.py`)**:
  * Interactive format browser displaying raw streams with codec, resolution, and estimated file size.
  * Integrated System Status Bar verifying active FFmpeg installation, yt-dlp engine version, and download paths.
  * Dedicated interactive screens for Settings management, Download History viewing, and Batch operations.

### ⚡ Improvements & Code Quality

* **Modular Architecture**: Split core functionality into clean, testable submodules (`cli.py`, `tui.py`, `config.py`, `history.py`).
* **Resilient Dependency Fallbacks**: Graceful fallback to basic terminal formatting if `rich` or `colorama` are not available in the environment.
* **Progress Bar Precision**: Upgraded transfer progress displays with real-time speed, ETA, and exact byte counts using `rich.progress`.

### 🐛 Bug Fixes

* Resolved path creation crashes on Windows systems when download directory doesn't exist.
* Fixed format table rendering errors when processing audio-only streams lacking spatial width/height parameters.
* Handled keyboard interrupt (`Ctrl+C`) cleanly during batch operations to prevent leftover temporary files.

---

## [1.0.4] - 2026-01-15

* **Initial Stable Release**:
  * Core CLI downloader supporting single videos, playlists, and audio extraction.
  * First version of interactive Questionary TUI.
  * Basic PyPI package configuration with Hatchling build backend.

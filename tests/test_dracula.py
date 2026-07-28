"""
tests/test_dracula.py — Automated test suite for The Dracula YouTube Downloader.
Tests configuration persistence, history logging, CLI parsing, and TUI components.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add repository root to path
REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from dracula_dl.config import load_config, save_config, DEFAULT_CONFIG, get_config_dir
from dracula_dl.history import add_history_entry, read_history, log_debug
from dracula_dl import cli
from dracula_dl import tui


class TestDraculaConfig(unittest.TestCase):
    """Test suite for configuration manager (dracula_dl.config)."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.patcher_config_dir = patch("dracula_dl.config.CONFIG_DIR", Path(self.tmp_dir.name))
        self.patcher_config_file = patch("dracula_dl.config.CONFIG_FILE", Path(self.tmp_dir.name) / "config.toml")
        self.patcher_config_dir.start()
        self.patcher_config_file.start()

    def tearDown(self):
        self.patcher_config_file.stop()
        self.patcher_config_dir.stop()
        self.tmp_dir.cleanup()

    def test_default_config(self):
        """Test default config when no config.toml exists."""
        cfg = load_config()
        self.assertIn("output_dir", cfg)
        self.assertEqual(cfg["default_quality"], "720p")
        self.assertEqual(cfg["default_audio_format"], "mp3")

    def test_save_and_load_preferences(self):
        """Test saving updated preferences and loading them back correctly."""
        new_settings = {
            "output_dir": os.path.join(self.tmp_dir.name, "MyDownloads"),
            "default_quality": "1080p",
            "default_audio_format": "flac",
            "default_audio_bitrate": "320",
        }
        success = save_config(new_settings)
        self.assertTrue(success, "save_config returned False")

        loaded = load_config()
        self.assertEqual(loaded["default_quality"], "1080p")
        self.assertEqual(loaded["default_audio_format"], "flac")
        self.assertEqual(loaded["default_audio_bitrate"], "320")
        self.assertTrue(loaded["output_dir"].endswith("MyDownloads"))


class TestDraculaHistory(unittest.TestCase):
    """Test suite for download history & debug logging (dracula_dl.history)."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.patcher_hist_dir = patch("dracula_dl.history.CONFIG_DIR", Path(self.tmp_dir.name))
        self.patcher_hist_file = patch("dracula_dl.history.HISTORY_FILE", Path(self.tmp_dir.name) / "history.jsonl")
        self.patcher_debug_file = patch("dracula_dl.history.DEBUG_FILE", Path(self.tmp_dir.name) / "debug.log")
        self.patcher_hist_dir.start()
        self.patcher_hist_file.start()
        self.patcher_debug_file.start()

    def tearDown(self):
        self.patcher_debug_file.stop()
        self.patcher_hist_file.stop()
        self.patcher_hist_dir.stop()
        self.tmp_dir.cleanup()

    def test_add_and_read_history(self):
        """Test adding download records and reading history."""
        add_history_entry("Test Video 1", "https://youtube.com/watch?v=test1", "mp4", "1080p", "/path/out1.mp4")
        add_history_entry("Test Video 2", "https://youtube.com/watch?v=test2", "mp3", "320k", "/path/out2.mp3")

        entries, total = read_history(limit=10)
        self.assertEqual(total, 2)
        self.assertEqual(len(entries), 2)
        # Most recent should come first
        self.assertEqual(entries[0]["title"], "Test Video 2")
        self.assertEqual(entries[1]["title"], "Test Video 1")

    def test_log_debug(self):
        """Test writing to debug.log."""
        log_debug("Test debug message", Exception("Sample Error"))
        debug_path = Path(self.tmp_dir.name) / "debug.log"
        self.assertTrue(debug_path.exists())
        content = debug_path.read_text(encoding="utf-8")
        self.assertIn("Test debug message", content)
        self.assertIn("Sample Error", content)


class TestDraculaCLI(unittest.TestCase):
    """Test suite for CLI argument parser and commands."""

    @patch("sys.argv", ["dracula", "video", "-u", "https://youtu.be/test", "-q", "1080p"])
    @patch("dracula_dl.cli.download_video")
    def test_cli_video_command(self, mock_download_video):
        """Test parsing 'dracula video' command."""
        cli.main()
        mock_download_video.assert_called_once()

    @patch("sys.argv", ["dracula", "audio", "-u", "https://youtu.be/test", "-f", "flac"])
    @patch("dracula_dl.cli.download_audio")
    def test_cli_audio_command(self, mock_download_audio):
        """Test parsing 'dracula audio' command."""
        cli.main()
        mock_download_audio.assert_called_once()

    @patch("sys.argv", ["dracula"])
    @patch("dracula_dl.tui.launch_tui")
    def test_cli_default_tui_launch(self, mock_launch_tui):
        """Test running 'dracula' without subcommands launches TUI."""
        cli.main()
        mock_launch_tui.assert_called_once()


class TestDraculaTUI(unittest.TestCase):
    """Test suite for TUI helper functions."""

    def test_render_logo(self):
        """Test rendering Rich logo panel."""
        panel = tui.render_logo()
        self.assertIsNotNone(panel)

    def test_quality_fmt_mapping(self):
        """Test video quality format mapping in TUI."""
        self.assertIn("height<=1080", tui._quality_fmt("1080p"))
        self.assertIn("height<=2160", tui._quality_fmt("4K"))


if __name__ == "__main__":
    unittest.main()

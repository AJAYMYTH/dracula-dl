#!/usr/bin/env python3
"""
tui.py — Standalone launcher wrapper for The Dracula Rich TUI
Imports and executes launch_tui() from dracula_dl.tui.
"""
import sys
from pathlib import Path

# Ensure root directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from dracula_dl.tui import *
from dracula_dl.tui import launch_tui

if __name__ == "__main__":
    launch_tui()

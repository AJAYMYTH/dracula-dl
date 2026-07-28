#!/usr/bin/env python3
"""
dracula.py — Standalone launcher wrapper for The Dracula CLI
Imports and executes main() from dracula_dl.cli.
"""
import sys
from pathlib import Path

# Ensure root directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from dracula_dl.cli import main

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
setup_check.py — Standalone launcher wrapper for setup checks
Imports and executes run_checks() from dracula_dl.setup_check.
"""
import sys
from pathlib import Path

# Ensure root directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from dracula_dl.setup_check import *
from dracula_dl.setup_check import run_checks

if __name__ == "__main__":
    run_checks(verbose=True)

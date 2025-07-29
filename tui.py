#!/usr/bin/env python3
"""TUI Entry Point for Animal Well Flute - Cosmic Edition"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.tui.app import run_tui


def main():
    """Main entry point for the TUI application"""
    try:
        return run_tui()
    except KeyboardInterrupt:
        print("\n👋 Farewell, cosmic musician!")
        return 130
    except Exception as e:
        print(f"💥 Cosmic disturbance detected: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
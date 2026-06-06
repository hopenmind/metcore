"""Frozen-app entry point for the Hope 'n Mind desktop GUI."""
import sys


def main() -> int:
    from metcore_gui.__main__ import main as gui_main
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())

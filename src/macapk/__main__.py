#!/usr/bin/env python3
"""MacAPK — Main entry point for bundled app."""
import sys
import os
import subprocess
import threading
import time
import webbrowser

# When running from PyInstaller bundle
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
    # Set UI_DIR to bundled resources
    os.environ['MACAPK_UI_DIR'] = os.path.join(BUNDLE_DIR, 'ui')
    # Add bundle dir to path for imports
    sys.path.insert(0, BUNDLE_DIR)

from macapk.api.server import run_server


def open_browser(url):
    """Open browser after a short delay."""
    time.sleep(2)
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='MacAPK — De keuring voor je Mac')
    parser.add_argument('--host', default='127.0.0.1', help='Host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8899, help='Port (default: 8899)')
    parser.add_argument('--no-auto', action='store_true', help='Geen automatische keuring')
    parser.add_argument('--no-browser', action='store_true', help='Geen browser openen')
    args = parser.parse_args()

    if not args.no_browser:
        threading.Thread(target=open_browser, args=(f'http://{args.host}:{args.port}',), daemon=True).start()

    run_server(host=args.host, port=args.port, auto=not args.no_auto)
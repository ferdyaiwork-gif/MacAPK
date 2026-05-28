#!/usr/bin/env python3
"""MacAPK — Local HTTP API server for the dashboard UI."""

import json
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from macapk.engine import run_check, calculate_score
from macapk.repair import get_available_repairs, run_repair, run_all_repairs, run_toggle, get_toggles
from macapk.storage.history import HistoryDB

# Global state
_cached_result = None
_cached_lock = threading.Lock()
_auto_thread = None
_auto_running = False
AUTO_INTERVAL = 300  # 5 minutes

DB_PATH = os.path.expanduser('~/.macapk/history.db')
# UI directory: check multiple locations
_SCRIPT_DIR = Path(__file__).resolve().parent
_env_ui = os.environ.get('MACAPK_UI_DIR')
_candidate_dirs = [
    Path(_env_ui) if _env_ui else None,              # env override (PyInstaller)
    _SCRIPT_DIR.parent.parent / 'ui',                 # development: src/macapk/api/../../ui = ui/
    _SCRIPT_DIR.parent / 'ui',                        # bundled: Resources/ui/
    Path(sys._MEIPASS) / 'ui' if getattr(sys, '_MEIPASS', None) else None,  # PyInstaller
    Path(os.getcwd()) / 'ui',                         # cwd/ui
    Path('/Applications/MacAPK.app/Contents/Resources/ui'),  # installed
]
_candidate_dirs = [d for d in _candidate_dirs if d is not None]
UI_DIR = str(next((d for d in _candidate_dirs if d.exists()), _candidate_dirs[0]))


class MacAPKHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MacAPK dashboard."""

    def log_message(self, fmt, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data, default=str, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type='text/html'):
        if not os.path.exists(filepath):
            self.send_error(404)
            return
        with open(filepath, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', f'{content_type}; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        global _cached_result
        path = self.path.split('?')[0]

        if path == '/' or path == '/index.html':
            self._send_file(os.path.join(UI_DIR, 'index.html'), 'text/html')
        elif path == '/api/status':
            with _cached_lock:
                self._send_json(_cached_result or {'status': 'no_data', 'message': 'Geen keuring beschikbaar. Voer een keuring uit.'})
        elif path == '/api/history':
            hours = 24
            try:
                qs = self.path.split('?', 1)
                if len(qs) > 1:
                    for param in qs[1].split('&'):
                        if param.startswith('hours='):
                            hours = int(param.split('=')[1])
            except (ValueError, IndexError):
                pass
            db = HistoryDB(DB_PATH)
            checks = db.get_last(hours=hours, limit=500)
            trends = {'status': 'no_data'} if len(checks) < 2 else {}
            if len(checks) >= 2:
                # Calculate trend per module
                from macapk.analyzers.diagnoser import analyze_trends
                trends = analyze_trends(checks)
            chart_data = [{'timestamp': c['timestamp'], 'overall_score': c.get('overall_score', c.get('scores', {}).get('overall', 0))} for c in checks]
            self._send_json({'checks': chart_data, 'trends': trends, 'count': len(checks)})
        elif path == '/api/check':
            # GET /api/check returns latest
            with _cached_lock:
                self._send_json(_cached_result or {'status': 'no_data'})
        elif path == '/api/repairs':
            # GET /api/repairs — list available toggles/repairs based on latest check
            with _cached_lock:
                toggles = get_available_repairs(_cached_result or {})
            self._send_json({'repairs': toggles})
        elif path == '/api/toggles':
            # GET /api/toggles — list all toggles with current state
            with _cached_lock:
                toggles = get_toggles(_cached_result or {})
            self._send_json({'toggles': toggles})
        else:
            # Serve static files from UI dir
            filepath = os.path.join(UI_DIR, path.lstrip('/'))
            if os.path.exists(filepath) and not os.path.isdir(filepath):
                ext = os.path.splitext(filepath)[1]
                ct = {'.css': 'text/css', '.js': 'application/javascript', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon'}.get(ext, 'application/octet-stream')
                self._send_file(filepath, ct)
            else:
                self.send_error(404)

    def do_POST(self):
        global _cached_result
        if self.path == '/api/check':
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len) if content_len else b''
            try:
                result = run_check()
                with _cached_lock:
                    _cached_result = result
                # Save to history
                db = HistoryDB(DB_PATH)
                db.save(result)
                self._send_json(result)
            except Exception as e:
                self._send_json({'error': str(e), 'status': 'error'}, 500)
        elif self.path == '/api/repair':
            # POST /api/repair — run a specific repair, toggle, or all repairs
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len) if content_len else b''
            try:
                params = json.loads(body) if body else {}
                repair_id = params.get('id', '')
                action = params.get('action', 'on')  # 'on', 'off', or 'run'
                
                with _cached_lock:
                    check_data = _cached_result or {}
                
                if repair_id == 'all':
                    results = run_all_repairs(check_data)
                    new_check = run_check()
                    with _cached_lock:
                        _cached_result = new_check
                    db = HistoryDB(DB_PATH)
                    db.save(new_check)
                    self._send_json({'repairs': results, 'new_check': new_check})
                elif repair_id:
                    # Check if it's a toggle or one-time action
                    from macapk.repair import TOGGLES
                    toggle = TOGGLES.get(repair_id)
                    if toggle and not toggle.get('is_action', False):
                        # It's a real toggle — use 'on' or 'off'
                        result = run_toggle(repair_id, action, check_data)
                    else:
                        # It's a one-time action
                        result = run_repair(repair_id, check_data)
                    # Re-run check after action
                    new_check = run_check()
                    with _cached_lock:
                        _cached_result = new_check
                    db = HistoryDB(DB_PATH)
                    db.save(new_check)
                    self._send_json({'repair': result, 'new_check': new_check})
                else:
                    self._send_json({'error': 'Geen reparatie-ID opgegeven'}, 400)
            except Exception as e:
                self._send_json({'error': str(e)}, 500)
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def auto_check_loop():
    """Background thread that periodically runs health checks."""
    global _cached_result, _auto_running
    while _auto_running:
        try:
            result = run_check()
            with _cached_lock:
                _cached_result = result
            db = HistoryDB(DB_PATH)
            db.save(result)
        except Exception as e:
            print(f'Auto-check error: {e}', file=sys.stderr)
        for _ in range(AUTO_INTERVAL):
            if not _auto_running:
                return
            time.sleep(1)


def run_server(host='127.0.0.1', port=8899, auto=True):
    """Start the MacAPK HTTP server."""
    global _auto_thread, _auto_running

    # Ensure DB dir exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Run initial check
    print('MacAPK — Eerste keuring uitvoeren...')
    try:
        result = run_check()
        global _cached_result
        with _cached_lock:
            _cached_result = result
        db = HistoryDB(DB_PATH)
        db.save(result)
        print(f'Keuring voltooid: {result["scores"]["overall"]}/100 ({result["scores"]["overall_status"]})')
    except Exception as e:
        print(f'Fout bij eerste keuring: {e}', file=sys.stderr)

    # Start auto-check background thread
    if auto:
        _auto_running = True
        _auto_thread = threading.Thread(target=auto_check_loop, daemon=True)
        _auto_thread.start()

    # Start HTTP server
    server = HTTPServer((host, port), MacAPKHandler)
    print(f'MacAPK dashboard draait op http://{host}:{port}')
    print(f'Druk Ctrl+C om te stoppen')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nMacAPK gestopt.')
        _auto_running = False
        server.server_close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='MacAPK — De keuring voor je Mac')
    parser.add_argument('--host', default='127.0.0.1', help='Host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8899, help='Port (default: 8899)')
    parser.add_argument('--no-auto', action='store_true', help='Disable auto-check')
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, auto=not args.no_auto)
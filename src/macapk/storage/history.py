#!/usr/bin/env python3
"""MacAPK History Storage — SQLite database for trend data."""

import os
import json
import sqlite3
from datetime import datetime, timedelta


class HistoryDB:
    """Store and retrieve time-series health check data."""

    def __init__(self, db_path='~/.macapk/history.db'):
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                overall_score REAL,
                overall_status TEXT,
                raw_json TEXT,
                scores_json TEXT
            );
            CREATE TABLE IF NOT EXISTS module_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id INTEGER,
                module TEXT NOT NULL,
                score REAL,
                status TEXT,
                FOREIGN KEY (check_id) REFERENCES checks(id)
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                module TEXT,
                severity TEXT,
                message TEXT,
                acknowledged INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_checks_ts ON checks(timestamp);
            CREATE INDEX IF NOT EXISTS idx_module_scores_check ON module_scores(check_id);
        ''')
        self.conn.commit()

    def save(self, result):
        """Save a check result to history."""
        ts = result.get('timestamp', datetime.now().isoformat())
        scores = result.get('scores', {})
        overall = scores.get('overall', 0)
        status = scores.get('overall_status', 'unknown')

        cur = self.conn.execute(
            'INSERT INTO checks (timestamp, overall_score, overall_status, raw_json, scores_json) VALUES (?,?,?,?,?)',
            (ts, overall, status, json.dumps(result.get('raw', {}), default=str),
             json.dumps(scores, default=str))
        )
        check_id = cur.lastrowid

        for mod, info in scores.get('modules', {}).items():
            self.conn.execute(
                'INSERT INTO module_scores (check_id, module, score, status) VALUES (?,?,?,?)',
                (check_id, mod, info.get('score', 0), info.get('status', 'unknown'))
            )

        self.conn.commit()

        # Auto-cleanup: keep last 7 days at hourly granularity, older at daily
        self._cleanup()
        return check_id

    def get_last(self, hours=24, limit=500):
        """Get check results from the last N hours."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        rows = self.conn.execute(
            'SELECT id, timestamp, overall_score, overall_status FROM checks WHERE timestamp > ? ORDER BY timestamp LIMIT ?',
            (since, limit)
        ).fetchall()
        result = []
        for row in rows:
            modules = self.conn.execute(
                'SELECT module, score, status FROM module_scores WHERE check_id = ?',
                (row['id'],)
            ).fetchall()
            result.append({
                'timestamp': row['timestamp'],
                'overall_score': row['overall_score'],
                'overall_status': row['overall_status'],
                'modules': {m['module']: {'score': m['score'], 'status': m['status']} for m in modules},
            })
        return result

    def _cleanup(self):
        """Remove old data: keep hourly for 7 days, daily for 30 days, beyond that remove."""
        now = datetime.now()
        # Remove entries older than 30 days
        cutoff_30d = (now - timedelta(days=30)).isoformat()
        ids_to_del = self.conn.execute(
            'SELECT id FROM checks WHERE timestamp < ?', (cutoff_30d,)
        ).fetchall()
        for row in ids_to_del:
            self.conn.execute('DELETE FROM module_scores WHERE check_id = ?', (row['id'],))
        self.conn.execute('DELETE FROM checks WHERE timestamp < ?', (cutoff_30d,))
        self.conn.commit()

    def add_alert(self, module, severity, message):
        """Add an alert."""
        self.conn.execute(
            'INSERT INTO alerts (timestamp, module, severity, message) VALUES (?,?,?,?)',
            (datetime.now().isoformat(), module, severity, message)
        )
        self.conn.commit()

    def get_alerts(self, acknowledged=False):
        """Get alerts."""
        rows = self.conn.execute(
            'SELECT * FROM alerts WHERE acknowledged = ? ORDER BY timestamp DESC',
            (1 if acknowledged else 0,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        """Close the database connection."""
        self.conn.close()
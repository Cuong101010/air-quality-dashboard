"""
database.py - SQLite module for Air Quality Dashboard
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'airquality.db')


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            pm25 REAL NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            pressure REAL NOT NULL,
            uv REAL NOT NULL,
            date_str TEXT,
            time_str TEXT
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_data(timestamp)
    ''')
    conn.commit()
    conn.close()


def insert_data(pm25, temperature, humidity, pressure, uv, date_str=None, time_str=None):
    """Insert a new sensor reading."""
    conn = get_db()
    conn.execute(
        '''INSERT INTO sensor_data (pm25, temperature, humidity, pressure, uv, date_str, time_str)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (pm25, temperature, humidity, pressure, uv, date_str, time_str)
    )
    conn.commit()
    conn.close()


def get_latest():
    """Get the most recent reading."""
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM sensor_data ORDER BY id DESC LIMIT 1'
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_data(hours=24, limit=2000):
    """Get data from the last N hours."""
    conn = get_db()
    since = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    rows = conn.execute(
        '''SELECT * FROM sensor_data
           WHERE timestamp >= ?
           ORDER BY timestamp ASC
           LIMIT ?''',
        (since, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats(hours=24):
    """Get min/max/avg stats for the last N hours."""
    conn = get_db()
    since = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    row = conn.execute(
        '''SELECT
               COUNT(*) as count,
               AVG(pm25) as avg_pm25, MIN(pm25) as min_pm25, MAX(pm25) as max_pm25,
               AVG(temperature) as avg_temp, MIN(temperature) as min_temp, MAX(temperature) as max_temp,
               AVG(humidity) as avg_hum, MIN(humidity) as min_hum, MAX(humidity) as max_hum,
               AVG(pressure) as avg_pres, MIN(pressure) as min_pres, MAX(pressure) as max_pres,
               AVG(uv) as avg_uv, MIN(uv) as min_uv, MAX(uv) as max_uv
           FROM sensor_data
           WHERE timestamp >= ?''',
        (since,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_row_count():
    """Get total number of rows."""
    conn = get_db()
    row = conn.execute('SELECT COUNT(*) as count FROM sensor_data').fetchone()
    conn.close()
    return row['count'] if row else 0

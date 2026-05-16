"""
database.py - PostgreSQL module for Air Quality Dashboard
Uses Neon.tech cloud database for persistent data storage.
"""
import psycopg2
import psycopg2.extras
import os
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://neondb_owner:npg_LveS4FVoGZE0@ep-polished-king-aogjlvko.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'
)


def get_db():
    """Get a database connection."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT NOW(),
            pm25 DOUBLE PRECISION NOT NULL,
            temperature DOUBLE PRECISION NOT NULL,
            humidity DOUBLE PRECISION NOT NULL,
            pressure DOUBLE PRECISION NOT NULL,
            uv DOUBLE PRECISION NOT NULL,
            date_str TEXT,
            time_str TEXT
        )
    ''')
    # Create index if not exists
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_data(timestamp)
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT NOW(),
            pred_time TIMESTAMP NOT NULL,
            target_period TEXT NOT NULL,
            pm25 DOUBLE PRECISION,
            temperature DOUBLE PRECISION,
            humidity DOUBLE PRECISION,
            pressure DOUBLE PRECISION,
            uv DOUBLE PRECISION,
            weather TEXT
        )
    ''')
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_pred_timestamp ON predictions(timestamp)
    ''')
    conn.commit()
    cur.close()
    conn.close()


def insert_data(pm25, temperature, humidity, pressure, uv, date_str=None, time_str=None):
    """Insert a new sensor reading."""
    conn = get_db()
    cur = conn.cursor()
    vn_time = (datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute(
        '''INSERT INTO sensor_data (timestamp, pm25, temperature, humidity, pressure, uv, date_str, time_str)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
        (vn_time, pm25, temperature, humidity, pressure, uv, date_str, time_str)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_latest():
    """Get the most recent reading."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM sensor_data ORDER BY id DESC LIMIT 1')
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        result = dict(row)
        # Convert timestamp to string for JSON serialization
        if isinstance(result.get('timestamp'), datetime):
            result['timestamp'] = result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return result
    return None


def get_data(hours=24, limit=2000):
    """Get data from the last N hours."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    vn_now = datetime.utcnow() + timedelta(hours=7)
    since = (vn_now - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute(
        '''SELECT * FROM sensor_data
           WHERE timestamp >= %s
           ORDER BY timestamp ASC
           LIMIT %s''',
        (since, limit)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get('timestamp'), datetime):
            d['timestamp'] = d['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        results.append(d)
    return results


def get_stats(hours=24):
    """Get min/max/avg stats for the last N hours."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    vn_now = datetime.utcnow() + timedelta(hours=7)
    since = (vn_now - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute(
        '''SELECT
               COUNT(*) as count,
               AVG(pm25) as avg_pm25, MIN(pm25) as min_pm25, MAX(pm25) as max_pm25,
               AVG(temperature) as avg_temp, MIN(temperature) as min_temp, MAX(temperature) as max_temp,
               AVG(humidity) as avg_hum, MIN(humidity) as min_hum, MAX(humidity) as max_hum,
               AVG(pressure) as avg_pres, MIN(pressure) as min_pres, MAX(pressure) as max_pres,
               AVG(uv) as avg_uv, MIN(uv) as min_uv, MAX(uv) as max_uv
           FROM sensor_data
           WHERE timestamp >= %s''',
        (since,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        result = dict(row)
        # Convert Decimal types to float for JSON serialization
        for key, value in result.items():
            if value is not None and not isinstance(value, (int, float, str)):
                try:
                    result[key] = float(value)
                except (ValueError, TypeError):
                    pass
        return result
    return {}


def get_row_count():
    """Get total number of rows."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as count FROM sensor_data')
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else 0


def get_data_range(start_date, end_date):
    """Get data between two dates (format YYYY-MM-DD)."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # Add time bounds to include the entire end_date
    start = f"{start_date} 00:00:00"
    end = f"{end_date} 23:59:59"
    cur.execute(
        '''SELECT * FROM sensor_data
           WHERE timestamp >= %s AND timestamp <= %s
           ORDER BY timestamp ASC''',
        (start, end)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get('timestamp'), datetime):
            d['timestamp'] = d['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        results.append(d)
    return results


def insert_prediction(pred_time, target_period, pm25, temperature, humidity, pressure, uv, weather):
    """Insert a new AI prediction."""
    conn = get_db()
    cur = conn.cursor()
    vn_time = (datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute(
        '''INSERT INTO predictions (timestamp, pred_time, target_period, pm25, temperature, humidity, pressure, uv, weather)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
        (vn_time, pred_time, target_period, pm25, temperature, humidity, pressure, uv, weather)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_predictions_range(start_date, end_date):
    """Get predictions between two dates (format YYYY-MM-DD)."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    start = f"{start_date} 00:00:00"
    end = f"{end_date} 23:59:59"
    cur.execute(
        '''SELECT * FROM predictions
           WHERE timestamp >= %s AND timestamp <= %s
           ORDER BY timestamp ASC''',
        (start, end)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get('timestamp'), datetime):
            d['timestamp'] = d['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(d.get('pred_time'), datetime):
            d['pred_time'] = d['pred_time'].strftime('%Y-%m-%d %H:%M:%S')
        results.append(d)
    return results


def delete_data(hours):
    """Delete sensor data and predictions from the last N hours. If hours=0, delete ALL data."""
    conn = get_db()
    cur = conn.cursor()
    try:
        if hours == 0:
            cur.execute('DELETE FROM sensor_data')
            cur.execute('DELETE FROM predictions')
            deleted_sensor = cur.rowcount
            # rowcount for the second query might overwrite the first, but we just need to execute
        else:
            vn_now = datetime.utcnow() + timedelta(hours=7)
            since = (vn_now - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            
            cur.execute('DELETE FROM sensor_data WHERE timestamp >= %s', (since,))
            cur.execute('DELETE FROM predictions WHERE timestamp >= %s', (since,))
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete error: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()

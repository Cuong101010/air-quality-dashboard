"""
app.py - Flask server for Air Quality Monitoring Dashboard
"""
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import database
import predictor
import os
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Initialize database on startup
database.init_db()

# Models will be loaded lazily on the first AI prediction request to save memory


# ======================== API ENDPOINTS ========================

@app.route('/api/data', methods=['POST'])
def receive_data():
    """Receive sensor data from ESP32 via JSON POST."""
    try:
        data = request.get_json(force=True)

        pm25 = float(data.get('pm25', 0))
        temperature = float(data.get('temperature', 0))
        humidity = float(data.get('humidity', 0))
        pressure = float(data.get('pressure', 0))
        uv = float(data.get('uv', 0))
        date_str = data.get('date', '')
        time_str = data.get('time', '')

        database.insert_data(pm25, temperature, humidity, pressure, uv, date_str, time_str)

        return jsonify({'status': 'ok', 'message': 'Data saved'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/delete', methods=['POST'])
def delete_data():
    """Delete data from the last N hours, or all data if hours=0."""
    try:
        data = request.get_json(force=True)
        hours = int(data.get('hours', 0))
        
        success = database.delete_data(hours)
        if success:
            return jsonify({'status': 'ok', 'message': f'Đã xóa dữ liệu (hours={hours})'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Lỗi khi xóa dữ liệu trong DB'}), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/latest', methods=['GET'])
def get_latest():
    """Get the most recent sensor reading."""
    latest = database.get_latest()
    if latest:
        return jsonify(latest), 200
    return jsonify({'status': 'no_data'}), 200


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get historical data. Query param: hours (default 24)."""
    hours = request.args.get('hours', 24, type=int)
    hours = min(hours, 168)  # max 7 days
    data = database.get_data(hours=hours)
    return jsonify(data), 200


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics for the last N hours."""
    hours = request.args.get('hours', 24, type=int)
    stats = database.get_stats(hours=hours)
    stats['total_records'] = database.get_row_count()
    return jsonify(stats), 200


import csv
from io import StringIO

@app.route('/api/predict', methods=['GET'])
def get_prediction():
    """AI prediction endpoint: LSTM forecasting + Random Forest classification."""
    # Lazy load models if not already loaded
    if not predictor.is_loaded():
        success = predictor.load_models()
        if not success:
            return jsonify({
                'status': 'not_ready',
                'message': 'Không thể tải mô hình AI. Kiểm tra tài nguyên server (RAM).',
                'prediction': None
            }), 200

    try:
        # Get recent data (need at least 30 records for LSTM input window)
        data = database.get_data(hours=2, limit=100)
        if len(data) < 30:
            return jsonify({
                'status': 'insufficient_data',
                'message': f'Cần ít nhất 30 bản ghi, hiện có {len(data)}',
                'prediction': None
            }), 200

        result = predictor.predict(data)
        if result is None:
            return jsonify({
                'status': 'error',
                'message': 'Prediction failed',
                'prediction': None
            }), 200

        if result.get('status') == 'ok':
            vn_now = datetime.utcnow() + timedelta(hours=7)
            # Save 30min prediction
            p30 = result['predictions']['30min']
            pt30 = (vn_now + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
            database.insert_prediction(pt30, '30min', p30['pm25'], p30['temperature'], p30['humidity'], p30['pressure'], p30['uv'], p30['weather'])
            
            # Save 60min prediction
            p60 = result['predictions']['60min']
            pt60 = (vn_now + timedelta(minutes=60)).strftime('%Y-%m-%d %H:%M:%S')
            database.insert_prediction(pt60, '60min', p60['pm25'], p60['temperature'], p60['humidity'], p60['pressure'], p60['uv'], p60['weather'])

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/export', methods=['GET'])
def export_data():
    """Export data as CSV for a given date range."""
    start_date = request.args.get('start', '2000-01-01')
    end_date = request.args.get('end', '2100-12-31')
    
    rows = database.get_data_range(start_date, end_date)
    
    si = StringIO()
    cw = csv.writer(si)
    # Header
    cw.writerow(['ID', 'Timestamp_VN', 'PM2.5', 'Temperature_C', 'Humidity_%', 'Pressure_hPa', 'UV_Index', 'Date_ESP32', 'Time_ESP32'])
    
    for r in rows:
        cw.writerow([
            r['id'], r['timestamp'], r['pm25'], r['temperature'], 
            r['humidity'], r['pressure'], r['uv'], 
            r['date_str'], r['time_str']
        ])
        
    output = si.getvalue()
    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=air_quality_{start_date}_to_{end_date}.csv"}
    )


@app.route('/api/export_predictions', methods=['GET'])
def export_predictions():
    """Export AI predictions as CSV for a given date range."""
    start_date = request.args.get('start', '2000-01-01')
    end_date = request.args.get('end', '2100-12-31')
    
    rows = database.get_predictions_range(start_date, end_date)
    
    si = StringIO()
    cw = csv.writer(si)
    # Header
    cw.writerow(['ID', 'Generated_At', 'Predicted_For_Time', 'Target_Period', 'PM2.5', 'Temperature_C', 'Humidity_%', 'Pressure_hPa', 'UV_Index', 'Weather'])
    
    for r in rows:
        cw.writerow([
            r['id'], r['timestamp'], r['pred_time'], r['target_period'],
            r['pm25'], r['temperature'], r['humidity'], r['pressure'], 
            r['uv'], r['weather']
        ])
        
    output = si.getvalue()
    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=ai_predictions_{start_date}_to_{end_date}.csv"}
    )

# ======================== SERVE FRONTEND ========================

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')


# ======================== RUN ========================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

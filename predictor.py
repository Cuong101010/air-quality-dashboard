"""
predictor.py - AI Prediction Module for Air Quality Dashboard
==============================================================
Loads trained LSTM + Random Forest models and performs inference.
Pipeline: Recent sensor data → LSTM → predicted values → Random Forest → weather label
"""

import os
import numpy as np
import joblib
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ======================== PATHS ========================
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')

# ======================== GLOBALS ========================
_lstm_model = None
_rf_model = None
_scaler = None
_label_encoder = None
_config = None
_loaded = False

WEATHER_VI = {
    'normal': 'Bình thường',
    'sunny': 'Nắng',
    'rainy': 'Có mưa',
}


def load_models():
    """Load all models and preprocessors. Call once at startup."""
    global _lstm_model, _rf_model, _scaler, _label_encoder, _config, _loaded

    try:
        # Check if model files exist
        required_files = ['lstm_model.onnx', 'rf_classifier.pkl', 'scaler.pkl',
                          'label_encoder.pkl', 'config.pkl']
        for f in required_files:
            path = os.path.join(MODELS_DIR, f)
            if not os.path.exists(path):
                logger.warning(f"Model file not found: {path}")
                return False

        import onnxruntime as ort

        logger.info("Loading AI models...")

        _config = joblib.load(os.path.join(MODELS_DIR, 'config.pkl'))
        _scaler = joblib.load(os.path.join(MODELS_DIR, 'scaler.pkl'))
        _label_encoder = joblib.load(os.path.join(MODELS_DIR, 'label_encoder.pkl'))
        _rf_model = joblib.load(os.path.join(MODELS_DIR, 'rf_classifier.pkl'))

        _lstm_model = ort.InferenceSession(os.path.join(MODELS_DIR, 'lstm_model.onnx'))

        _loaded = True
        logger.info("All AI models loaded successfully!")
        return True

    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        _loaded = False
        return False


def is_loaded():
    """Check if models are loaded and ready."""
    return _loaded


def _add_time_features(data_array, timestamps):
    """Add cyclical time features (hour_sin, hour_cos, dow_sin, dow_cos)."""
    time_features = []
    for ts in timestamps:
        if isinstance(ts, str):
            ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        hour = ts.hour + ts.minute / 60.0
        dow = ts.weekday()
        time_features.append([
            np.sin(2 * np.pi * hour / 24.0),
            np.cos(2 * np.pi * hour / 24.0),
            np.sin(2 * np.pi * dow / 7.0),
            np.cos(2 * np.pi * dow / 7.0),
        ])
    return np.hstack([data_array, np.array(time_features)])


def predict(recent_records):
    """
    Run the full hybrid prediction pipeline.

    Args:
        recent_records: list of dicts from database, each containing:
            pm25, temperature, humidity, pressure, uv, timestamp
            Must be sorted by timestamp ASC, at least SEQUENCE_LENGTH records.

    Returns:
        dict with prediction results, or None if not enough data / models not loaded.
    """
    if not _loaded:
        return None

    seq_len = _config['sequence_length']
    feature_cols = _config['feature_cols']

    if len(recent_records) < seq_len:
        logger.warning(f"Not enough data: {len(recent_records)} < {seq_len}")
        return None

    try:
        # Take the last seq_len records
        records = recent_records[-seq_len:]

        # Extract sensor features
        sensor_data = np.array([
            [float(r['pm25']), float(r['temperature']), float(r['humidity']),
             float(r['pressure']), float(r['uv'])]
            for r in records
        ])

        # Extract timestamps
        timestamps = [
            datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S')
            if isinstance(r['timestamp'], str) else r['timestamp']
            for r in records
        ]

        # Scale sensor features
        sensor_scaled = _scaler.transform(sensor_data)

        # Add time features
        full_features = _add_time_features(sensor_scaled, timestamps)

        # Reshape for LSTM: (1, seq_len, n_features)
        X = full_features.reshape(1, seq_len, -1).astype(np.float32)

        # ======== PHASE 1: LSTM Prediction ========
        input_name = _lstm_model.get_inputs()[0].name
        lstm_output = _lstm_model.run(None, {input_name: X})[0][0]  # shape: (10,)

        # Split into 30min and 60min predictions (scaled values)
        pred_30_scaled = lstm_output[:5]
        pred_60_scaled = lstm_output[5:]

        # Inverse transform to get actual values
        pred_30_actual = _scaler.inverse_transform(pred_30_scaled.reshape(1, -1))[0]
        pred_60_actual = _scaler.inverse_transform(pred_60_scaled.reshape(1, -1))[0]

        # ======== PHASE 2: Random Forest Classification ========
        # For current weather: use latest sensor data + time features
        last_ts = timestamps[-1]
        last_hour = last_ts.hour + last_ts.minute / 60.0
        last_dow = last_ts.weekday()
        current_features = np.concatenate([
            sensor_data[-1],
            [np.sin(2 * np.pi * last_hour / 24.0),
             np.cos(2 * np.pi * last_hour / 24.0),
             np.sin(2 * np.pi * last_dow / 7.0),
             np.cos(2 * np.pi * last_dow / 7.0)]
        ]).reshape(1, -1)
        current_weather_idx = _rf_model.predict(current_features)[0]
        current_weather = _label_encoder.inverse_transform([current_weather_idx])[0]

        # For predicted weather at t+30
        ts_30 = last_ts + timedelta(minutes=30)
        hour_30 = ts_30.hour + ts_30.minute / 60.0
        dow_30 = ts_30.weekday()
        features_30 = np.concatenate([
            pred_30_actual,
            [np.sin(2 * np.pi * hour_30 / 24.0),
             np.cos(2 * np.pi * hour_30 / 24.0),
             np.sin(2 * np.pi * dow_30 / 7.0),
             np.cos(2 * np.pi * dow_30 / 7.0)]
        ]).reshape(1, -1)
        weather_30_idx = _rf_model.predict(features_30)[0]
        weather_30 = _label_encoder.inverse_transform([weather_30_idx])[0]

        # For predicted weather at t+60
        ts_60 = last_ts + timedelta(minutes=60)
        hour_60 = ts_60.hour + ts_60.minute / 60.0
        dow_60 = ts_60.weekday()
        features_60 = np.concatenate([
            pred_60_actual,
            [np.sin(2 * np.pi * hour_60 / 24.0),
             np.cos(2 * np.pi * hour_60 / 24.0),
             np.sin(2 * np.pi * dow_60 / 7.0),
             np.cos(2 * np.pi * dow_60 / 7.0)]
        ]).reshape(1, -1)
        weather_60_idx = _rf_model.predict(features_60)[0]
        weather_60 = _label_encoder.inverse_transform([weather_60_idx])[0]

        # ======== Build Response ========
        result = {
            'status': 'ok',
            'current_weather': current_weather,
            'current_weather_vi': WEATHER_VI.get(current_weather, current_weather),
            'predictions': {
                '30min': {
                    'pm25': round(float(pred_30_actual[0]), 1),
                    'temperature': round(float(pred_30_actual[1]), 1),
                    'humidity': round(float(pred_30_actual[2]), 1),
                    'pressure': round(float(pred_30_actual[3]), 1),
                    'uv': round(float(pred_30_actual[4]), 2),
                    'weather': weather_30,
                    'weather_vi': WEATHER_VI.get(weather_30, weather_30),
                    'time': ts_30.strftime('%H:%M'),
                },
                '60min': {
                    'pm25': round(float(pred_60_actual[0]), 1),
                    'temperature': round(float(pred_60_actual[1]), 1),
                    'humidity': round(float(pred_60_actual[2]), 1),
                    'pressure': round(float(pred_60_actual[3]), 1),
                    'uv': round(float(pred_60_actual[4]), 2),
                    'weather': weather_60,
                    'weather_vi': WEATHER_VI.get(weather_60, weather_60),
                    'time': ts_60.strftime('%H:%M'),
                },
            },
            'model_info': {
                'lstm_input_window': f'{seq_len * 2} phút ({seq_len} bước)',
                'features': feature_cols,
                'method': 'LSTM → Random Forest (Hybrid Pipeline)',
            }
        }

        return result

    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}

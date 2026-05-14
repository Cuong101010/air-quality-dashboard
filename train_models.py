"""
train_models.py - Training script for Hybrid LSTM + Random Forest AI Pipeline
==============================================================================
Giai đoạn 1 (LSTM): Dự đoán PM2.5, Temperature, Humidity, Pressure, UV tại t+30min và t+60min
Giai đoạn 2 (Random Forest): Phân loại trạng thái thời tiết (Normal / Sunny / Rainy)

Chạy: python train_models.py
Output: models/lstm_model.keras, models/rf_classifier.pkl, models/scaler.pkl, models/label_encoder.pkl
"""

import os
import numpy as np
import pandas as pd
import joblib
import warnings
warnings.filterwarnings('ignore')

# ======================== CONFIG ========================
DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data_train', '_combined_balanced.csv')
MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')

# LSTM config
SEQUENCE_LENGTH = 30        # 30 bước quá khứ (~60 phút với khoảng cách 2 phút/bước)
FORECAST_STEPS_30 = 15      # 15 bước x 2 phút = 30 phút
FORECAST_STEPS_60 = 30      # 30 bước x 2 phút = 60 phút
LSTM_EPOCHS = 50
LSTM_BATCH_SIZE = 64

FEATURE_COLS = ['pm25', 'temperature', 'humidity', 'pressure', 'uv']
TIME_FEATURES = ['hour_sin', 'hour_cos', 'dow_sin', 'dow_cos']
ALL_FEATURES = FEATURE_COLS + TIME_FEATURES

os.makedirs(MODELS_DIR, exist_ok=True)


# ======================== STEP 1: LOAD & PREPROCESS ========================
def load_and_preprocess():
    """Load CSV, parse datetime, add time features, sort by time."""
    print("=" * 60)
    print("STEP 1: Loading and preprocessing data...")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH)
    print(f"  Raw data: {len(df)} rows")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Label distribution:\n{df['weather_label'].value_counts().to_string()}")

    # Parse datetime
    df['datetime'] = pd.to_datetime(
        df['date'] + ' ' + df['time'],
        format='%d/%m/%Y %H:%M:%S',
        errors='coerce'
    )
    df = df.dropna(subset=['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)

    # Add cyclical time features (giúp mô hình hiểu chu kỳ ngày/đêm)
    hours = df['datetime'].dt.hour + df['datetime'].dt.minute / 60.0
    df['hour_sin'] = np.sin(2 * np.pi * hours / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * hours / 24.0)

    dow = df['datetime'].dt.dayofweek
    df['dow_sin'] = np.sin(2 * np.pi * dow / 7.0)
    df['dow_cos'] = np.cos(2 * np.pi * dow / 7.0)

    print(f"  After preprocessing: {len(df)} rows")
    print(f"  Date range: {df['datetime'].min()} -> {df['datetime'].max()}")
    print()

    return df


# ======================== STEP 2: SCALING ========================
def scale_features(df):
    """Normalize sensor features using MinMaxScaler."""
    from sklearn.preprocessing import MinMaxScaler

    print("STEP 2: Scaling features...")

    scaler = MinMaxScaler()
    df_scaled = df.copy()
    df_scaled[FEATURE_COLS] = scaler.fit_transform(df[FEATURE_COLS])
    # Time features are already in [-1, 1] range, no need to scale

    joblib.dump(scaler, os.path.join(MODELS_DIR, 'scaler.pkl'))
    print(f"  Scaler saved to models/scaler.pkl")
    print(f"  Feature ranges (original):")
    for i, col in enumerate(FEATURE_COLS):
        print(f"    {col}: [{scaler.data_min_[i]:.2f}, {scaler.data_max_[i]:.2f}]")
    print()

    return df_scaled, scaler


# ======================== STEP 3: CREATE SEQUENCES FOR LSTM ========================
def create_sequences(df_scaled):
    """Create sliding window sequences for LSTM training."""
    print("STEP 3: Creating sequences for LSTM...")

    data = df_scaled[ALL_FEATURES].values
    targets_cols = df_scaled[FEATURE_COLS].values  # Only predict sensor values

    X, y = [], []

    max_offset = FORECAST_STEPS_60  # Need data up to t+60min

    for i in range(len(data) - SEQUENCE_LENGTH - max_offset):
        # Input: SEQUENCE_LENGTH steps of all features
        X.append(data[i:i + SEQUENCE_LENGTH])

        # Output: sensor values at t+30min and t+60min
        idx_30 = i + SEQUENCE_LENGTH + FORECAST_STEPS_30 - 1
        idx_60 = i + SEQUENCE_LENGTH + FORECAST_STEPS_60 - 1

        target_30 = targets_cols[idx_30]  # 5 values
        target_60 = targets_cols[idx_60]  # 5 values
        y.append(np.concatenate([target_30, target_60]))  # 10 values total

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)

    # Split 80/20 by time (no shuffle)
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"  Total sequences: {len(X)}")
    print(f"  X shape: {X.shape}  (samples, timesteps, features)")
    print(f"  y shape: {y.shape}  (samples, 10) = 5 features x 2 horizons")
    print(f"  Train: {len(X_train)} | Val: {len(X_val)}")
    print()

    return X_train, X_val, y_train, y_val


# ======================== STEP 4: TRAIN LSTM ========================
def train_lstm(X_train, X_val, y_train, y_val):
    """Build and train LSTM model for multi-step forecasting."""
    print("=" * 60)
    print("STEP 4: Training LSTM model...")
    print("=" * 60)

    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

    import tensorflow as tf
    tf.get_logger().setLevel('ERROR')
    from tensorflow import keras
    from tensorflow.keras import layers

    # Build model
    model = keras.Sequential([
        layers.Input(shape=(SEQUENCE_LENGTH, len(ALL_FEATURES))),
        layers.LSTM(64, return_sequences=True, dropout=0.2),
        layers.LSTM(32, dropout=0.2),
        layers.Dense(32, activation='relu'),
        layers.Dense(10)  # 5 features x 2 horizons
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='mse',
        metrics=['mae']
    )

    model.summary()
    print()

    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=10, restore_best_weights=True, verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1
        ),
    ]

    # Train
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=LSTM_EPOCHS,
        batch_size=LSTM_BATCH_SIZE,
        callbacks=callbacks,
        verbose=1
    )

    # Save model
    model_path = os.path.join(MODELS_DIR, 'lstm_model.keras')
    model.save(model_path)
    print(f"\n  LSTM model saved to {model_path}")

    # Evaluate
    val_loss, val_mae = model.evaluate(X_val, y_val, verbose=0)
    print(f"\n  === LSTM Evaluation (Validation Set) ===")
    print(f"  MSE Loss: {val_loss:.6f}")
    print(f"  MAE:      {val_mae:.6f}")

    # Calculate per-feature metrics
    y_pred = model.predict(X_val, verbose=0)
    feature_names_30 = [f"{f}_30min" for f in FEATURE_COLS]
    feature_names_60 = [f"{f}_60min" for f in FEATURE_COLS]
    all_names = feature_names_30 + feature_names_60

    print(f"\n  Per-feature MAE (scaled):")
    for i, name in enumerate(all_names):
        mae = np.mean(np.abs(y_val[:, i] - y_pred[:, i]))
        print(f"    {name:25s}: {mae:.4f}")

    print()
    return model, history


# ======================== STEP 5: TRAIN RANDOM FOREST ========================
def train_random_forest(df):
    """Train Random Forest classifier for weather state prediction."""
    print("=" * 60)
    print("STEP 5: Training Random Forest classifier...")
    print("=" * 60)

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix

    # Prepare features: sensor values + time features
    X = df[ALL_FEATURES].values
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(df['weather_label'])

    print(f"  Classes: {list(label_encoder.classes_)}")
    print(f"  Encoding: {dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))}")

    # Split (stratified to maintain class balance)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"  Train: {len(X_train)} | Test: {len(X_test)}")

    # Train
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)

    # Evaluate
    y_pred = rf.predict(X_test)
    accuracy = np.mean(y_pred == y_test)

    print(f"\n  === Random Forest Evaluation (Test Set) ===")
    print(f"  Accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")
    print(f"\n  Classification Report:")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))

    print(f"  Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  {' ':10s} {'  '.join(label_encoder.classes_)}")
    for i, row in enumerate(cm):
        print(f"  {label_encoder.classes_[i]:10s} {row}")

    # Feature importance
    print(f"\n  Feature Importance:")
    importances = rf.feature_importances_
    for name, imp in sorted(zip(ALL_FEATURES, importances), key=lambda x: -x[1]):
        bar = '#' * int(imp * 50)
        print(f"    {name:15s}: {imp:.4f} {bar}")

    # Save
    rf_path = os.path.join(MODELS_DIR, 'rf_classifier.pkl')
    le_path = os.path.join(MODELS_DIR, 'label_encoder.pkl')
    joblib.dump(rf, rf_path)
    joblib.dump(label_encoder, le_path)
    print(f"\n  Random Forest saved to {rf_path}")
    print(f"  Label Encoder saved to {le_path}")
    print()

    return rf, label_encoder


# ======================== MAIN ========================
def main():
    print("\n" + "=" * 60)
    print("  HYBRID AI PIPELINE TRAINING")
    print("  LSTM (Regression) + Random Forest (Classification)")
    print("=" * 60 + "\n")

    # Step 1: Load data
    df = load_and_preprocess()

    # Step 2: Scale features
    df_scaled, scaler = scale_features(df)

    # Step 3: Create sequences
    X_train, X_val, y_train, y_val = create_sequences(df_scaled)

    # Step 4: Train LSTM
    lstm_model, history = train_lstm(X_train, X_val, y_train, y_val)

    # Step 5: Train Random Forest (using ORIGINAL unscaled data)
    rf_model, label_encoder = train_random_forest(df)

    # Summary
    print("=" * 60)
    print("  [OK] TRAINING COMPLETE!")
    print("=" * 60)
    print(f"  Models saved to: {os.path.abspath(MODELS_DIR)}/")
    print(f"    - lstm_model.keras    (LSTM regression)")
    print(f"    - rf_classifier.pkl   (Random Forest classification)")
    print(f"    - scaler.pkl          (MinMaxScaler)")
    print(f"    - label_encoder.pkl   (LabelEncoder)")
    print()

    # Save training config for predictor to use
    config = {
        'sequence_length': SEQUENCE_LENGTH,
        'forecast_steps_30': FORECAST_STEPS_30,
        'forecast_steps_60': FORECAST_STEPS_60,
        'feature_cols': FEATURE_COLS,
        'time_features': TIME_FEATURES,
        'all_features': ALL_FEATURES,
    }
    joblib.dump(config, os.path.join(MODELS_DIR, 'config.pkl'))
    print(f"  Config saved to models/config.pkl")
    print()


if __name__ == '__main__':
    main()

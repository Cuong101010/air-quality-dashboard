import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
import tf2onnx
import warnings
warnings.filterwarnings('ignore')

print("Loading Keras model...")
model = tf.keras.models.load_model('models/lstm_model.keras')

print("Converting to ONNX...")
spec = (tf.TensorSpec((None, 30, 9), tf.float32, name="input"),)
output_path = "models/lstm_model.onnx"
model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13, output_path=output_path)
print(f"Successfully converted to {output_path}")

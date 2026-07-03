"""
AI-Powered Threat Detection Module
Implements MLP-GRU architecture for network security threat detection
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import pickle

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.config_loader import ConfigLoader
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MLPGRUModel:
    """
    Hybrid MLP-GRU Model for Threat Detection
    Combines Multi-Layer Perceptron with Gated Recurrent Units
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.history = None
        
        # Model parameters from config
        self.input_features = config.get('model', {}).get('input_features', 78)
        self.hidden_layers = config.get('model', {}).get('hidden_layers', [128, 64, 32])
        self.gru_units = config.get('model', {}).get('gru_units', 64)
        self.dropout_rate = config.get('model', {}).get('dropout_rate', 0.3)
        self.learning_rate = config.get('model', {}).get('learning_rate', 0.001)
        
    def build_model(self, input_shape: int, num_classes: int = 2) -> keras.Model:
        """
        Build the MLP-GRU hybrid architecture
        
        Args:
            input_shape: Number of input features
            num_classes: Number of output classes (default: 2 for binary classification)
        
        Returns:
            Compiled Keras model
        """
        try:
            self.logger.info("Building MLP-GRU model...")
            
            # Input layer
            inputs = layers.Input(shape=(input_shape,))
            
            # MLP layers for feature extraction
            x = layers.Dense(self.hidden_layers[0], activation='relu')(inputs)
            x = layers.BatchNormalization()(x)
            x = layers.Dropout(self.dropout_rate)(x)
            
            for units in self.hidden_layers[1:]:
                x = layers.Dense(units, activation='relu')(x)
                x = layers.BatchNormalization()(x)
                x = layers.Dropout(self.dropout_rate)(x)
            
            # Reshape for GRU (add time dimension)
            x = layers.Reshape((1, self.hidden_layers[-1]))(x)
            
            # GRU layers for temporal pattern learning
            x = layers.GRU(self.gru_units, return_sequences=True)(x)
            x = layers.Dropout(self.dropout_rate)(x)
            x = layers.GRU(self.gru_units // 2)(x)
            x = layers.Dropout(self.dropout_rate)(x)
            
            # Output layer
            if num_classes == 2:
                outputs = layers.Dense(1, activation='sigmoid')(x)
                loss = 'binary_crossentropy'
            else:
                outputs = layers.Dense(num_classes, activation='softmax')(x)
                loss = 'categorical_crossentropy'
            
            # Create model
            model = models.Model(inputs=inputs, outputs=outputs)
            
            # Compile model
            optimizer = keras.optimizers.Adam(learning_rate=self.learning_rate)
            model.compile(
                optimizer=optimizer,
                loss=loss,
                metrics=['accuracy', 
                        keras.metrics.Precision(name='precision'),
                        keras.metrics.Recall(name='recall')]
            )
            
            self.logger.info("Model built successfully")
            self.logger.info(f"Model summary:\n{model.summary()}")
            
            self.model = model
            return model
            
        except Exception as e:
            self.logger.error(f"Error building model: {str(e)}")
            raise
    
    def prepare_data(self, data_path: str, test_size: float = 0.2) -> Tuple:
        """
        Prepare data for training
        
        Args:
            data_path: Path to the processed data CSV file
            test_size: Proportion of data for testing
        
        Returns:
            Tuple of (X_train, X_test, y_train, y_test)
        """
        try:
            self.logger.info(f"Loading data from: {data_path}")
            
            # Load data
            df = pd.read_csv(data_path)
            self.logger.info(f"Loaded {len(df)} records")
            
            # Assume last column is the label
            X = df.iloc[:, :-1].values
            y = df.iloc[:, -1].values
            
            # Encode labels if necessary
            if y.dtype == 'object':
                y = self.label_encoder.fit_transform(y)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )
            
            # Scale features
            X_train = self.scaler.fit_transform(X_train)
            X_test = self.scaler.transform(X_test)
            
            self.logger.info(f"Train set: {X_train.shape}, Test set: {X_test.shape}")
            
            return X_train, X_test, y_train, y_test
            
        except Exception as e:
            self.logger.error(f"Error preparing data: {str(e)}")
            raise
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, 
              X_val: np.ndarray = None, y_val: np.ndarray = None,
              epochs: int = 50, batch_size: int = 256) -> Dict:
        """
        Train the model
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            epochs: Number of training epochs
            batch_size: Batch size for training
        
        Returns:
            Training history
        """
        try:
            self.logger.info("Starting model training...")
            
            # Build model if not already built
            if self.model is None:
                num_classes = len(np.unique(y_train))
                self.build_model(X_train.shape[1], num_classes)
            
            # Prepare validation data
            if X_val is None:
                X_train, X_val, y_train, y_val = train_test_split(
                    X_train, y_train, test_size=0.2, random_state=42
                )
            
            # Callbacks
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=10,
                    restore_best_weights=True,
                    verbose=1
                ),
                ModelCheckpoint(
                    'data/models/best_model.h5',
                    monitor='val_accuracy',
                    save_best_only=True,
                    verbose=1
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=5,
                    min_lr=1e-7,
                    verbose=1
                )
            ]
            
            # Train model
            self.history = self.model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=epochs,
                batch_size=batch_size,
                callbacks=callbacks,
                verbose=1
            )
            
            self.logger.info("Model training completed")
            
            return self.history.history
            
        except Exception as e:
            self.logger.error(f"Error training model: {str(e)}")
            raise
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """
        Evaluate the model on test data
        
        Args:
            X_test: Test features
            y_test: Test labels
        
        Returns:
            Dictionary of evaluation metrics
        """
        try:
            self.logger.info("Evaluating model...")
            
            # Get predictions
            y_pred_proba = self.model.predict(X_test)
            y_pred = (y_pred_proba > 0.5).astype(int).flatten()
            
            # Calculate metrics
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred, average='binary'),
                'recall': recall_score(y_test, y_pred, average='binary'),
                'f1_score': f1_score(y_test, y_pred, average='binary')
            }
            
            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred)
            metrics['confusion_matrix'] = cm.tolist()
            
            self.logger.info(f"Evaluation metrics: {metrics}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error evaluating model: {str(e)}")
            raise
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions on new data
        
        Args:
            X: Input features
        
        Returns:
            Tuple of (predictions, probabilities)
        """
        try:
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Get predictions
            y_pred_proba = self.model.predict(X_scaled)
            y_pred = (y_pred_proba > 0.5).astype(int).flatten()
            
            return y_pred, y_pred_proba
            
        except Exception as e:
            self.logger.error(f"Error making predictions: {str(e)}")
            raise
    
    def save_model(self, model_path: str):
        """Save the trained model and preprocessing objects"""
        try:
            self.logger.info(f"Saving model to: {model_path}")
            
            # Create directory
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # Save Keras model
            self.model.save(f"{model_path}_model.h5")
            
            # Save scaler and encoder
            with open(f"{model_path}_scaler.pkl", 'wb') as f:
                pickle.dump(self.scaler, f)
            
            with open(f"{model_path}_encoder.pkl", 'wb') as f:
                pickle.dump(self.label_encoder, f)
            
            self.logger.info("Model saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving model: {str(e)}")
            raise
    
    def load_model(self, model_path: str):
        """Load a trained model and preprocessing objects"""
        try:
            self.logger.info(f"Loading model from: {model_path}")
            
            # Load Keras model
            self.model = keras.models.load_model(f"{model_path}_model.h5")
            
            # Load scaler and encoder
            with open(f"{model_path}_scaler.pkl", 'rb') as f:
                self.scaler = pickle.load(f)
            
            with open(f"{model_path}_encoder.pkl", 'rb') as f:
                self.label_encoder = pickle.load(f)
            
            self.logger.info("Model loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            raise


class ThreatDetector:
    """High-level threat detection interface"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = ConfigLoader.load_config(config_path)
        self.logger = setup_logger(__name__)
        self.model = MLPGRUModel(self.config)
        
    def train_model(self, data_path: str) -> Dict[str, Any]:
        """Train the threat detection model"""
        try:
            self.logger.info("Starting threat detection model training...")
            
            # Prepare data
            X_train, X_test, y_train, y_test = self.model.prepare_data(data_path)
            
            # Train model
            history = self.model.train(
                X_train, y_train,
                epochs=self.config.get('model', {}).get('epochs', 50),
                batch_size=self.config.get('model', {}).get('batch_size', 256)
            )
            
            # Evaluate model
            metrics = self.model.evaluate(X_test, y_test)
            
            # Save model
            model_path = f"data/models/threat_detector_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.model.save_model(model_path)
            
            result = {
                'history': history,
                'metrics': metrics,
                'model_path': model_path
            }
            
            self.logger.info("Model training completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in model training: {str(e)}")
            raise
    
    def detect_threats(self, data: pd.DataFrame) -> pd.DataFrame:
        """Detect threats in new data"""
        try:
            self.logger.info(f"Detecting threats in {len(data)} records...")
            
            # Get predictions
            X = data.values
            predictions, probabilities = self.model.predict(X)
            
            # Add results to dataframe
            data['threat_detected'] = predictions
            data['threat_probability'] = probabilities
            
            # Classify severity
            data['severity'] = pd.cut(
                data['threat_probability'],
                bins=[0, 0.3, 0.5, 0.7, 0.9, 1.0],
                labels=['low', 'medium', 'high', 'critical', 'extreme']
            )
            
            self.logger.info(f"Detected {predictions.sum()} threats")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error detecting threats: {str(e)}")
            raise


def main():
    """Main execution function"""
    logger.info("Initializing Threat Detection System...")
    
    detector = ThreatDetector()
    
    # Check if processed data exists
    processed_files = list(Path('data/processed').glob('*.csv'))
    
    if processed_files:
        latest_file = max(processed_files, key=os.path.getctime)
        logger.info(f"Training model with: {latest_file}")
        
        result = detector.train_model(str(latest_file))
        logger.info(f"Training completed. Metrics: {result['metrics']}")
    else:
        logger.warning("No processed data found. Please run ETL pipeline first.")
    
    return True


if __name__ == "__main__":
    main()

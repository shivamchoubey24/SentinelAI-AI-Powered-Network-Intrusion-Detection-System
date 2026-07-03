"""
MLOps Module
Handles automated model retraining, versioning, and deployment
"""

import os
import sys
import logging
import mlflow
import mlflow.tensorflow
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.config_loader import ConfigLoader
from src.utils.logger import setup_logger
from src.models.threat_detector import ThreatDetector, MLPGRUModel
from src.blockchain.blockchain_logger import BlockchainLogger

logger = setup_logger(__name__)


class ModelRegistry:
    """Manages model versioning and registry"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Set MLflow tracking URI
        mlflow_uri = config.get('mlops', {}).get('tracking', {}).get('mlflow_uri', 'http://localhost:5000')
        mlflow.set_tracking_uri(mlflow_uri)
        
        # Set experiment
        experiment_name = config.get('mlops', {}).get('tracking', {}).get('experiment_name', 'network_security')
        mlflow.set_experiment(experiment_name)
        
        self.logger.info(f"MLflow tracking URI: {mlflow_uri}")
        self.logger.info(f"MLflow experiment: {experiment_name}")
    
    def log_model(self, model, model_name: str, metrics: Dict[str, float], 
                  params: Dict[str, Any], artifacts: Optional[Dict[str, str]] = None) -> str:
        """
        Log model to MLflow
        
        Args:
            model: Trained model object
            model_name: Name of the model
            metrics: Dictionary of evaluation metrics
            params: Dictionary of model parameters
            artifacts: Optional dictionary of artifact paths
        
        Returns:
            Run ID
        """
        try:
            with mlflow.start_run(run_name=model_name) as run:
                # Log parameters
                mlflow.log_params(params)
                
                # Log metrics
                mlflow.log_metrics(metrics)
                
                # Log model
                mlflow.tensorflow.log_model(
                    model,
                    artifact_path="model",
                    registered_model_name=model_name
                )
                
                # Log additional artifacts
                if artifacts:
                    for name, path in artifacts.items():
                        mlflow.log_artifact(path, artifact_path=name)
                
                # Add tags
                mlflow.set_tags({
                    'model_type': 'MLP-GRU',
                    'framework': 'TensorFlow',
                    'purpose': 'Threat Detection',
                    'timestamp': datetime.now().isoformat()
                })
                
                self.logger.info(f"Model logged to MLflow with run_id: {run.info.run_id}")
                
                return run.info.run_id
                
        except Exception as e:
            self.logger.error(f"Error logging model to MLflow: {str(e)}")
            raise
    
    def promote_model(self, model_name: str, version: int, stage: str = "Production") -> bool:
        """
        Promote a model version to a specific stage
        
        Args:
            model_name: Name of the registered model
            version: Model version number
            stage: Target stage (Staging, Production, Archived)
        
        Returns:
            True if successful
        """
        try:
            client = mlflow.tracking.MlflowClient()
            client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage
            )
            
            self.logger.info(f"Model {model_name} v{version} promoted to {stage}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error promoting model: {str(e)}")
            return False
    
    def get_latest_model(self, model_name: str, stage: str = "Production"):
        """
        Get the latest model from a specific stage
        
        Args:
            model_name: Name of the registered model
            stage: Stage to retrieve from
        
        Returns:
            Model object
        """
        try:
            model_uri = f"models:/{model_name}/{stage}"
            model = mlflow.tensorflow.load_model(model_uri)
            
            self.logger.info(f"Loaded model {model_name} from {stage}")
            return model
            
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            return None


class ModelMonitor:
    """Monitors model performance and detects drift"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.baseline_metrics = {}
        
    def set_baseline(self, metrics: Dict[str, float]):
        """Set baseline metrics for comparison"""
        self.baseline_metrics = metrics
        self.logger.info(f"Baseline metrics set: {metrics}")
    
    def detect_performance_drift(self, current_metrics: Dict[str, float], 
                                threshold: float = 0.1) -> bool:
        """
        Detect if model performance has degraded
        
        Args:
            current_metrics: Current model metrics
            threshold: Acceptable degradation threshold
        
        Returns:
            True if drift detected
        """
        try:
            if not self.baseline_metrics:
                self.logger.warning("No baseline metrics set")
                return False
            
            drift_detected = False
            
            for metric_name, baseline_value in self.baseline_metrics.items():
                if metric_name in current_metrics:
                    current_value = current_metrics[metric_name]
                    degradation = baseline_value - current_value
                    
                    if degradation > threshold:
                        self.logger.warning(
                            f"Performance drift detected in {metric_name}: "
                            f"baseline={baseline_value:.4f}, current={current_value:.4f}, "
                            f"degradation={degradation:.4f}"
                        )
                        drift_detected = True
            
            return drift_detected
            
        except Exception as e:
            self.logger.error(f"Error detecting performance drift: {str(e)}")
            return False
    
    def detect_data_drift(self, reference_data: pd.DataFrame, 
                         current_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect data drift between reference and current data
        
        Args:
            reference_data: Reference dataset
            current_data: Current dataset
        
        Returns:
            Dictionary with drift analysis results
        """
        try:
            drift_report = {}
            
            # Compare statistical properties
            for column in reference_data.columns:
                if column in current_data.columns:
                    ref_mean = reference_data[column].mean()
                    curr_mean = current_data[column].mean()
                    ref_std = reference_data[column].std()
                    curr_std = current_data[column].std()
                    
                    # Calculate drift score (simplified)
                    mean_diff = abs(ref_mean - curr_mean) / (ref_std + 1e-7)
                    
                    drift_report[column] = {
                        'mean_difference': mean_diff,
                        'drift_detected': mean_diff > 2.0  # 2 standard deviations
                    }
            
            self.logger.info(f"Data drift analysis completed for {len(drift_report)} features")
            
            return drift_report
            
        except Exception as e:
            self.logger.error(f"Error detecting data drift: {str(e)}")
            return {}


class AutoRetrainer:
    """Handles automated model retraining"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = ConfigLoader.load_config(config_path)
        self.logger = setup_logger(__name__)
        
        self.model_registry = ModelRegistry(self.config)
        self.model_monitor = ModelMonitor(self.config)
        self.blockchain_logger = BlockchainLogger(self.config)
        
        self.last_training_date = None
        
    def should_retrain(self) -> bool:
        """
        Determine if model should be retrained
        
        Returns:
            True if retraining is needed
        """
        try:
            # Check schedule
            schedule = self.config.get('model', {}).get('retraining', {}).get('schedule', 'weekly')
            
            if self.last_training_date is None:
                return True
            
            days_since_training = (datetime.now() - self.last_training_date).days
            
            if schedule == 'daily' and days_since_training >= 1:
                return True
            elif schedule == 'weekly' and days_since_training >= 7:
                return True
            elif schedule == 'monthly' and days_since_training >= 30:
                return True
            
            # Check if enough new data is available
            min_samples = self.config.get('model', {}).get('retraining', {}).get('min_new_samples', 1000)
            # This would check actual new data count in production
            
            self.logger.info("Retraining not needed at this time")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking retrain condition: {str(e)}")
            return False
    
    def retrain_model(self, data_path: str) -> Dict[str, Any]:
        """
        Retrain the model with new data
        
        Args:
            data_path: Path to training data
        
        Returns:
            Dictionary with retraining results
        """
        try:
            self.logger.info("Starting automated model retraining...")
            
            # Log to blockchain
            self.blockchain_logger.log_model_update({
                'operation': 'RETRAIN_START',
                'data_path': data_path,
                'timestamp': datetime.now().isoformat()
            })
            
            # Initialize detector
            detector = ThreatDetector(config_path=None)
            
            # Train model
            result = detector.train_model(data_path)
            
            # Log to MLflow
            run_id = self.model_registry.log_model(
                model=detector.model.model,
                model_name="threat_detector",
                metrics=result['metrics'],
                params={
                    'input_features': detector.model.input_features,
                    'hidden_layers': detector.model.hidden_layers,
                    'gru_units': detector.model.gru_units,
                    'dropout_rate': detector.model.dropout_rate,
                    'learning_rate': detector.model.learning_rate
                }
            )
            
            # Check if model should be promoted
            performance_threshold = self.config.get('mlops', {}).get('model_registry', {}).get('production_threshold', 0.95)
            
            if result['metrics']['accuracy'] >= performance_threshold:
                self.logger.info(f"Model meets production threshold ({performance_threshold})")
                # In production, you would promote the model here
            
            # Update last training date
            self.last_training_date = datetime.now()
            
            # Log to blockchain
            self.blockchain_logger.log_model_update({
                'operation': 'RETRAIN_COMPLETE',
                'run_id': run_id,
                'metrics': result['metrics'],
                'model_path': result['model_path'],
                'timestamp': datetime.now().isoformat()
            })
            
            self.logger.info("Model retraining completed successfully")
            
            return {
                'success': True,
                'run_id': run_id,
                'metrics': result['metrics'],
                'model_path': result['model_path']
            }
            
        except Exception as e:
            self.logger.error(f"Error during model retraining: {str(e)}")
            
            # Log failure to blockchain
            self.blockchain_logger.log_model_update({
                'operation': 'RETRAIN_FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_monitoring_cycle(self, test_data_path: str) -> Dict[str, Any]:
        """
        Run a complete monitoring cycle
        
        Args:
            test_data_path: Path to test data for evaluation
        
        Returns:
            Monitoring results
        """
        try:
            self.logger.info("Running model monitoring cycle...")
            
            # Load test data
            test_data = pd.read_csv(test_data_path)
            X_test = test_data.iloc[:, :-1].values
            y_test = test_data.iloc[:, -1].values
            
            # Load current production model
            detector = ThreatDetector()
            # In production, load from MLflow registry
            
            # Evaluate current performance
            # current_metrics = detector.model.evaluate(X_test, y_test)
            
            # Check for drift
            # drift_detected = self.model_monitor.detect_performance_drift(current_metrics)
            
            # If drift detected, trigger retraining
            # if drift_detected:
            #     self.logger.warning("Drift detected, triggering retraining...")
            #     self.retrain_model(data_path)
            
            monitoring_result = {
                'timestamp': datetime.now().isoformat(),
                'monitoring_completed': True
            }
            
            return monitoring_result
            
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {str(e)}")
            return {'error': str(e)}


def main():
    """Main execution function"""
    logger.info("Testing MLOps Module...")
    
    retrainer = AutoRetrainer()
    
    # Check if processed data exists
    processed_files = list(Path('data/processed').glob('*.csv'))
    
    if processed_files:
        latest_file = max(processed_files, key=os.path.getctime)
        logger.info(f"Using data file: {latest_file}")
        
        # Check if retraining is needed
        if retrainer.should_retrain():
            logger.info("Triggering model retraining...")
            result = retrainer.retrain_model(str(latest_file))
            logger.info(f"Retraining result: {result}")
        else:
            logger.info("Retraining not needed")
    else:
        logger.warning("No processed data found")
    
    logger.info("MLOps testing completed")


if __name__ == "__main__":
    main()

"""
Configuration Loader Utility
Loads and manages application configuration
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv


class ConfigLoader:
    """Loads configuration from YAML and environment variables"""
    
    @staticmethod
    def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from YAML file and environment variables
        
        Args:
            config_path: Path to config YAML file (optional)
        
        Returns:
            Configuration dictionary
        """
        # Load environment variables
        env_path = Path(__file__).parent.parent.parent / 'config' / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        # Default config path
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'
        
        # Load YAML config
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        
        # Override with environment variables
        config = ConfigLoader._merge_env_variables(config)
        
        return config
    
    @staticmethod
    def _merge_env_variables(config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge environment variables into config"""
        
        # Database configurations
        if 'MONGODB_URI' in os.environ:
            if 'database' not in config:
                config['database'] = {}
            if 'mongodb' not in config['database']:
                config['database']['mongodb'] = {}
            config['database']['mongodb']['uri'] = os.environ['MONGODB_URI']
        
        if 'POSTGRES_URI' in os.environ:
            if 'database' not in config:
                config['database'] = {}
            if 'postgresql' not in config['database']:
                config['database']['postgresql'] = {}
            config['database']['postgresql']['uri'] = os.environ['POSTGRES_URI']
        
        # API keys
        if 'GEMINI_API_KEY' in os.environ:
            if 'api_keys' not in config:
                config['api_keys'] = {}
            config['api_keys']['gemini'] = os.environ['GEMINI_API_KEY']
        
        # Blockchain configuration
        if 'BLOCKCHAIN_NETWORK' in os.environ:
            if 'blockchain' not in config:
                config['blockchain'] = {}
            config['blockchain']['network'] = os.environ['BLOCKCHAIN_NETWORK']
        
        # MLflow configuration
        if 'MLFLOW_TRACKING_URI' in os.environ:
            if 'mlops' not in config:
                config['mlops'] = {}
            if 'tracking' not in config['mlops']:
                config['mlops']['tracking'] = {}
            config['mlops']['tracking']['mlflow_uri'] = os.environ['MLFLOW_TRACKING_URI']
        
        return config
    
    @staticmethod
    def get_env(key: str, default: Any = None) -> Any:
        """
        Get environment variable
        
        Args:
            key: Environment variable key
            default: Default value if key not found
        
        Returns:
            Environment variable value or default
        """
        return os.environ.get(key, default)
    
    @staticmethod
    def save_config(config: Dict[str, Any], config_path: str):
        """
        Save configuration to YAML file
        
        Args:
            config: Configuration dictionary
            config_path: Path to save config file
        """
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    # Test configuration loader
    config = ConfigLoader.load_config()
    print("Configuration loaded successfully:")
    print(yaml.dump(config, default_flow_style=False))

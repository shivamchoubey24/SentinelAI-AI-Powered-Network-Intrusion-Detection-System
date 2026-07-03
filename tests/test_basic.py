# AI-Powered Network Security System
# Test Suite

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_config():
    """Provide sample configuration for tests"""
    return {
        'model': {
            'input_features': 10,
            'hidden_layers': [64, 32],
            'gru_units': 32,
            'dropout_rate': 0.3,
            'learning_rate': 0.001,
            'batch_size': 32,
            'epochs': 5
        },
        'blockchain': {
            'enabled': True,
            'difficulty': 2
        },
        'etl': {
            'batch_size': 100
        }
    }


@pytest.fixture
def sample_data():
    """Provide sample data for tests"""
    import pandas as pd
    import numpy as np
    
    data = pd.DataFrame({
        'feature1': np.random.randn(100),
        'feature2': np.random.randn(100),
        'feature3': np.random.randn(100),
        'label': np.random.choice([0, 1], 100)
    })
    
    return data


def test_imports():
    """Test that all main modules can be imported"""
    try:
        from src.etl import pipeline
        from src.models import threat_detector
        from src.blockchain import blockchain_logger
        from src.mlops import auto_retrainer
        from src.utils import config_loader, logger
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {str(e)}")


def test_config_loader():
    """Test configuration loading"""
    from src.utils.config_loader import ConfigLoader
    
    config = ConfigLoader.load_config()
    assert isinstance(config, dict)


def test_logger_setup():
    """Test logger initialization"""
    from src.utils.logger import setup_logger
    
    logger = setup_logger('test_logger')
    assert logger is not None
    logger.info("Test log message")


def test_blockchain_creation():
    """Test blockchain initialization"""
    from src.blockchain.blockchain_logger import Blockchain
    
    blockchain = Blockchain(difficulty=2)
    assert len(blockchain.chain) == 1  # Genesis block
    assert blockchain.is_chain_valid()


def test_blockchain_add_block():
    """Test adding blocks to blockchain"""
    from src.blockchain.blockchain_logger import Blockchain
    
    blockchain = Blockchain(difficulty=2)
    blockchain.add_block({'test': 'data'})
    
    assert len(blockchain.chain) == 2
    assert blockchain.is_chain_valid()


def test_etl_extractor(sample_config, tmp_path):
    """Test ETL data extractor"""
    from src.etl.pipeline import DataExtractor
    import pandas as pd
    
    # Create sample file
    sample_file = tmp_path / "test_data.csv"
    df = pd.DataFrame({'col1': [1, 2, 3], 'col2': [4, 5, 6]})
    df.to_csv(sample_file, index=False)
    
    extractor = DataExtractor(sample_config)
    result = extractor.extract_firewall_logs(str(sample_file))
    
    assert not result.empty
    assert len(result) == 3


def test_etl_transformer(sample_config, sample_data):
    """Test ETL data transformer"""
    from src.etl.pipeline import DataTransformer
    
    transformer = DataTransformer(sample_config)
    result = transformer.normalize_data(sample_data.copy())
    
    assert not result.empty
    assert len(result) == len(sample_data)


def test_model_building(sample_config):
    """Test MLP-GRU model building"""
    from src.models.threat_detector import MLPGRUModel
    
    model = MLPGRUModel(sample_config)
    keras_model = model.build_model(input_shape=10, num_classes=2)
    
    assert keras_model is not None
    assert len(keras_model.layers) > 0


# Add more test cases as needed

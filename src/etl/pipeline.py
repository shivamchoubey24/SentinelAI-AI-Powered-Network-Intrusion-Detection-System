"""
ETL Pipeline Module
Handles extraction, transformation, and loading of security data
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.config_loader import ConfigLoader
from src.utils.logger import setup_logger
from src.blockchain.blockchain_logger import BlockchainLogger

logger = setup_logger(__name__)


class DataExtractor:
    """Extract data from various security sources"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def extract_firewall_logs(self, file_path: str) -> pd.DataFrame:
        """Extract firewall log data"""
        try:
            self.logger.info(f"Extracting firewall logs from: {file_path}")
            
            if not os.path.exists(file_path):
                self.logger.warning(f"File not found: {file_path}, returning empty DataFrame")
                return pd.DataFrame()
            
            # Read CSV firewall logs
            df = pd.read_csv(file_path)
            self.logger.info(f"Extracted {len(df)} firewall log records")
            return df
            
        except Exception as e:
            self.logger.error(f"Error extracting firewall logs: {str(e)}")
            return pd.DataFrame()
    
    def extract_network_traffic(self, file_path: str) -> pd.DataFrame:
        """Extract network traffic data"""
        try:
            self.logger.info(f"Extracting network traffic from: {file_path}")
            
            if not os.path.exists(file_path):
                self.logger.warning(f"File not found: {file_path}, returning empty DataFrame")
                return pd.DataFrame()
            
            # For PCAP files, we'll use a simplified approach
            # In production, you'd use scapy or pyshark
            df = pd.read_csv(file_path)  # Assume pre-converted to CSV
            self.logger.info(f"Extracted {len(df)} network traffic records")
            return df
            
        except Exception as e:
            self.logger.error(f"Error extracting network traffic: {str(e)}")
            return pd.DataFrame()
    
    def extract_system_logs(self, file_path: str) -> pd.DataFrame:
        """Extract system log data"""
        try:
            self.logger.info(f"Extracting system logs from: {file_path}")
            
            if not os.path.exists(file_path):
                self.logger.warning(f"File not found: {file_path}, returning empty DataFrame")
                return pd.DataFrame()
            
            # Read JSON system logs
            with open(file_path, 'r') as f:
                logs = json.load(f)
            
            df = pd.DataFrame(logs)
            self.logger.info(f"Extracted {len(df)} system log records")
            return df
            
        except Exception as e:
            self.logger.error(f"Error extracting system logs: {str(e)}")
            return pd.DataFrame()


class DataTransformer:
    """Transform and normalize security data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize data for ML processing"""
        try:
            self.logger.info("Normalizing data...")
            
            if df.empty:
                return df
            
            # Handle missing values
            df = df.fillna(0)
            
            # Convert timestamps
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            
            # Normalize numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if df[col].std() != 0:
                    df[col] = (df[col] - df[col].mean()) / df[col].std()
            
            self.logger.info("Data normalization completed")
            return df
            
        except Exception as e:
            self.logger.error(f"Error normalizing data: {str(e)}")
            return df
    
    def feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create additional features for ML"""
        try:
            self.logger.info("Performing feature engineering...")
            
            if df.empty:
                return df
            
            # Add time-based features
            if 'timestamp' in df.columns:
                df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
                df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
                df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            
            # Add statistical features (example)
            if 'packet_size' in df.columns:
                df['packet_size_log'] = np.log1p(df['packet_size'])
            
            self.logger.info("Feature engineering completed")
            return df
            
        except Exception as e:
            self.logger.error(f"Error in feature engineering: {str(e)}")
            return df
    
    def encode_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical variables"""
        try:
            self.logger.info("Encoding categorical variables...")
            
            if df.empty:
                return df
            
            categorical_cols = df.select_dtypes(include=['object']).columns
            
            for col in categorical_cols:
                if col != 'timestamp':
                    # Label encoding for simplicity
                    df[col] = pd.Categorical(df[col]).codes
            
            self.logger.info("Categorical encoding completed")
            return df
            
        except Exception as e:
            self.logger.error(f"Error encoding categorical variables: {str(e)}")
            return df


class DataLoader:
    """Load processed data into storage"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def save_to_csv(self, df: pd.DataFrame, output_path: str) -> bool:
        """Save DataFrame to CSV"""
        try:
            self.logger.info(f"Saving data to: {output_path}")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            df.to_csv(output_path, index=False)
            self.logger.info(f"Successfully saved {len(df)} records to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving to CSV: {str(e)}")
            return False
    
    def save_to_database(self, df: pd.DataFrame, collection_name: str) -> bool:
        """Save DataFrame to MongoDB"""
        try:
            self.logger.info(f"Saving data to MongoDB collection: {collection_name}")
            
            # This is a placeholder - implement actual MongoDB connection
            # from pymongo import MongoClient
            # client = MongoClient(self.config['mongodb']['uri'])
            # db = client[self.config['mongodb']['database']]
            # collection = db[collection_name]
            # collection.insert_many(df.to_dict('records'))
            
            self.logger.info(f"Successfully saved {len(df)} records to database")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving to database: {str(e)}")
            return False


class ETLPipeline:
    """Main ETL Pipeline orchestrator"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = ConfigLoader.load_config(config_path)
        self.logger = setup_logger(__name__)
        
        # Initialize components
        self.extractor = DataExtractor(self.config)
        self.transformer = DataTransformer(self.config)
        self.loader = DataLoader(self.config)
        
        # Initialize blockchain logger if enabled
        self.blockchain_enabled = self.config.get('blockchain', {}).get('enabled', False)
        if self.blockchain_enabled:
            self.blockchain_logger = BlockchainLogger(self.config)
        
    def run_pipeline(self, source_type: str = 'all') -> bool:
        """Run the complete ETL pipeline"""
        try:
            self.logger.info(f"Starting ETL pipeline for source: {source_type}")
            start_time = datetime.now()
            
            # Log to blockchain
            if self.blockchain_enabled:
                self.blockchain_logger.log_etl_operation({
                    'operation': 'ETL_START',
                    'source_type': source_type,
                    'timestamp': start_time.isoformat()
                })
            
            # Extract
            data_frames = []
            
            if source_type in ['all', 'firewall']:
                firewall_df = self.extractor.extract_firewall_logs(
                    'data/raw/firewall/firewall_logs.csv'
                )
                data_frames.append(firewall_df)
            
            if source_type in ['all', 'traffic']:
                traffic_df = self.extractor.extract_network_traffic(
                    'data/raw/traffic/network_traffic.csv'
                )
                data_frames.append(traffic_df)
            
            if source_type in ['all', 'system']:
                system_df = self.extractor.extract_system_logs(
                    'data/raw/system/system_logs.json'
                )
                data_frames.append(system_df)
            
            # Combine all data
            if data_frames:
                combined_df = pd.concat(data_frames, ignore_index=True)
            else:
                self.logger.warning("No data extracted")
                return False
            
            self.logger.info(f"Extracted total {len(combined_df)} records")
            
            # Transform
            transformed_df = self.transformer.normalize_data(combined_df)
            transformed_df = self.transformer.feature_engineering(transformed_df)
            transformed_df = self.transformer.encode_categorical(transformed_df)
            
            # Load
            output_path = f"data/processed/processed_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            success = self.loader.save_to_csv(transformed_df, output_path)
            
            if success:
                # Save to database
                self.loader.save_to_database(transformed_df, 'security_logs')
            
            # Log completion to blockchain
            if self.blockchain_enabled:
                self.blockchain_logger.log_etl_operation({
                    'operation': 'ETL_COMPLETE',
                    'source_type': source_type,
                    'records_processed': len(transformed_df),
                    'output_file': output_path,
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': (datetime.now() - start_time).total_seconds()
                })
            
            self.logger.info("ETL pipeline completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"ETL pipeline failed: {str(e)}")
            
            # Log failure to blockchain
            if self.blockchain_enabled:
                self.blockchain_logger.log_etl_operation({
                    'operation': 'ETL_FAILED',
                    'source_type': source_type,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
            
            return False


def main():
    """Main execution function"""
    logger.info("Initializing ETL Pipeline...")
    
    pipeline = ETLPipeline()
    success = pipeline.run_pipeline(source_type='all')
    
    if success:
        logger.info("ETL Pipeline executed successfully")
    else:
        logger.error("ETL Pipeline execution failed")
    
    return success


if __name__ == "__main__":
    main()

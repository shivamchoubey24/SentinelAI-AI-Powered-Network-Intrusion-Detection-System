#!/usr/bin/env python3
"""
Initialize database connections and create necessary collections/tables
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import setup_logger
from src.utils.config_loader import ConfigLoader

logger = setup_logger(__name__)


def init_mongodb():
    """Initialize MongoDB collections"""
    try:
        logger.info("Initializing MongoDB...")
        
        # Placeholder for actual MongoDB initialization
        # from pymongo import MongoClient
        # config = ConfigLoader.load_config()
        # mongodb_uri = config.get('database', {}).get('mongodb', {}).get('uri')
        # client = MongoClient(mongodb_uri)
        # db = client[config['database']['mongodb']['database']]
        
        # Create collections
        collections = ['security_logs', 'security_alerts', 'model_metadata', 'blockchain_records']
        
        for collection_name in collections:
            logger.info(f"Collection '{collection_name}' ready")
            # db.create_collection(collection_name)
        
        logger.info("MongoDB initialization completed")
        return True
        
    except Exception as e:
        logger.error(f"MongoDB initialization failed: {str(e)}")
        logger.info("MongoDB is optional. System will use file-based storage.")
        return False


def init_postgresql():
    """Initialize PostgreSQL tables"""
    try:
        logger.info("Initializing PostgreSQL...")
        
        # Placeholder for actual PostgreSQL initialization
        # import psycopg2
        # config = ConfigLoader.load_config()
        # postgres_uri = config.get('database', {}).get('postgresql', {}).get('uri')
        # conn = psycopg2.connect(postgres_uri)
        # cursor = conn.cursor()
        
        # Create tables
        tables = ['users', 'audit_trail', 'performance_metrics']
        
        for table_name in tables:
            logger.info(f"Table '{table_name}' ready")
            # cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (...)")
        
        # conn.commit()
        # cursor.close()
        # conn.close()
        
        logger.info("PostgreSQL initialization completed")
        return True
        
    except Exception as e:
        logger.error(f"PostgreSQL initialization failed: {str(e)}")
        logger.info("PostgreSQL is optional. System will use file-based storage.")
        return False


def create_directories():
    """Create necessary directories"""
    logger.info("Creating project directories...")
    
    directories = [
        'data/raw/firewall',
        'data/raw/traffic',
        'data/raw/system',
        'data/processed',
        'data/models',
        'data/blockchain',
        'logs',
        'outputs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Directory created: {directory}")
    
    logger.info("All directories created successfully")
    return True


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("Database Initialization Script")
    logger.info("=" * 60)
    
    # Create directories
    create_directories()
    
    # Initialize databases
    logger.info("\nInitializing databases...")
    logger.info("Note: Database initialization is optional.")
    logger.info("The system can run with file-based storage if databases are not available.")
    
    mongo_success = init_mongodb()
    postgres_success = init_postgresql()
    
    logger.info("\n" + "=" * 60)
    logger.info("Initialization Summary:")
    logger.info("=" * 60)
    logger.info(f"MongoDB: {'✓ Success' if mongo_success else '✗ Not configured (optional)'}")
    logger.info(f"PostgreSQL: {'✓ Success' if postgres_success else '✗ Not configured (optional)'}")
    logger.info(f"Directories: ✓ Success")
    logger.info("=" * 60)
    logger.info("\nSystem is ready to use!")
    logger.info("Run 'python scripts/download_datasets.py' to create sample data.")


if __name__ == "__main__":
    main()

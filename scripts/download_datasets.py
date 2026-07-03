#!/usr/bin/env python3
"""
Script to download security datasets
Downloads CIC-IDS2017, UNSW-NB15, and other security datasets
"""

import os
import sys
import logging
import requests
from pathlib import Path
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_sample_data():
    """
    Create sample security data for testing
    Since actual datasets are large, we'll create synthetic data
    """
    logger.info("Creating sample security datasets...")
    
    # Create directories
    os.makedirs('data/raw/firewall', exist_ok=True)
    os.makedirs('data/raw/traffic', exist_ok=True)
    os.makedirs('data/raw/system', exist_ok=True)
    
    # Generate sample firewall logs
    logger.info("Generating sample firewall logs...")
    num_samples = 1000
    
    firewall_data = {
        'timestamp': pd.date_range(start='2024-01-01', periods=num_samples, freq='1min'),
        'source_ip': [f"192.168.{np.random.randint(1,255)}.{np.random.randint(1,255)}" 
                     for _ in range(num_samples)],
        'dest_ip': [f"10.0.{np.random.randint(1,255)}.{np.random.randint(1,255)}" 
                   for _ in range(num_samples)],
        'source_port': np.random.randint(1024, 65535, num_samples),
        'dest_port': np.random.choice([80, 443, 22, 21, 3306, 5432], num_samples),
        'protocol': np.random.choice(['TCP', 'UDP', 'ICMP'], num_samples),
        'bytes_sent': np.random.randint(100, 100000, num_samples),
        'bytes_received': np.random.randint(100, 100000, num_samples),
        'duration': np.random.randint(1, 300, num_samples),
        'flags': np.random.choice(['SYN', 'ACK', 'FIN', 'RST', 'PSH'], num_samples),
        'label': np.random.choice(['normal', 'attack'], num_samples, p=[0.85, 0.15])
    }
    
    firewall_df = pd.DataFrame(firewall_data)
    firewall_df.to_csv('data/raw/firewall/firewall_logs.csv', index=False)
    logger.info(f"Created {num_samples} firewall log records")
    
    # Generate sample network traffic data
    logger.info("Generating sample network traffic data...")
    
    traffic_data = {
        'timestamp': pd.date_range(start='2024-01-01', periods=num_samples, freq='1min'),
        'src_ip': [f"192.168.{np.random.randint(1,255)}.{np.random.randint(1,255)}" 
                  for _ in range(num_samples)],
        'dst_ip': [f"10.0.{np.random.randint(1,255)}.{np.random.randint(1,255)}" 
                  for _ in range(num_samples)],
        'protocol': np.random.choice(['TCP', 'UDP', 'ICMP'], num_samples),
        'packet_size': np.random.randint(64, 1500, num_samples),
        'ttl': np.random.randint(64, 128, num_samples),
        'window_size': np.random.randint(1024, 65535, num_samples),
        'flow_duration': np.random.randint(1, 1000, num_samples),
        'total_fwd_packets': np.random.randint(1, 100, num_samples),
        'total_bwd_packets': np.random.randint(1, 100, num_samples),
        'label': np.random.choice([0, 1], num_samples, p=[0.85, 0.15])
    }
    
    traffic_df = pd.DataFrame(traffic_data)
    traffic_df.to_csv('data/raw/traffic/network_traffic.csv', index=False)
    logger.info(f"Created {num_samples} network traffic records")
    
    # Generate sample system logs
    logger.info("Generating sample system logs...")
    
    import json
    
    system_logs = []
    log_levels = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
    log_messages = [
        'User login successful',
        'Failed login attempt',
        'File access denied',
        'Suspicious process detected',
        'Configuration changed',
        'Service started',
        'Service stopped',
        'Memory usage high'
    ]
    
    for i in range(num_samples):
        log_entry = {
            'timestamp': (pd.Timestamp('2024-01-01') + pd.Timedelta(minutes=i)).isoformat(),
            'level': np.random.choice(log_levels),
            'message': np.random.choice(log_messages),
            'user': f"user{np.random.randint(1, 100)}",
            'process': f"proc{np.random.randint(1, 50)}",
            'cpu_usage': float(np.random.uniform(0, 100)),
            'memory_usage': float(np.random.uniform(0, 100)),
            'label': int(np.random.choice([0, 1], p=[0.9, 0.1]))
        }
        system_logs.append(log_entry)
    
    with open('data/raw/system/system_logs.json', 'w') as f:
        json.dump(system_logs, f, indent=2)
    
    logger.info(f"Created {num_samples} system log records")
    
    logger.info("Sample dataset creation completed successfully!")
    
    return True


def download_cic_ids2017():
    """
    Download CIC-IDS2017 dataset
    Note: This is a placeholder - actual download would require authentication
    """
    logger.info("CIC-IDS2017 dataset download instructions:")
    logger.info("1. Visit: https://www.unb.ca/cic/datasets/ids-2017.html")
    logger.info("2. Download the dataset manually")
    logger.info("3. Extract to data/raw/cic-ids2017/")
    logger.info("For now, using sample data instead.")
    
    return False


def download_unsw_nb15():
    """
    Download UNSW-NB15 dataset
    Note: This is a placeholder - actual download would require authentication
    """
    logger.info("UNSW-NB15 dataset download instructions:")
    logger.info("1. Visit: https://research.unsw.edu.au/projects/unsw-nb15-dataset")
    logger.info("2. Download the dataset manually")
    logger.info("3. Extract to data/raw/unsw-nb15/")
    logger.info("For now, using sample data instead.")
    
    return False


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("Security Dataset Downloader")
    logger.info("=" * 60)
    
    # Create sample data (always available)
    create_sample_data()
    
    # Note about real datasets
    logger.info("\n" + "=" * 60)
    logger.info("IMPORTANT: Sample data has been created for testing.")
    logger.info("For production use, download real security datasets:")
    logger.info("=" * 60)
    
    download_cic_ids2017()
    logger.info("")
    download_unsw_nb15()
    
    logger.info("\n" + "=" * 60)
    logger.info("Dataset setup completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

"""
AI-Powered Network Security System
Main package initialization
"""

__version__ = "1.0.0"
__author__ = "UIET Team - Sourav, Shubham, Om, Tanuj, Sehwag, Yatin"
__description__ = "AI-Powered Network Security System with Real-Time ETL Pipelines, Automated MLOps Retraining, and Blockchain-Secured Logs"

from src.utils.config_loader import ConfigLoader
from src.utils.logger import setup_logger

__all__ = ['ConfigLoader', 'setup_logger']

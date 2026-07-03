"""
Blockchain Security Module
Provides tamper-proof logging and audit trails for security operations
"""

import os
import sys
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import pickle

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.config_loader import ConfigLoader
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Block:
    """Represents a single block in the blockchain"""
    
    def __init__(self, index: int, timestamp: str, data: Dict, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block"""
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int = 4):
        """Mine the block with proof of work"""
        target = '0' * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def to_dict(self) -> Dict:
        """Convert block to dictionary"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'hash': self.hash
        }


class Blockchain:
    """Blockchain implementation for security audit logs"""
    
    def __init__(self, difficulty: int = 4):
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.pending_transactions: List[Dict] = []
        
        # Create genesis block
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create the first block in the chain"""
        genesis_block = Block(0, datetime.now().isoformat(), 
                             {'message': 'Genesis Block'}, '0')
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain"""
        return self.chain[-1]
    
    def add_block(self, data: Dict) -> Block:
        """Add a new block to the chain"""
        new_block = Block(
            index=len(self.chain),
            timestamp=datetime.now().isoformat(),
            data=data,
            previous_hash=self.get_latest_block().hash
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        return new_block
    
    def is_chain_valid(self) -> bool:
        """Validate the integrity of the blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Check if current block's hash is correct
            if current_block.hash != current_block.calculate_hash():
                return False
            
            # Check if previous hash matches
            if current_block.previous_hash != previous_block.hash:
                return False
        
        return True
    
    def get_chain(self) -> List[Dict]:
        """Get the entire blockchain as a list of dictionaries"""
        return [block.to_dict() for block in self.chain]
    
    def save_chain(self, filepath: str):
        """Save the blockchain to a file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'wb') as f:
                pickle.dump(self.chain, f)
            logger.info(f"Blockchain saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving blockchain: {str(e)}")
    
    def load_chain(self, filepath: str) -> bool:
        """Load the blockchain from a file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    self.chain = pickle.load(f)
                logger.info(f"Blockchain loaded from {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading blockchain: {str(e)}")
            return False


class BlockchainLogger:
    """
    High-level interface for logging security operations to blockchain
    """
    
    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            config = ConfigLoader.load_config()
        
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize blockchain
        self.blockchain = Blockchain(difficulty=2)  # Lower difficulty for faster testing
        
        # Load existing chain if available
        self.chain_file = 'data/blockchain/security_chain.pkl'
        self.blockchain.load_chain(self.chain_file)
        
        self.logger.info("Blockchain logger initialized")
    
    def log_etl_operation(self, operation_data: Dict) -> Dict:
        """
        Log an ETL operation to the blockchain
        
        Args:
            operation_data: Dictionary containing operation details
        
        Returns:
            Block information
        """
        try:
            self.logger.info(f"Logging ETL operation: {operation_data.get('operation', 'UNKNOWN')}")
            
            # Add metadata
            log_entry = {
                'type': 'ETL_OPERATION',
                'timestamp': datetime.now().isoformat(),
                **operation_data
            }
            
            # Add block to chain
            block = self.blockchain.add_block(log_entry)
            
            # Save chain
            self.blockchain.save_chain(self.chain_file)
            
            self.logger.info(f"ETL operation logged to block #{block.index}")
            
            return block.to_dict()
            
        except Exception as e:
            self.logger.error(f"Error logging ETL operation: {str(e)}")
            return {}
    
    def log_threat_detection(self, threat_data: Dict) -> Dict:
        """
        Log a threat detection event to the blockchain
        
        Args:
            threat_data: Dictionary containing threat details
        
        Returns:
            Block information
        """
        try:
            self.logger.info(f"Logging threat detection: {threat_data.get('threat_type', 'UNKNOWN')}")
            
            log_entry = {
                'type': 'THREAT_DETECTION',
                'timestamp': datetime.now().isoformat(),
                **threat_data
            }
            
            block = self.blockchain.add_block(log_entry)
            self.blockchain.save_chain(self.chain_file)
            
            self.logger.info(f"Threat detection logged to block #{block.index}")
            
            return block.to_dict()
            
        except Exception as e:
            self.logger.error(f"Error logging threat detection: {str(e)}")
            return {}
    
    def log_model_update(self, model_data: Dict) -> Dict:
        """
        Log a model training/update event to the blockchain
        
        Args:
            model_data: Dictionary containing model details
        
        Returns:
            Block information
        """
        try:
            self.logger.info(f"Logging model update: {model_data.get('operation', 'UNKNOWN')}")
            
            log_entry = {
                'type': 'MODEL_UPDATE',
                'timestamp': datetime.now().isoformat(),
                **model_data
            }
            
            block = self.blockchain.add_block(log_entry)
            self.blockchain.save_chain(self.chain_file)
            
            self.logger.info(f"Model update logged to block #{block.index}")
            
            return block.to_dict()
            
        except Exception as e:
            self.logger.error(f"Error logging model update: {str(e)}")
            return {}
    
    def log_system_event(self, event_data: Dict) -> Dict:
        """
        Log a general system event to the blockchain
        
        Args:
            event_data: Dictionary containing event details
        
        Returns:
            Block information
        """
        try:
            self.logger.info(f"Logging system event: {event_data.get('event_type', 'UNKNOWN')}")
            
            log_entry = {
                'type': 'SYSTEM_EVENT',
                'timestamp': datetime.now().isoformat(),
                **event_data
            }
            
            block = self.blockchain.add_block(log_entry)
            self.blockchain.save_chain(self.chain_file)
            
            self.logger.info(f"System event logged to block #{block.index}")
            
            return block.to_dict()
            
        except Exception as e:
            self.logger.error(f"Error logging system event: {str(e)}")
            return {}
    
    def verify_integrity(self) -> bool:
        """
        Verify the integrity of the blockchain
        
        Returns:
            True if blockchain is valid, False otherwise
        """
        try:
            is_valid = self.blockchain.is_chain_valid()
            
            if is_valid:
                self.logger.info("Blockchain integrity verified - VALID")
            else:
                self.logger.error("Blockchain integrity check - INVALID")
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Error verifying blockchain: {str(e)}")
            return False
    
    def get_audit_trail(self, start_date: Optional[str] = None, 
                       end_date: Optional[str] = None,
                       event_type: Optional[str] = None) -> List[Dict]:
        """
        Retrieve audit trail from blockchain
        
        Args:
            start_date: Filter events from this date
            end_date: Filter events until this date
            event_type: Filter by event type
        
        Returns:
            List of audit log entries
        """
        try:
            chain = self.blockchain.get_chain()
            filtered_logs = []
            
            for block in chain[1:]:  # Skip genesis block
                data = block['data']
                
                # Apply filters
                if event_type and data.get('type') != event_type:
                    continue
                
                if start_date and data.get('timestamp', '') < start_date:
                    continue
                
                if end_date and data.get('timestamp', '') > end_date:
                    continue
                
                filtered_logs.append(block)
            
            self.logger.info(f"Retrieved {len(filtered_logs)} audit log entries")
            
            return filtered_logs
            
        except Exception as e:
            self.logger.error(f"Error retrieving audit trail: {str(e)}")
            return []
    
    def export_audit_report(self, output_path: str, 
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> bool:
        """
        Export audit report to JSON file
        
        Args:
            output_path: Path to save the report
            start_date: Filter events from this date
            end_date: Filter events until this date
        
        Returns:
            True if successful, False otherwise
        """
        try:
            audit_trail = self.get_audit_trail(start_date, end_date)
            
            report = {
                'generated_at': datetime.now().isoformat(),
                'total_blocks': len(self.blockchain.chain),
                'integrity_verified': self.blockchain.is_chain_valid(),
                'start_date': start_date,
                'end_date': end_date,
                'audit_logs': audit_trail
            }
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Audit report exported to {output_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting audit report: {str(e)}")
            return False


def main():
    """Main execution function for testing"""
    logger.info("Testing Blockchain Security Module...")
    
    # Initialize blockchain logger
    bc_logger = BlockchainLogger()
    
    # Test logging different types of events
    bc_logger.log_etl_operation({
        'operation': 'ETL_START',
        'source': 'firewall_logs',
        'records': 1000
    })
    
    bc_logger.log_threat_detection({
        'threat_type': 'intrusion_attempt',
        'severity': 'high',
        'source_ip': '192.168.1.100',
        'blocked': True
    })
    
    bc_logger.log_model_update({
        'operation': 'MODEL_TRAIN',
        'model_version': '1.0.0',
        'accuracy': 0.95
    })
    
    # Verify integrity
    is_valid = bc_logger.verify_integrity()
    logger.info(f"Blockchain valid: {is_valid}")
    
    # Export audit report
    bc_logger.export_audit_report('data/blockchain/audit_report.json')
    
    logger.info("Blockchain testing completed")


if __name__ == "__main__":
    main()

"""
Test Configuration
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ['TESTING'] = 'True'


@pytest.fixture(scope='session')
def project_root_path():
    """Return project root path"""
    return project_root


@pytest.fixture(scope='session')
def test_data_dir(tmp_path_factory):
    """Create temporary directory for test data"""
    return tmp_path_factory.mktemp('test_data')

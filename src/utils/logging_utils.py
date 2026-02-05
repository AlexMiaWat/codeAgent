"""
Utility functions for logging setup.
"""

import logging
import sys
from pathlib import Path
import codecs

logger = logging.getLogger(__name__)

def setup_logging():
    """Setup logging (called after log cleanup)"""
    # Remove existing FileHandler for code_agent.log if it exists
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            # baseFilename can be a string with an absolute path
            base_filename = str(handler.baseFilename)
            if base_filename.endswith('code_agent.log') or 'code_agent.log' in base_filename:
                root_logger.removeHandler(handler)
                handler.close()
    
    # Remove code_agent.log file if it exists
    log_file = Path('logs/code_agent.log')
    if log_file.exists():
        try:
            log_file.unlink()
        except Exception:
            pass
    
    # Configure logging (force=True is available from Python 3.8+)
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/code_agent.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ],
            force=True  # Override existing configuration (Python 3.8+)
        )
    except TypeError:
        # For older Python versions without force=True
        # Clear handlers and configure again
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(logging.FileHandler('logs/code_agent.log', encoding='utf-8'))
        root_logger.addHandler(logging.StreamHandler(sys.stdout))
        root_logger.setLevel(logging.INFO)

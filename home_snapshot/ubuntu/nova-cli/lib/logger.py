"""Logger utility for Nova CLI"""

import sys
import logging
from datetime import datetime
from pathlib import Path

class Logger:
    """Centralized logging"""
    
    LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    
    COLORS = {
        'DEBUG': '\033[0;36m',     # Cyan
        'INFO': '\033[0;32m',      # Green
        'WARNING': '\033[1;33m',   # Yellow
        'ERROR': '\033[0;31m',     # Red
        'CRITICAL': '\033[0;35m',  # Magenta
        'RESET': '\033[0m',
    }
    
    def __init__(self, name='nova-cli', log_file=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.level = logging.INFO
        
        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.DEBUG)
        console.setFormatter(self._get_formatter())
        self.logger.addHandler(console)
        
        # File handler
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            file_h = logging.FileHandler(log_file)
            file_h.setLevel(logging.DEBUG)
            file_h.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s'
            ))
            self.logger.addHandler(file_h)
    
    def _get_formatter(self):
        """Get colored formatter"""
        class ColoredFormatter(logging.Formatter):
            def format(self, record):
                color = Logger.COLORS.get(record.levelname, '')
                reset = Logger.COLORS['RESET']
                record.levelname = f"{color}{record.levelname}{reset}"
                return super().format(record)
        
        return ColoredFormatter('%(levelname)-8s %(message)s')
    
    def set_level(self, level):
        """Set logging level"""
        self.level = self.LEVELS.get(level.upper(), logging.INFO)
        self.logger.setLevel(self.level)
    
    def debug(self, msg):
        self.logger.debug(msg)
    
    def info(self, msg):
        self.logger.info(msg)
    
    def success(self, msg):
        self.logger.info(f"✓ {msg}")
    
    def warning(self, msg):
        self.logger.warning(f"⚠ {msg}")
    
    def error(self, msg):
        self.logger.error(f"✗ {msg}")
    
    def critical(self, msg):
        self.logger.critical(f"✗ {msg}")
    
    def step(self, msg, step_num=None):
        """Log a step"""
        prefix = f"[{step_num}]" if step_num else "→"
        self.info(f"{prefix} {msg}")

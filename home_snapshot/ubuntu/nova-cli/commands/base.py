"""Base command class for Nova CLI"""

from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
import sys
import os

# Add lib directory to path
_lib_path = Path(__file__).parent.parent / 'lib'
if str(_lib_path) not in sys.path:
    sys.path.insert(0, str(_lib_path))

from logger import Logger
from config import Config


class BaseCommand(ABC):
    """Abstract base class for Nova CLI commands"""
    
    def __init__(self, logger: Logger, config: Config):
        self.logger = logger
        self.config = config
        self.migration_home = Path(config.get('migration_home', os.getcwd()))
    
    @staticmethod
    @abstractmethod
    def run(logger: Logger, config: Config, args: list) -> int:
        """
        Execute the command
        
        Args:
            logger: Logger instance
            config: Config instance
            args: Command arguments
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        pass
    
    def success(self, msg: str) -> None:
        """Log success message"""
        self.logger.success(msg)
    
    def error(self, msg: str) -> None:
        """Log error message"""
        self.logger.error(msg)
    
    def info(self, msg: str) -> None:
        """Log info message"""
        self.logger.info(msg)
    
    def warning(self, msg: str) -> None:
        """Log warning message"""
        self.logger.warning(msg)
    
    def step(self, msg: str, step_num: Optional[int] = None) -> None:
        """Log step message"""
        self.logger.step(msg, step_num)

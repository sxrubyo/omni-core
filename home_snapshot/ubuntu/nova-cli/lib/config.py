"""Configuration management for Nova CLI"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """Configuration loader and manager"""
    
    DEFAULT_CONFIG_PATHS = [
        Path.home() / '.nova' / 'config.json',
        Path('/etc/nova/config.json'),
        Path('./nova-config.json'),
    ]
    
    def __init__(self):
        self.config: Dict[str, Any] = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment"""
        config = {}
        
        # Check for config files
        for path in self.DEFAULT_CONFIG_PATHS:
            if path.exists():
                try:
                    with open(path) as f:
                        config.update(json.load(f))
                    break
                except Exception:
                    pass
        
        # Override with environment variables
        config.update({
            'migration_home': os.getenv('MIGRATION_HOME', os.getcwd()),
            'backup_dir': os.getenv('BACKUP_DIR', './backups'),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'ssh_user': os.getenv('SSH_USER', 'ubuntu'),
            'ssh_port': int(os.getenv('SSH_PORT', '22')),
            'ssh_key': os.getenv('SSH_KEY', os.path.expanduser('~/.ssh/id_rsa')),
        })
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self.config[key] = value
    
    def save(self, path: Path) -> None:
        """Save configuration to file"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.config, f, indent=2)

"""SSH operations helper"""

import subprocess
import os
from pathlib import Path
from typing import Optional, Tuple

class SSH:
    """SSH operations wrapper"""
    
    @staticmethod
    def check_connection(host: str, user: str = 'ubuntu', port: int = 22, 
                         key: Optional[Path] = None) -> bool:
        """Test SSH connection"""
        cmd = ['ssh']
        
        if key and key.exists():
            cmd.extend(['-i', str(key)])
        
        cmd.extend(['-p', str(port), f'{user}@{host}', 'echo ok'])
        
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def copy_file(local: Path, remote: str, host: str, user: str = 'ubuntu', 
                  port: int = 22, key: Optional[Path] = None) -> bool:
        """Copy file via SCP"""
        cmd = ['scp', '-r']
        
        if key and key.exists():
            cmd.extend(['-i', str(key)])
        
        cmd.extend(['-P', str(port)])
        cmd.append(str(local))
        cmd.append(f'{user}@{host}:{remote}')
        
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def execute(cmd: str, host: str, user: str = 'ubuntu', port: int = 22,
                key: Optional[Path] = None) -> Tuple[int, str]:
        """Execute command remotely"""
        ssh_cmd = ['ssh']
        
        if key and key.exists():
            ssh_cmd.extend(['-i', str(key)])
        
        ssh_cmd.extend(['-p', str(port), f'{user}@{host}', cmd])
        
        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=300)
            return result.returncode, result.stdout + result.stderr
        except Exception as e:
            return 1, str(e)

"""Docker operations helper"""

import subprocess
import json
from typing import List, Dict, Optional
from pathlib import Path

class Docker:
    """Docker and Docker Compose wrapper"""
    
    @staticmethod
    def compose_file_exists(path: Path) -> bool:
        """Check if docker-compose file exists"""
        return (path / 'docker-compose-prod.yml').exists()
    
    @staticmethod
    def run_compose(args: List[str], cwd: Path) -> int:
        """Run docker-compose command"""
        cmd = ['docker-compose', '-f', str(cwd / 'docker-compose-prod.yml')] + args
        result = subprocess.run(cmd, cwd=cwd)
        return result.returncode
    
    @staticmethod
    def ps(cwd: Path) -> Dict[str, str]:
        """Get container status"""
        cmd = ['docker-compose', '-f', str(cwd / 'docker-compose-prod.yml'), 'ps', '--format', 'json']
        try:
            output = subprocess.check_output(cmd, cwd=cwd, text=True)
            return json.loads(output) if output else {}
        except Exception:
            return {}
    
    @staticmethod
    def logs(cwd: Path, service: str = '') -> str:
        """Get container logs"""
        cmd = ['docker-compose', '-f', str(cwd / 'docker-compose-prod.yml'), 'logs', '--tail=50']
        if service:
            cmd.append(service)
        
        try:
            return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.STDOUT)
        except Exception as e:
            return f"Error getting logs: {e}"
    
    @staticmethod
    def is_healthy(cwd: Path, service: str = '') -> bool:
        """Check if services are healthy"""
        containers = Docker.ps(cwd)
        
        if not containers:
            return False
        
        if isinstance(containers, dict):
            containers = [containers]
        
        for container in containers:
            if service and service not in container.get('Service', ''):
                continue
            
            status = container.get('State', '').lower()
            if 'healthy' not in status and 'running' not in status:
                return False
        
        return True

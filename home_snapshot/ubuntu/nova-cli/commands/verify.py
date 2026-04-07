"""Post-migration verification command"""

import sys
import socket
import subprocess
import json
from pathlib import Path
from typing import Tuple

# Add paths for imports
_lib_path = Path(__file__).parent.parent / 'lib'
if str(_lib_path) not in sys.path:
    sys.path.insert(0, str(_lib_path))

from logger import Logger
from config import Config
from .base import BaseCommand
from docker import Docker
from utils import run_command_output


class VerifyCommand(BaseCommand):
    """Post-migration verification"""
    
    @staticmethod
    def run(logger: Logger, config: Config, args: list) -> int:
        """Execute verification"""
        cmd = VerifyCommand(logger, config)
        return cmd.execute()
    
    def execute(self) -> int:
        """Run all verification checks"""
        self.step("Starting post-migration verification", 1)
        
        checks = [
            ("Container status", self.check_containers),
            ("Port connectivity", self.check_ports),
            ("Database connectivity", self.check_databases),
            ("API endpoints", self.check_api_endpoints),
            ("Backup integrity", self.check_backups),
        ]
        
        failed = []
        for check_name, check_func in checks:
            self.step(f"Verifying {check_name}...")
            try:
                if check_func():
                    self.success(f"{check_name} OK")
                else:
                    self.warning(f"{check_name} failed or incomplete")
                    failed.append(check_name)
            except Exception as e:
                self.error(f"{check_name} error: {e}")
                failed.append(check_name)
        
        if not failed:
            self.success("All verification checks passed")
            return 0
        else:
            self.warning(f"Some checks failed: {', '.join(failed)}")
            return 1
    
    def check_containers(self) -> bool:
        """Check all containers running and healthy"""
        try:
            migration_prep = self.migration_home / 'migration_prep'
            
            if not migration_prep.exists():
                self.warning("  migration_prep not found")
                return False
            
            if not Docker.compose_file_exists(migration_prep):
                self.warning("  docker-compose-prod.yml not found")
                return False
            
            containers = Docker.ps(migration_prep)
            
            if not containers:
                self.error("  No containers found")
                return False
            
            if isinstance(containers, dict):
                containers = [containers]
            
            all_healthy = True
            for container in containers:
                service = container.get('Service', 'unknown')
                state = container.get('State', 'unknown')
                status = container.get('Status', 'unknown')
                
                self.info(f"  {service}: {state} ({status})")
                
                if 'running' not in state.lower():
                    all_healthy = False
            
            return all_healthy
        except Exception as e:
            self.error(f"  Container check error: {e}")
            return False
    
    def check_ports(self) -> bool:
        """Verify services respond on expected ports"""
        ports = {
            80: 'HTTP',
            443: 'HTTPS',
            3005: 'Nova API',
            8002: 'Backup Service',
            5678: 'Debug Port',
        }
        
        responding = []
        not_responding = []
        
        for port, service in ports.items():
            if self._port_responding(port):
                responding.append(f"{service}({port})")
            else:
                not_responding.append(f"{service}({port})")
        
        if responding:
            self.info(f"  Responding: {', '.join(responding)}")
        
        if not_responding:
            self.warning(f"  Not responding: {', '.join(not_responding)}")
        
        return len(responding) > 0
    
    def _port_responding(self, port: int) -> bool:
        """Check if port is responding"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0
        except Exception:
            return False
    
    def check_databases(self) -> bool:
        """Check database connectivity"""
        databases_ok = True
        
        # Check PostgreSQL
        if self._check_postgresql():
            self.info("  PostgreSQL: connected")
        else:
            self.warning("  PostgreSQL: not available")
            databases_ok = False
        
        # Check SQLite
        if self._check_sqlite():
            self.info("  SQLite: available")
        else:
            self.warning("  SQLite: not available")
        
        return databases_ok
    
    def _check_postgresql(self) -> bool:
        """Check PostgreSQL connectivity"""
        try:
            rc, stdout, stderr = run_command_output(
                "psql -U postgres -d postgres -c 'SELECT 1' 2>/dev/null"
            )
            return rc == 0
        except Exception:
            return False
    
    def _check_sqlite(self) -> bool:
        """Check SQLite database"""
        melissa_db = self.migration_home / 'melissa.db'
        
        if not melissa_db.exists():
            return False
        
        try:
            rc, stdout, stderr = run_command_output(f"sqlite3 {melissa_db} 'SELECT 1'")
            return rc == 0
        except Exception:
            return False
    
    def check_api_endpoints(self) -> bool:
        """Test API endpoints"""
        try:
            endpoints = [
                ('http://localhost:3005/health', 'Nova API health'),
                ('http://localhost:8002/status', 'Backup service status'),
            ]
            
            responding = []
            failed = []
            
            for url, name in endpoints:
                if self._test_endpoint(url):
                    responding.append(name)
                else:
                    failed.append(name)
            
            if responding:
                self.info(f"  Responding: {', '.join(responding)}")
            
            if failed:
                self.warning(f"  Not responding: {', '.join(failed)}")
            
            return len(responding) > 0
        except Exception as e:
            self.warning(f"  API endpoint check error: {e}")
            return False
    
    def _test_endpoint(self, url: str) -> bool:
        """Test if endpoint responds"""
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(url)
            req.add_header('User-agent', 'nova-cli')
            
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status == 200 or response.status == 404
        except Exception:
            return False
    
    def check_backups(self) -> bool:
        """Validate backups exist and are readable"""
        try:
            backup_dir = Path(self.config.get('backup_dir', './backups'))
            
            if not backup_dir.exists():
                self.warning("  Backup directory does not exist")
                return False
            
            backups = list(backup_dir.glob('backup_*'))
            
            if not backups:
                self.warning("  No backups found")
                return False
            
            latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
            self.info(f"  Latest backup: {latest_backup.name}")
            
            # Check for backup metadata
            metadata_file = latest_backup / 'backup.json'
            if metadata_file.exists():
                try:
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                    
                    self.info(f"  Metadata: {len(metadata.get('backups', {}))} backup files")
                    return True
                except Exception as e:
                    self.warning(f"  Could not read backup metadata: {e}")
                    return False
            else:
                self.info(f"  Backup exists but no metadata")
                return True
        except Exception as e:
            self.error(f"  Backup check error: {e}")
            return False

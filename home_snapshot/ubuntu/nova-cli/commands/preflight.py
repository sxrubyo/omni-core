"""Preflight validation command"""

import sys
import os
import shutil
import subprocess
import socket
from pathlib import Path

# Add paths for imports
_lib_path = Path(__file__).parent.parent / 'lib'
if str(_lib_path) not in sys.path:
    sys.path.insert(0, str(_lib_path))

from logger import Logger
from config import Config
from .base import BaseCommand
from utils import check_command_exists, run_command_output


class PreflightCommand(BaseCommand):
    """Validate server readiness for Nova deployment"""
    
    @staticmethod
    def run(logger: Logger, config: Config, args: list) -> int:
        """Execute preflight validation"""
        cmd = PreflightCommand(logger, config)
        return cmd.execute()
    
    def execute(self) -> int:
        """Run all preflight checks"""
        self.step("Starting preflight validation", 1)
        
        checks = [
            ("Docker installation", self.check_docker),
            ("Available ports", self.check_ports),
            ("Disk space", self.check_disk_space),
            ("Network configuration", self.check_network),
            (".env.secure file", self.check_env_secure),
            ("Database integrity", self.check_database_integrity),
        ]
        
        failed = []
        for check_name, check_func in checks:
            self.step(f"Checking {check_name}...")
            try:
                if check_func():
                    self.success(f"{check_name} OK")
                else:
                    self.error(f"{check_name} failed")
                    failed.append(check_name)
            except Exception as e:
                self.error(f"{check_name} error: {e}")
                failed.append(check_name)
        
        if failed:
            self.error(f"Preflight validation failed: {', '.join(failed)}")
            return 1
        
        self.success("All preflight checks passed")
        return 0
    
    def check_docker(self) -> bool:
        """Check Docker is installed and working"""
        if not check_command_exists('docker'):
            self.error("Docker not found in PATH")
            return False
        
        try:
            rc, stdout, stderr = run_command_output('docker --version')
            if rc != 0:
                self.error(f"Docker check failed: {stderr}")
                return False
            
            # Get version string
            version_line = stdout.strip()
            self.info(f"  {version_line}")
            
            # Verify docker-compose
            if not check_command_exists('docker-compose'):
                self.error("docker-compose not found in PATH")
                return False
            
            return True
        except Exception as e:
            self.error(f"Docker check error: {e}")
            return False
    
    def check_ports(self) -> bool:
        """Check required ports are available"""
        required_ports = [80, 443, 3005, 8002, 5678]
        unavailable = []
        
        for port in required_ports:
            if not self._is_port_available(port):
                unavailable.append(port)
        
        if unavailable:
            self.error(f"Ports in use: {unavailable}")
            return False
        
        self.info(f"  Ports available: {required_ports}")
        return True
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return True
        except OSError:
            return False
    
    def check_disk_space(self) -> bool:
        """Check minimum disk space (1.5GB required)"""
        try:
            stat = shutil.disk_usage(self.migration_home)
            free_gb = stat.free / (1024 ** 3)
            required_gb = 1.5
            
            self.info(f"  Free space: {free_gb:.1f}GB (required: {required_gb}GB)")
            
            if free_gb < required_gb:
                self.error(f"Insufficient disk space: {free_gb:.1f}GB < {required_gb}GB")
                return False
            
            return True
        except Exception as e:
            self.error(f"Disk space check error: {e}")
            return False
    
    def check_network(self) -> bool:
        """Check network configuration (validate 172.28.0.0/16 not in use)"""
        try:
            rc, stdout, stderr = run_command_output(
                "ip route | grep -q '172.28.0.0/16' && echo 'in_use' || echo 'free'"
            )
            
            if "in_use" in stdout:
                self.error("Network 172.28.0.0/16 is already in use")
                return False
            
            self.info("  Network 172.28.0.0/16 is available")
            return True
        except Exception as e:
            self.error(f"Network check error: {e}")
            return False
    
    def check_env_secure(self) -> bool:
        """Check .env.secure file exists and has correct permissions"""
        env_path = self.migration_home / '.env.secure'
        
        if not env_path.exists():
            self.error(f".env.secure not found at {env_path}")
            return False
        
        try:
            # Check permissions (should not be world readable)
            mode = oct(env_path.stat().st_mode)[-3:]
            if mode[-1] != '0':  # Last digit should not include 'other' read permission
                self.warning(f".env.secure has permissive permissions: {mode}")
            
            self.info(f"  .env.secure found with permissions {mode}")
            return True
        except Exception as e:
            self.error(f".env.secure check error: {e}")
            return False
    
    def check_database_integrity(self) -> bool:
        """Validate database files integrity"""
        try:
            # Check if validate-databases.sh exists and run it
            validate_script = self.migration_home / 'validate-databases.sh'
            
            if validate_script.exists():
                rc = run_command_output(f"bash {validate_script}")[0]
                if rc != 0:
                    self.error("Database validation script failed")
                    return False
                self.info("  Database validation script passed")
            else:
                self.warning("validate-databases.sh not found, skipping script validation")
            
            # Check for common database files
            db_files = [
                self.migration_home / 'melissa.db',
                self.migration_home / 'migration_prep' / 'databases',
            ]
            
            found_dbs = []
            for db_path in db_files:
                if db_path.exists():
                    found_dbs.append(str(db_path))
            
            if not found_dbs and not validate_script.exists():
                self.warning("No database files found")
            else:
                self.info(f"  Database files: {found_dbs}")
            
            return True
        except Exception as e:
            self.error(f"Database integrity check error: {e}")
            return False

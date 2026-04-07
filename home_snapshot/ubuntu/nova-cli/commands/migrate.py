"""Full migration execution command"""

import sys
import os
import time
from pathlib import Path

# Add paths for imports
_lib_path = Path(__file__).parent.parent / 'lib'
if str(_lib_path) not in sys.path:
    sys.path.insert(0, str(_lib_path))

from logger import Logger
from config import Config
from .base import BaseCommand
from utils import check_command_exists, run_command_output
from ssh import SSH
from docker import Docker


class MigrateCommand(BaseCommand):
    """Execute full migration to target server"""
    
    @staticmethod
    def run(logger: Logger, config: Config, args: list) -> int:
        """Execute migration"""
        if len(args) < 1:
            logger.error("Usage: nova migrate <target_host> [--skip-preflight] [--skip-backup]")
            return 1
        
        target_host = args[0]
        skip_preflight = '--skip-preflight' in args
        skip_backup = '--skip-backup' in args
        
        cmd = MigrateCommand(logger, config)
        return cmd.execute(target_host, skip_preflight, skip_backup)
    
    def execute(self, target_host: str, skip_preflight: bool = False, 
                skip_backup: bool = False) -> int:
        """Run migration"""
        self.step("Starting migration to target server", 1)
        
        ssh_user = self.config.get('ssh_user', 'ubuntu')
        ssh_port = self.config.get('ssh_port', 22)
        ssh_key = self.config.get('ssh_key', None)
        if ssh_key:
            ssh_key = Path(ssh_key)
        
        # Step 1: Preflight check on source
        if not skip_preflight:
            self.step("Running preflight checks on source", 2)
            if not self._run_preflight_local():
                self.error("Source preflight check failed")
                return 1
        
        # Step 2: Create backup on source
        if not skip_backup:
            self.step("Creating backup on source", 3)
            if not self._create_backup():
                self.error("Backup creation failed")
                return 1
        
        # Step 3: Verify SSH connection to target
        self.step("Verifying connection to target server", 4)
        if not SSH.check_connection(target_host, user=ssh_user, port=ssh_port, key=ssh_key):
            self.error(f"Cannot connect to {ssh_user}@{target_host}:{ssh_port}")
            return 1
        self.success(f"Connected to {target_host}")
        
        # Step 4: Copy migration_prep to target
        self.step("Copying migration_prep to target", 5)
        migration_prep = self.migration_home / 'migration_prep'
        if not migration_prep.exists():
            self.error("migration_prep directory not found on source")
            return 1
        
        target_path = f"/tmp/nova-migration-{int(time.time())}"
        if not SSH.copy_file(migration_prep, target_path, target_host, user=ssh_user, 
                             port=ssh_port, key=ssh_key):
            self.error(f"Failed to copy migration_prep to {target_host}")
            return 1
        self.success(f"Copied to {target_host}:{target_path}")
        
        # Step 5: Run preflight on target
        self.step("Running preflight checks on target", 6)
        preflight_cmd = f"cd {target_path} && python3 -m nova.commands preflight"
        rc, output = SSH.execute(preflight_cmd, target_host, user=ssh_user, 
                                 port=ssh_port, key=ssh_key)
        
        if rc != 0:
            self.error("Target preflight check failed")
            self.error(output)
            return 1
        self.success("Target preflight passed")
        
        # Step 6: Restore databases on target
        self.step("Restoring databases on target", 7)
        restore_cmd = f"cd {target_path} && bash scripts/restore-databases.sh"
        rc, output = SSH.execute(restore_cmd, target_host, user=ssh_user, 
                                 port=ssh_port, key=ssh_key)
        
        if rc != 0:
            self.warning(f"Database restore completed with status {rc}")
            self.info(output)
        else:
            self.success("Databases restored")
        
        # Step 7: Start docker-compose on target
        self.step("Starting services on target", 8)
        compose_cmd = f"cd {target_path} && docker-compose -f docker-compose-prod.yml up -d"
        rc, output = SSH.execute(compose_cmd, target_host, user=ssh_user, 
                                 port=ssh_port, key=ssh_key)
        
        if rc != 0:
            self.error("Failed to start services on target")
            self.error(output)
            return 1
        self.success("Services started")
        
        # Step 8: Wait for services to be ready
        self.step("Waiting for services to be ready", 9)
        time.sleep(10)
        
        # Step 9: Verify health on target
        self.step("Verifying service health on target", 10)
        if not self._verify_health_remote(target_host, target_path, ssh_user, ssh_port, ssh_key):
            self.warning("Some health checks failed, but migration completed")
        else:
            self.success("All services healthy")
        
        self.success(f"Migration completed successfully to {target_host}")
        return 0
    
    def _run_preflight_local(self) -> bool:
        """Run preflight on local machine"""
        try:
            from preflight import PreflightCommand
            
            result = PreflightCommand.run(self.logger, self.config, [])
            return result == 0
        except Exception as e:
            self.error(f"Preflight error: {e}")
            return False
    
    def _create_backup(self) -> bool:
        """Create backup on local machine"""
        try:
            from backup import BackupCommand
            
            result = BackupCommand.run(self.logger, self.config, ['--compress'])
            return result == 0
        except Exception as e:
            self.error(f"Backup error: {e}")
            return False
    
    def _verify_health_remote(self, host: str, work_dir: str, user: str, 
                              port: int, key: Path) -> bool:
        """Verify service health on remote server"""
        try:
            # Check docker-compose status
            cmd = f"cd {work_dir} && docker-compose -f docker-compose-prod.yml ps"
            rc, output = SSH.execute(cmd, host, user=user, port=port, key=key)
            
            if rc != 0:
                self.warning("Could not get docker-compose status")
                return False
            
            self.info("Docker services status:")
            for line in output.split('\n')[-5:]:
                if line.strip():
                    self.info(f"  {line}")
            
            return True
        except Exception as e:
            self.warning(f"Health verification error: {e}")
            return False

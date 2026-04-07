"""Rollback to previous snapshot command"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add paths for imports
_lib_path = Path(__file__).parent.parent / 'lib'
if str(_lib_path) not in sys.path:
    sys.path.insert(0, str(_lib_path))

from logger import Logger
from config import Config
from .base import BaseCommand
from docker import Docker
from utils import run_command_output, check_command_exists


class RollbackCommand(BaseCommand):
    """Rollback to previous snapshot"""
    
    @staticmethod
    def run(logger: Logger, config: Config, args: list) -> int:
        """Execute rollback"""
        snapshot_id = args[0] if args else None
        cmd = RollbackCommand(logger, config)
        
        if snapshot_id:
            return cmd.execute(snapshot_id)
        else:
            return cmd.list_snapshots()
    
    def execute(self, snapshot_id: str) -> int:
        """Run rollback to snapshot"""
        self.step("Starting rollback to snapshot", 1)
        
        # Step 1: Validate snapshot
        self.step("Validating snapshot integrity", 2)
        snapshot_path = self._find_snapshot(snapshot_id)
        
        if not snapshot_path:
            self.error(f"Snapshot not found: {snapshot_id}")
            return 1
        
        if not self._validate_snapshot(snapshot_path):
            self.error("Snapshot validation failed")
            return 1
        
        self.success(f"Snapshot valid: {snapshot_path}")
        
        # Step 2: Backup current state
        self.step("Backing up current state", 3)
        backup_path = self.migration_home / f"pre-rollback-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Create pre-rollback backup
            import shutil
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Backup migration_prep if it exists
            migration_prep = self.migration_home / 'migration_prep'
            if migration_prep.exists():
                shutil.copytree(
                    migration_prep,
                    backup_path / 'migration_prep_before',
                    dirs_exist_ok=True
                )
            
            self.success(f"Pre-rollback backup created: {backup_path}")
        except Exception as e:
            self.warning(f"Pre-rollback backup failed: {e}")
        
        # Step 3: Stop services
        self.step("Stopping services", 4)
        if not self._stop_services():
            self.warning("Could not stop all services")
        
        # Step 4: Restore from snapshot
        self.step("Restoring from snapshot", 5)
        if not self._restore_snapshot(snapshot_path):
            self.error("Snapshot restore failed")
            return 1
        
        self.success("Snapshot restored")
        
        # Step 5: Restart services
        self.step("Restarting services", 6)
        if not self._start_services():
            self.error("Failed to start services")
            return 1
        
        self.success("Services restarted")
        
        # Step 6: Wait for services
        self.step("Waiting for services to stabilize", 7)
        time.sleep(10)
        
        # Step 7: Verify health
        self.step("Verifying service health", 8)
        if not self._verify_health():
            self.warning("Health verification failed, but rollback completed")
        else:
            self.success("All services healthy")
        
        self.success(f"Rollback completed successfully to {snapshot_id}")
        return 0
    
    def list_snapshots(self) -> int:
        """List available snapshots"""
        self.step("Available snapshots", 1)
        
        backup_dir = Path(self.config.get('backup_dir', './backups'))
        
        if not backup_dir.exists():
            self.info("No backups found")
            return 0
        
        snapshots = []
        
        # Find all backup directories
        for backup_path in sorted(backup_dir.glob('backup_*'), reverse=True):
            if backup_path.is_dir():
                metadata_file = backup_path / 'backup.json'
                
                try:
                    if metadata_file.exists():
                        with open(metadata_file) as f:
                            metadata = json.load(f)
                        
                        timestamp = metadata.get('timestamp', 'unknown')
                        size = metadata.get('size', 'unknown')
                        
                        snapshots.append({
                            'id': backup_path.name,
                            'timestamp': timestamp,
                            'size': size,
                            'valid': self._validate_snapshot(backup_path)
                        })
                except Exception as e:
                    self.warning(f"Could not read metadata for {backup_path.name}: {e}")
        
        if not snapshots:
            self.info("No snapshots available")
            return 0
        
        self.info(f"Found {len(snapshots)} snapshot(s):\n")
        
        for i, snapshot in enumerate(snapshots, 1):
            status = "✓" if snapshot['valid'] else "✗"
            self.info(f"  {status} {snapshot['id']}")
            self.info(f"      Timestamp: {snapshot['timestamp']}")
            self.info(f"      Size: {snapshot['size']}\n")
        
        return 0
    
    def _find_snapshot(self, snapshot_id: str) -> Path:
        """Find snapshot by ID"""
        backup_dir = Path(self.config.get('backup_dir', './backups'))
        snapshot_path = backup_dir / snapshot_id
        
        if snapshot_path.exists():
            return snapshot_path
        
        return None
    
    def _validate_snapshot(self, snapshot_path: Path) -> bool:
        """Validate snapshot integrity"""
        try:
            # Check if metadata exists
            metadata_file = snapshot_path / 'backup.json'
            if not metadata_file.exists():
                self.warning(f"  No metadata file in snapshot")
                return False
            
            # Parse and validate metadata
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            if 'backups' not in metadata:
                self.warning(f"  Invalid metadata format")
                return False
            
            # Check backup files exist
            backups = metadata.get('backups', {})
            missing_files = []
            
            for backup_name, backup_info in backups.items():
                file_path = snapshot_path / backup_info.get('path', '')
                if not file_path.exists():
                    missing_files.append(backup_info.get('path', 'unknown'))
            
            if missing_files:
                self.warning(f"  Missing files: {', '.join(missing_files)}")
                return False
            
            return True
        except Exception as e:
            self.error(f"  Snapshot validation error: {e}")
            return False
    
    def _stop_services(self) -> bool:
        """Stop services"""
        try:
            migration_prep = self.migration_home / 'migration_prep'
            
            if not Docker.compose_file_exists(migration_prep):
                self.warning("  docker-compose-prod.yml not found")
                return False
            
            rc = Docker.run_compose(['down'], migration_prep)
            return rc == 0
        except Exception as e:
            self.error(f"  Stop services error: {e}")
            return False
    
    def _restore_snapshot(self, snapshot_path: Path) -> bool:
        """Restore from snapshot"""
        try:
            import shutil
            
            # Find source and database backups in snapshot
            migration_prep = self.migration_home / 'migration_prep'
            
            # Restore migration_prep if backup exists
            source_backup = snapshot_path / 'migration_prep.tar.gz'
            if source_backup.exists():
                # Clean old migration_prep
                if migration_prep.exists():
                    shutil.rmtree(migration_prep)
                
                # Extract backup
                rc, stdout, stderr = run_command_output(
                    f"cd {self.migration_home} && tar -xzf {source_backup}"
                )
                
                if rc != 0:
                    self.error(f"  Source restore failed: {stderr}")
                    return False
                
                self.info("  Migration source restored")
            
            # Restore databases
            self._restore_databases(snapshot_path)
            
            return True
        except Exception as e:
            self.error(f"  Restore error: {e}")
            return False
    
    def _restore_databases(self, snapshot_path: Path) -> bool:
        """Restore databases from snapshot"""
        try:
            # Restore PostgreSQL databases
            for db_file in snapshot_path.glob('*.sql'):
                db_name = db_file.stem
                
                if check_command_exists('psql'):
                    cmd = f"psql -U postgres < {db_file}"
                    rc, stdout, stderr = run_command_output(cmd)
                    
                    if rc == 0:
                        self.info(f"  Database {db_name} restored")
                    else:
                        self.warning(f"  Database {db_name} restore failed")
            
            # Restore SQLite database
            sqlite_backup = snapshot_path / 'melissa.db'
            if sqlite_backup.exists():
                import shutil
                melissa_db = self.migration_home / 'melissa.db'
                shutil.copy2(sqlite_backup, melissa_db)
                self.info("  SQLite database restored")
            
            return True
        except Exception as e:
            self.warning(f"  Database restore error: {e}")
            return True  # Don't fail the whole restore
    
    def _start_services(self) -> bool:
        """Start services"""
        try:
            migration_prep = self.migration_home / 'migration_prep'
            
            if not Docker.compose_file_exists(migration_prep):
                self.error("  docker-compose-prod.yml not found")
                return False
            
            rc = Docker.run_compose(['up', '-d'], migration_prep)
            return rc == 0
        except Exception as e:
            self.error(f"  Start services error: {e}")
            return False
    
    def _verify_health(self) -> bool:
        """Verify service health after rollback"""
        try:
            migration_prep = self.migration_home / 'migration_prep'
            return Docker.is_healthy(migration_prep)
        except Exception as e:
            self.warning(f"  Health verification error: {e}")
            return False

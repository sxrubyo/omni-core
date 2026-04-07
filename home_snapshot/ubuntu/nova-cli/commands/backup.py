"""Backup creation command"""

import sys
import os
import json
import subprocess
import hashlib
import gzip
import shutil
from pathlib import Path
from datetime import datetime

# Add paths for imports
_lib_path = Path(__file__).parent.parent / 'lib'
if str(_lib_path) not in sys.path:
    sys.path.insert(0, str(_lib_path))

from logger import Logger
from config import Config
from .base import BaseCommand
from utils import check_command_exists, run_command_output, get_file_size


class BackupCommand(BaseCommand):
    """Create backups of sources and databases"""
    
    @staticmethod
    def run(logger: Logger, config: Config, args: list) -> int:
        """Execute backup creation"""
        cmd = BackupCommand(logger, config)
        
        # Parse arguments
        compress = '--compress' in args
        encrypt = '--encrypt' in args
        
        return cmd.execute(compress=compress, encrypt=encrypt)
    
    def execute(self, compress: bool = False, encrypt: bool = False) -> int:
        """Run backup creation"""
        self.step("Starting backup process", 1)
        
        backup_dir = Path(self.config.get('backup_dir', './backups'))
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}"
        backup_path = backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        self.info(f"Backup directory: {backup_path}")
        
        metadata = {
            'timestamp': timestamp,
            'backup_name': backup_name,
            'compress': compress,
            'encrypt': encrypt,
            'backups': {}
        }
        
        # Step 1: Source backup (migration_prep)
        self.step("Backing up migration_prep source", 2)
        migration_prep = self.migration_home / 'migration_prep'
        
        if migration_prep.exists():
            source_backup = self._backup_directory(migration_prep, backup_path / 'migration_prep.tar.gz')
            if source_backup:
                metadata['backups']['source'] = {
                    'path': 'migration_prep.tar.gz',
                    'size': get_file_size(source_backup),
                    'checksum': self._calculate_checksum(source_backup)
                }
                self.success(f"Source backup: {metadata['backups']['source']['size']}")
            else:
                self.error("Failed to backup migration_prep")
                return 1
        else:
            self.warning("migration_prep directory not found")
        
        # Step 2: Database backups
        self.step("Backing up databases", 3)
        db_backups = self._backup_databases(backup_path)
        metadata['backups'].update(db_backups)
        
        if db_backups:
            self.success(f"Database backups completed")
        
        # Step 3: SQLite backup
        self.step("Backing up SQLite database", 4)
        sqlite_backup = self._backup_sqlite(backup_path)
        if sqlite_backup:
            metadata['backups']['sqlite'] = sqlite_backup
            self.success(f"SQLite backup: {sqlite_backup['size']}")
        
        # Step 4: Compression
        if compress:
            self.step("Compressing backup", 5)
            if self._compress_backup(backup_path):
                self.success("Backup compressed")
            else:
                self.warning("Compression failed")
        
        # Step 5: Encryption
        if encrypt:
            self.step("Encrypting backup", 6)
            if self._encrypt_backup(backup_path):
                self.success("Backup encrypted")
            else:
                self.warning("Encryption failed")
        
        # Step 6: Write metadata
        self.step("Writing backup metadata", 7)
        metadata_file = backup_path / 'backup.json'
        metadata['size'] = self._get_directory_size(backup_path)
        
        try:
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.success(f"Backup metadata written to {metadata_file}")
        except Exception as e:
            self.error(f"Failed to write metadata: {e}")
            return 1
        
        self.success(f"Backup completed: {backup_path}")
        return 0
    
    def _backup_directory(self, source_dir: Path, output_file: Path) -> Path:
        """Backup directory to tar.gz"""
        try:
            cmd = f"tar -czf {output_file} -C {source_dir.parent} {source_dir.name}"
            rc, stdout, stderr = run_command_output(cmd)
            
            if rc == 0 and output_file.exists():
                return output_file
            else:
                self.error(f"tar command failed: {stderr}")
                return None
        except Exception as e:
            self.error(f"Backup directory error: {e}")
            return None
    
    def _backup_databases(self, backup_path: Path) -> dict:
        """Backup PostgreSQL databases if available"""
        backups = {}
        
        # Check if PostgreSQL is available
        if not check_command_exists('pg_dump'):
            self.info("  PostgreSQL not found, skipping pg_dump")
            return backups
        
        try:
            # Try to dump databases
            databases = ['nova_db', 'nova_analytics']
            
            for db in databases:
                output_file = backup_path / f"{db}.sql"
                cmd = f"pg_dump {db} > {output_file}"
                rc, stdout, stderr = run_command_output(cmd)
                
                if rc == 0 and output_file.exists():
                    backups[f'database_{db}'] = {
                        'path': f"{db}.sql",
                        'size': get_file_size(output_file),
                        'checksum': self._calculate_checksum(output_file)
                    }
                    self.info(f"  {db} backed up: {backups[f'database_{db}']['size']}")
        except Exception as e:
            self.warning(f"Database backup error: {e}")
        
        return backups
    
    def _backup_sqlite(self, backup_path: Path) -> dict:
        """Backup SQLite database if it exists"""
        melissa_db = self.migration_home / 'melissa.db'
        
        if not melissa_db.exists():
            return {}
        
        try:
            output_file = backup_path / 'melissa.db'
            shutil.copy2(melissa_db, output_file)
            
            return {
                'path': 'melissa.db',
                'size': get_file_size(output_file),
                'checksum': self._calculate_checksum(output_file)
            }
        except Exception as e:
            self.warning(f"SQLite backup error: {e}")
            return {}
    
    def _compress_backup(self, backup_path: Path) -> bool:
        """Compress backup directory"""
        try:
            parent = backup_path.parent
            backup_name = backup_path.name
            
            cmd = f"cd {parent} && tar -czf {backup_name}.tar.gz {backup_name}"
            rc, stdout, stderr = run_command_output(cmd)
            
            if rc == 0:
                compressed_file = parent / f"{backup_name}.tar.gz"
                if compressed_file.exists():
                    shutil.rmtree(backup_path)
                    return True
            
            self.error(f"Compression failed: {stderr}")
            return False
        except Exception as e:
            self.error(f"Compression error: {e}")
            return False
    
    def _encrypt_backup(self, backup_path: Path) -> bool:
        """Encrypt backup with GPG"""
        if not check_command_exists('gpg'):
            self.warning("GPG not found, skipping encryption")
            return False
        
        try:
            # Create encrypted archive
            cmd = f"tar -cf - {backup_path} | gpg --symmetric --cipher-algo AES256 > {backup_path}.tar.gpg"
            rc, stdout, stderr = run_command_output(cmd)
            
            if rc == 0:
                encrypted_file = Path(f"{backup_path}.tar.gpg")
                if encrypted_file.exists():
                    shutil.rmtree(backup_path)
                    return True
            
            self.error(f"Encryption failed: {stderr}")
            return False
        except Exception as e:
            self.error(f"Encryption error: {e}")
            return False
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.warning(f"Checksum calculation error: {e}")
            return ""
    
    def _get_directory_size(self, directory: Path) -> str:
        """Get total size of directory"""
        try:
            total_size = 0
            for path in directory.rglob('*'):
                if path.is_file():
                    total_size += path.stat().st_size
            
            return get_file_size(Path(f"/tmp/{total_size}"))  # Hacky but works with existing util
        except Exception as e:
            self.warning(f"Directory size calculation error: {e}")
            return "unknown"

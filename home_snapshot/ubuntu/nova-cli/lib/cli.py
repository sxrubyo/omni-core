"""Main Nova CLI module"""

import sys
import argparse
from pathlib import Path

from logger import Logger
from config import Config
from commands import (
    PreflightCommand,
    BackupCommand,
    MigrateCommand,
    VerifyCommand,
    RollbackCommand,
)

class NovaCLI:
    """Main CLI handler"""
    
    VERSION = "1.0.0"
    DESCRIPTION = """
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║   NOVA CLI - Enterprise Migration & Fleet Management Tool            ║
    ║                                                                       ║
    ║   Simplify complex infrastructure migrations with automated          ║
    ║   preflight checks, backups, deployment, verification, and           ║
    ║   rollback capabilities.                                             ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self):
        self.logger = Logger()
        self.config = Config()
        self.commands = {
            'preflight': PreflightCommand,
            'backup': BackupCommand,
            'migrate': MigrateCommand,
            'verify': VerifyCommand,
            'rollback': RollbackCommand,
        }
    
    def run(self, args):
        """Main entry point"""
        parser = self._build_parser()
        parsed = parser.parse_args(args)
        
        # Global options
        if parsed.verbose:
            self.logger.set_level('DEBUG')
        
        if parsed.version:
            print(f"Nova CLI v{self.VERSION}")
            return 0
        
        # Run command
        if hasattr(parsed, 'command_func'):
            try:
                return parsed.command_func(self.logger, self.config, parsed)
            except Exception as e:
                self.logger.error(str(e))
                if parsed.verbose:
                    import traceback
                    traceback.print_exc()
                return 1
        else:
            parser.print_help()
            return 1
    
    def _build_parser(self):
        """Build argument parser"""
        parser = argparse.ArgumentParser(
            description=self.DESCRIPTION,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
EXAMPLES:
  # Validate migration readiness
  nova preflight --path /home/ubuntu/migration_prep

  # Create backup
  nova backup --source /home/ubuntu/migration_prep --dest ./backups --compress

  # Execute full migration
  nova migrate --source /home/ubuntu/migration_prep --dest-host 192.168.1.100

  # Verify post-migration health
  nova verify --path /home/ubuntu/migration_prep

  # Rollback to snapshot
  nova rollback --snapshot ./backups/snapshot_20260319_142505

DOCUMENTATION:
  For detailed documentation, run: nova <command> --help
  Full docs: https://github.com/your-org/nova-cli
            """
        )
        
        parser.add_argument('-v', '--verbose', action='store_true',
                           help='Enable verbose output (DEBUG level)')
        parser.add_argument('--version', action='store_true',
                           help='Show version and exit')
        parser.add_argument('--no-color', action='store_true',
                           help='Disable colored output')
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Preflight command
        preflight = subparsers.add_parser('preflight',
            help='Validate migration readiness and target server')
        preflight.add_argument('--path', required=True,
            help='Path to migration_prep directory')
        preflight.add_argument('--target-host', '--host',
            help='Target server hostname/IP for port validation')
        preflight.set_defaults(command_func=PreflightCommand.run)
        
        # Backup command
        backup = subparsers.add_parser('backup',
            help='Create backup of migration_prep')
        backup.add_argument('--source', '-s', required=True,
            help='Source path (migration_prep directory)')
        backup.add_argument('--dest', '-d', required=True,
            help='Backup destination directory')
        backup.add_argument('--compress', '-c', action='store_true',
            help='Compress backup with gzip')
        backup.add_argument('--encrypt', '-e', action='store_true',
            help='Encrypt backup with GPG (requires gnupg installed)')
        backup.add_argument('--include-databases', action='store_true',
            help='Include database dumps in backup')
        backup.set_defaults(command_func=BackupCommand.run)
        
        # Migrate command
        migrate = subparsers.add_parser('migrate',
            help='Execute full migration to target server')
        migrate.add_argument('--source', '-s', required=True,
            help='Source path (migration_prep directory)')
        migrate.add_argument('--dest-host', '-H', required=True,
            help='Destination server hostname/IP')
        migrate.add_argument('--dest-user', '-u', default='ubuntu',
            help='SSH user for destination (default: ubuntu)')
        migrate.add_argument('--dest-path', '-p', default='/home/ubuntu/migration_prep',
            help='Destination path (default: /home/ubuntu/migration_prep)')
        migrate.add_argument('--ssh-key', '-k',
            help='SSH private key path')
        migrate.add_argument('--ssh-port', default=22, type=int,
            help='SSH port (default: 22)')
        migrate.add_argument('--dry-run', action='store_true',
            help='Simulate migration without making changes')
        migrate.add_argument('--skip-backup', action='store_true',
            help='Skip creating backup on source')
        migrate.set_defaults(command_func=MigrateCommand.run)
        
        # Verify command
        verify = subparsers.add_parser('verify',
            help='Post-migration verification')
        verify.add_argument('--path', '-p', required=True,
            help='Path to migration_prep')
        verify.add_argument('--comprehensive', action='store_true',
            help='Run comprehensive health checks (slower)')
        verify.add_argument('--test-endpoints', action='store_true',
            help='Test all service API endpoints')
        verify.set_defaults(command_func=VerifyCommand.run)
        
        # Rollback command
        rollback = subparsers.add_parser('rollback',
            help='Rollback to previous snapshot')
        rollback.add_argument('--snapshot', '-s', required=True,
            help='Snapshot path to restore')
        rollback.add_argument('--list', action='store_true',
            help='List available snapshots')
        rollback.add_argument('--force', action='store_true',
            help='Force rollback without confirmation')
        rollback.set_defaults(command_func=RollbackCommand.run)
        
        return parser

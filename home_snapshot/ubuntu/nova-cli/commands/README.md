# Nova CLI Commands

Complete implementation of 5 production-ready Nova CLI commands for deployment, backup, migration, verification, and rollback.

## Quick Start

### Files

- **base.py** - Abstract base class for all commands
- **preflight.py** - Server readiness validation
- **backup.py** - Backup creation with optional compression and encryption
- **migrate.py** - Full server migration execution
- **verify.py** - Post-migration health verification
- **rollback.py** - Snapshot rollback functionality

### Usage

```python
from lib.logger import Logger
from lib.config import Config
from commands.preflight import PreflightCommand

logger = Logger('nova-cli')
config = Config()

# Run any command
exit_code = PreflightCommand.run(logger, config, [])
```

## Commands

### preflight
Validates server readiness before migration
```bash
nova preflight
```

### backup
Creates comprehensive backups
```bash
nova backup [--compress] [--encrypt]
```

### migrate
Executes full migration to target server
```bash
nova migrate <target_host> [--skip-preflight] [--skip-backup]
```

### verify
Post-migration verification
```bash
nova verify
```

### rollback
Rollback to previous snapshot
```bash
nova rollback [snapshot_id]
```

## Documentation

See `COMMANDS_REFERENCE.md` for complete documentation with examples.

## Features

- ✓ Abstract base class for consistency
- ✓ Static entry points for easy integration
- ✓ Comprehensive error handling
- ✓ Full logging with colors
- ✓ Type hints throughout
- ✓ Proper exit codes
- ✓ Integration with existing libraries

## Testing

All commands have been validated for:
- Syntax correctness
- Proper imports
- Class instantiation
- Method signatures
- Return types

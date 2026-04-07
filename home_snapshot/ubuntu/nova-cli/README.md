# Nova CLI - Enterprise Migration & Fleet Management Tool

> Automate complex infrastructure migrations with confidence

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Status](https://img.shields.io/badge/status-production-green.svg)

## 🎯 Overview

Nova CLI is a comprehensive command-line tool designed to simplify enterprise infrastructure migrations. Built for teams managing complex Docker-based systems with multiple services, databases, and configurations.

**Key Features:**
- ✅ Pre-migration validation (preflight checks)
- ✅ Automated backup & restore
- ✅ Full migration orchestration
- ✅ Post-migration verification
- ✅ Automatic rollback on failures
- ✅ Comprehensive logging & audit trails
- ✅ Multi-environment support

## 🚀 Quick Start

### Installation

```bash
# Clone or copy
cp -r /home/ubuntu/nova-cli ~/local/nova-cli
cd ~/local/nova-cli

# Make executable
chmod +x nova-cli

# Optional: Add to PATH
sudo cp nova-cli /usr/local/bin/nova
```

### Basic Usage

```bash
# Check migration readiness
./nova-cli preflight --path /path/to/migration_prep

# Create backup
./nova-cli backup --source /path/to/migration_prep --dest ./backups --compress

# Execute migration
./nova-cli migrate --source /path/to/migration_prep --dest-host target.server.com

# Verify health
./nova-cli verify --path /path/to/migration_prep
```

## 📖 Commands

- `preflight` - Validate migration readiness
- `backup` - Create backup
- `migrate` - Execute full migration
- `verify` - Post-migration verification
- `rollback` - Restore to previous snapshot

See [docs/COMMANDS.md](docs/COMMANDS.md) for detailed documentation.

## 🔐 Security

- SSH key management
- Backup encryption (GPG)
- Environment variable isolation
- Audit logging

## 📝 License

MIT License

---

**Version**: 1.0.0 | **Updated**: 2026-03-19

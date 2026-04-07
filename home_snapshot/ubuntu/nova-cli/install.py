"""Nova CLI Installation Script"""

import os
import sys
from pathlib import Path
import subprocess

def main():
    """Install Nova CLI"""
    
    print("🔧 Installing Nova CLI...")
    
    script_dir = Path(__file__).parent
    
    # Make main executable
    os.chmod(script_dir / 'nova-cli', 0o755)
    print("✓ nova-cli is executable")
    
    # Create directories
    (Path.home() / '.nova').mkdir(exist_ok=True)
    print("✓ Created ~/.nova/")
    
    # Optional: Install to /usr/local/bin
    if len(sys.argv) > 1 and sys.argv[1] == '--system':
        try:
            subprocess.run(['sudo', 'cp', str(script_dir / 'nova-cli'), '/usr/local/bin/nova'],
                         check=True)
            print("✓ Installed to /usr/local/bin/nova")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install to /usr/local/bin: {e}")
            return 1
    else:
        print("\nℹ To install system-wide: python3 install.py --system")
    
    print("\n✅ Nova CLI installed successfully!")
    print(f"\n📝 Usage: {script_dir}/nova-cli --help")
    return 0

if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv


def verify_environment() -> List[str]:
    """Verify required environment variables are set."""
    required_vars = ["GH_TOKEN", "PYPI_TOKEN"]
    return [var for var in required_vars if not os.getenv(var)]


def find_dotenv() -> Optional[Path]:
    """Find .env file in current or parent directories."""
    current = Path.cwd()
    while current != current.parent:
        env_file = current / ".env"
        if env_file.exists():
            return env_file
        current = current.parent
    return None


def print_help():
    """Print usage information."""
    print("""
📦 ONVIF Scout Release Tool

Commands:
  changelog   Generate changelog only
  version    Update version and changelog
  publish    Full release (version + changelog + build + publish)

Example usage:
  python scripts/release.py changelog
  python scripts/release.py publish

Environment:
  Required variables in .env file:
  - GH_TOKEN: GitHub personal access token
  - PYPI_TOKEN: PyPI API token
""")


def main():
    # Show help if no arguments or help requested
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print_help()
        sys.exit(0)

    # Find and load .env file
    env_file = find_dotenv()
    if not env_file:
        print("❌ Error: No .env file found in current or parent directories")
        print("Please create a .env file with GH_TOKEN and PYPI_TOKEN")
        sys.exit(1)

    # Load environment variables
    load_dotenv(env_file)

    # Verify required environment variables
    missing_vars = verify_environment()
    if missing_vars:
        print("❌ Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print(f"\nPlease add them to your .env file at: {env_file}")
        sys.exit(1)

    # Validate command
    valid_commands = ["changelog", "version", "publish"]
    command = sys.argv[1]
    if command not in valid_commands:
        print(f"❌ Error: Unknown command '{command}'")
        print(f"Valid commands are: {', '.join(valid_commands)}")
        sys.exit(1)

    # Run semantic-release
    try:
        print(f"🚀 Running: semantic-release {' '.join(sys.argv[1:])}")
        cmd = ["semantic-release"] + sys.argv[1:]
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print(result.stdout)
        if result.stderr:
            print("Warnings/Errors:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
        print("\n✨ Release process completed successfully!")
    except subprocess.CalledProcessError as e:
        print("\n❌ Release process failed!")
        if e.stdout:
            print("\nOutput:")
            print(e.stdout)
        if e.stderr:
            print("\nErrors:")
            print(e.stderr)
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

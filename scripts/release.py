#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

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


def get_current_version() -> str:
    """Extract current version from setup.py."""
    with open("setup.py", "r") as f:
        content = f.read()
        match = re.search(r'version="(\d+\.\d+\.\d+)"', content)
        if match:
            return match.group(1)
    return "0.0.0"  # Fallback if version not found


def update_version(version_type: str) -> Optional[str]:
    """Update version based on version type (major, minor, patch)."""
    current = get_current_version()
    major, minor, patch = map(int, current.split("."))

    if version_type == "major":
        new_version = f"{major + 1}.0.0"
    elif version_type == "minor":
        new_version = f"{major}.{minor + 1}.0"
    elif version_type == "patch":
        new_version = f"{major}.{minor}.{patch + 1}"
    else:
        return None

    # Update version in setup.py
    with open("setup.py", "r") as f:
        content = f.read()

    content = re.sub(r'version="(\d+\.\d+\.\d+)"', f'version="{new_version}"', content)

    with open("setup.py", "w") as f:
        f.write(content)

    return new_version


def update_changelog(version: str) -> bool:
    """Update CHANGELOG.md with new version."""
    now = datetime.now().strftime("%Y-%m-%d")

    # Get commit logs since last tag
    try:
        last_tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        commits = subprocess.check_output(
            ["git", "log", f"{last_tag}..HEAD", "--oneline"], text=True
        ).strip()
    except subprocess.CalledProcessError:
        # No tags yet, get all commits
        commits = subprocess.check_output(
            ["git", "log", "--oneline"], text=True
        ).strip()

    if not commits:
        print("No changes since last release")
        return False

    # Categorize commits
    features = []
    fixes = []
    others = []

    for line in commits.split("\n"):
        if not line.strip():
            continue

        if "feat" in line.lower():
            features.append(line)
        elif "fix" in line.lower():
            fixes.append(line)
        else:
            others.append(line)

    # Read current changelog
    try:
        with open("CHANGELOG.md", "r") as f:
            content = f.read()
    except FileNotFoundError:
        content = "# Changelog\n\n"

    # Prepare new entry
    entry = f"## {version} - {now}\n\n"

    if features:
        entry += "### Features\n\n"
        for feat in features:
            entry += f"* {feat}\n"
        entry += "\n"

    if fixes:
        entry += "### Bug Fixes\n\n"
        for fix in fixes:
            entry += f"* {fix}\n"
        entry += "\n"

    if others:
        entry += "### Other Changes\n\n"
        for other in others:
            entry += f"* {other}\n"
        entry += "\n"

    # Insert new entry after header
    if "# Changelog" in content:
        # Ensure we insert after the header line, preserving existing content
        content = re.sub(r"# Changelog\n+", f"# Changelog\n\n{entry}", content)
    else:
        # If no header exists, create it
        content = f"# Changelog\n\n{entry}\n" + content

    with open("CHANGELOG.md", "w") as f:
        f.write(content)

    return True


def create_release(version: str, prerelease: bool = False) -> bool:
    """Create a new release on GitHub."""
    # Create and push tag
    tag = f"v{version}"
    try:
        subprocess.run(["git", "add", "setup.py", "CHANGELOG.md"], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore(release): {version}"], check=True
        )
        subprocess.run(["git", "tag", tag], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        subprocess.run(["git", "push", "origin", tag], check=True)
        print(f"✅ Created and pushed tag {tag}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create/push tag: {e}")
        return False

    # Extract changelog entry for this version
    with open("CHANGELOG.md", "r") as f:
        content = f.read()

    section_pattern = re.compile(rf"## {version} - .*?(?=## |\Z)", re.DOTALL)
    match = section_pattern.search(content)
    release_notes = match.group(0).strip() if match else ""

    # Create GitHub release
    try:
        cmd = [
            "gh",
            "release",
            "create",
            tag,
            "--title",
            f"ONVIFScout {version}",
            "--notes",
            release_notes or f"Release {version}",
        ]

        if prerelease:
            cmd.append("--prerelease")

        subprocess.run(cmd, check=True, env=os.environ)
        print(f"✅ Created GitHub release {version}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create GitHub release: {e}")
        return False


def build_and_publish() -> bool:
    """Build and publish package to PyPI."""
    try:
        # Build package
        subprocess.run(["python", "-m", "build", "--wheel", "--sdist"], check=True)
        print("✅ Built package")

        # Publish to PyPI
        subprocess.run(
            ["python", "-m", "twine", "upload", "dist/*"], check=True, env=os.environ
        )
        print("✅ Published to PyPI")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build/publish package: {e}")
        return False


def print_help():
    """Print usage information."""
    print("""
📦 ONVIF Scout Release Tool

Commands:
  changelog   Generate/update changelog only
  version     Update version and changelog
  release     Create a GitHub release (version + changelog + git tag + GitHub release)
  publish     Full release process (version + changelog + release + PyPI publish)

Arguments:
  --type      Release type: major, minor, patch (default: patch)
  --pre       Mark as pre-release (default: false)
  --dry-run   Only show what would be done (default: false)

Example usage:
  python scripts/release.py changelog
  python scripts/release.py version --type minor
  python scripts/release.py release --type patch
  python scripts/release.py publish --type minor --pre
  python scripts/release.py --dry-run publish

Environment:
  Required variables in .env file:
  - GH_TOKEN: GitHub personal access token
  - PYPI_TOKEN: PyPI API token
""")


def parse_args() -> Tuple[str, dict]:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(add_help=False)

    # Add optional arguments
    parser.add_argument(
        "--type",
        choices=["major", "minor", "patch"],
        default="patch",
        help="Release type",
    )
    parser.add_argument("--pre", action="store_true", help="Mark as pre-release")
    parser.add_argument(
        "--dry-run", action="store_true", help="Only show what would be done"
    )
    parser.add_argument("-h", "--help", action="store_true", help="Show help message")

    # Add commands
    parser.add_argument(
        "command",
        nargs="?",
        choices=["changelog", "version", "release", "publish", "help"],
    )

    args = parser.parse_args()

    # Show help if requested
    if args.help or args.command in [None, "help"]:
        print_help()
        sys.exit(0)

    # Return command and options
    return args.command, {
        "version_type": args.type,
        "prerelease": args.pre,
        "dry_run": args.dry_run,
    }


def setup_environment():
    """Setup and verify the environment."""
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


def handle_changelog(dry_run=False):
    """Handle the changelog command."""
    if dry_run:
        print("🔍 Dry run: Would update CHANGELOG.md")
        return True

    version = get_current_version()
    if update_changelog(version):
        print("✅ Updated CHANGELOG.md")
        return True
    return False


def handle_version(version_type, dry_run=False):
    """Handle the version command."""
    if dry_run:
        print(f"🔍 Dry run: Would update version ({version_type})")
        print("🔍 Dry run: Would update CHANGELOG.md")
        return None

    version = update_version(version_type)
    if version:
        print(f"✅ Updated version to {version}")
        if update_changelog(version):
            print("✅ Updated CHANGELOG.md")
        return version
    return None


def handle_release(version_type, prerelease=False, dry_run=False):
    """Handle the release command."""
    if dry_run:
        print(f"🔍 Dry run: Would update version ({version_type})")
        print("🔍 Dry run: Would update CHANGELOG.md")
        print(f"🔍 Dry run: Would create GitHub release (prerelease: {prerelease})")
        return True

    version = update_version(version_type)
    if not version:
        return False

    print(f"✅ Updated version to {version}")
    if not update_changelog(version):
        return False

    print("✅ Updated CHANGELOG.md")
    if create_release(version, prerelease):
        print("✅ Created GitHub release")
        return True
    return False


def handle_publish(version_type, prerelease=False, dry_run=False):
    """Handle the publish command."""
    if dry_run:
        print(f"🔍 Dry run: Would update version ({version_type})")
        print("🔍 Dry run: Would update CHANGELOG.md")
        print(f"🔍 Dry run: Would create GitHub release (prerelease: {prerelease})")
        print("🔍 Dry run: Would build and publish to PyPI")
        return True

    version = update_version(version_type)
    if not version:
        return False

    print(f"✅ Updated version to {version}")
    if not update_changelog(version):
        return False

    print("✅ Updated CHANGELOG.md")
    if not create_release(version, prerelease):
        return False

    print("✅ Created GitHub release")
    if build_and_publish():
        print(f"✅ Published version {version} to PyPI")
        return True
    return False


def main():
    """Main entry point for the script."""
    # Parse arguments
    command, options = parse_args()
    dry_run = options["dry_run"]

    # Setup environment
    setup_environment()

    # Process command
    try:
        handlers = {
            "changelog": lambda: handle_changelog(dry_run),
            "version": lambda: handle_version(options["version_type"], dry_run),
            "release": lambda: handle_release(
                options["version_type"], options["prerelease"], dry_run
            ),
            "publish": lambda: handle_publish(
                options["version_type"], options["prerelease"], dry_run
            ),
        }

        if command in handlers:
            result = handlers[command]()
            if not result and not dry_run:
                sys.exit(1)
        else:
            print(f"❌ Unknown command: {command}")
            print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        if os.getenv("DEBUG"):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

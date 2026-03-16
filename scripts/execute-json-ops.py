#!/usr/bin/env python3
"""
execute-json-ops.py - Execute JSON operations config (v3.0)

Purpose: Execute file create, delete, and code edit operations
Usage: python3 scripts/execute-json-ops.py path/to/ops.json [--dry-run]

Supports Two Formats:
  - LEGACY: {"plan": "...", "files": [...]} - Code edits only
  - MODERN: {"plan": "...", "operations": [...]} - file_create, file_delete, code_edit

Features:
  - Auto-detects format and normalizes to modern format internally
  - Automatic backup before all operations (including deleted files)
  - Backup manifest generation (compatible with restore-backup.py)
  - Dry-run mode with diff preview for code edits
  - Transactional execution with automatic rollback on failure
  - Execution lock to prevent concurrent runs
"""

import argparse
import difflib
import fcntl
import fnmatch
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

LOCK_FILE = ".codemanifest.lock"


class ExecutionLock:
    """File-based lock to prevent concurrent executor runs."""

    def __init__(self, lock_path: str = LOCK_FILE):
        self.lock_path = lock_path
        self._fd: Optional[int] = None

    def acquire(self) -> bool:
        try:
            self._fd = os.open(self.lock_path, os.O_CREAT | os.O_WRONLY)
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(self._fd, f"{os.getpid()}\n".encode())
            return True
        except (OSError, IOError):
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            return False

    def release(self):
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
            except (OSError, IOError):
                pass
            self._fd = None
            try:
                os.unlink(self.lock_path)
            except OSError:
                pass

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(
                f"Another CodeManifest executor is running (lock: {self.lock_path}).\n"
                "Wait for it to finish or remove the lock file if stale."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


class OperationTransaction:
    """Track executed operations for transactional rollback."""

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self._modified_files: List[str] = []
        self._created_files: List[str] = []

    def record_modified(self, file_path: str):
        self._modified_files.append(file_path)

    def record_created(self, file_path: str):
        self._created_files.append(file_path)

    def rollback(self):
        print("\n  ROLLBACK: Restoring files from backup...")
        for fp in self._modified_files:
            rel = Path(os.path.relpath(fp))
            bp = self.backup_dir / rel
            if bp.exists():
                try:
                    shutil.copy(str(bp), fp)
                    print(f"  Restored: {fp}")
                except Exception as e:
                    print(f"  Warning: Failed to restore {fp}: {e}")
        for fp in self._created_files:
            if os.path.exists(fp):
                try:
                    os.unlink(fp)
                    print(f"  Removed: {fp}")
                except Exception as e:
                    print(f"  Warning: Failed to remove {fp}: {e}")
        print("  ROLLBACK COMPLETE")

    @property
    def modified_files(self) -> List[str]:
        return list(self._modified_files)

    @property
    def created_files(self) -> List[str]:
        return list(self._created_files)

# Protected file patterns (cannot be deleted via ops config)
PROTECTED_PATTERNS = [
    ".gitignore",
    "*.md",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "Pipfile.lock",
    "tsconfig.json",
]


def is_protected_file(file_path: str) -> bool:
    """
    Check if file matches protected patterns.
    Protected files CANNOT be deleted via operations config.
    """
    file_name = os.path.basename(file_path)
    for pattern in PROTECTED_PATTERNS:
        if fnmatch.fnmatch(file_name, pattern):
            return True
    return False


def validate_path(file_path: str) -> bool:
    """
    Validate file path for safety.
    Rejects path traversal and null bytes.
    """
    if '\x00' in file_path:
        print(f"  BLOCKED: Path contains null bytes: {file_path!r}")
        return False
    rel = os.path.relpath(file_path)
    if rel.startswith('..'):
        print(f"  BLOCKED: Path traversal detected: {file_path}")
        return False
    if os.path.islink(file_path):
        resolved = os.path.realpath(file_path)
        cwd = os.path.realpath(os.getcwd())
        if not resolved.startswith(cwd + os.sep):
            print(f"  BLOCKED: Symlink points outside project: {file_path} -> {resolved}")
            return False
    return True


def normalize_config(config: dict) -> dict:
    """
    Convert legacy format to modern format for unified processing.

    Legacy: {"plan": "...", "files": [...]}
    Modern: {"plan": "...", "operations": [{"type": "code_edit", ...}]}
    """
    if 'operations' in config:
        return config

    operations = []
    for file_op in config.get('files', []):
        operations.append({
            'type': 'code_edit',
            'path': file_op['path'],
            'edits': file_op['edits']
        })

    return {
        'plan': config.get('plan', 'unknown'),
        'operations': operations
    }


def create_manifest(backup_dir: Path, plan_name: str, files_to_backup: List[str], files_to_create: List[str]) -> bool:
    """Create manifest.json for backup compatibility with restore-backup.py.

    Returns:
        True if manifest was created successfully, False otherwise.
    """
    manifest = {
        'plan': plan_name,
        'timestamp': datetime.now().isoformat(),
        'files': files_to_backup,
        'created_files': files_to_create
    }

    manifest_path = backup_dir / 'manifest.json'
    try:
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        print(f"  Manifest: {manifest_path}")
        return True
    except Exception as e:
        print(f"  Error: Could not create manifest: {e}")
        print("  Aborting execution — backup manifest is required for safe recovery.")
        return False


def show_diff(file_path: str, original: str, modified: str):
    """Show unified diff between original and modified content."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines, modified_lines,
        fromfile=f"a/{file_path}", tofile=f"b/{file_path}",
        lineterm=''
    )
    diff_lines = list(diff)
    if diff_lines:
        print("  --- Diff preview ---")
        for line in diff_lines[:50]:
            print(f"  {line.rstrip()}")
        if len(diff_lines) > 50:
            print(f"  ... ({len(diff_lines) - 50} more lines)")
        print("  --- End diff ---")


def execute_file_create(operation: dict, backup_dir: Path, dry_run: bool) -> Tuple[bool, str]:
    """Create new file with specified content."""
    file_path = Path(operation['path'])
    content = operation['content']

    if not validate_path(str(file_path)):
        return False, "path-validation-failed"

    byte_size = len(content.encode('utf-8'))

    if dry_run:
        print(f"  [DRY RUN] Would create: {file_path}")
        print(f"            Size: {byte_size} bytes, Lines: {content.count(chr(10)) + 1}")
        return True, "dry-run"

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        print(f"  Created: {file_path}")
        print(f"  Size: {byte_size} bytes, Lines: {content.count(chr(10)) + 1}")
        return True, "created"
    except Exception as e:
        print(f"  Error creating file: {e}")
        return False, str(e)


def execute_file_delete(operation: dict, backup_dir: Path, dry_run: bool) -> Tuple[bool, str]:
    """Back up then delete specified file."""
    file_path = Path(operation['path'])
    reason = operation.get('reason', '')

    if not validate_path(str(file_path)):
        return False, "path-validation-failed"

    # Check protected file patterns
    if is_protected_file(str(file_path)):
        print(f"  BLOCKED: Cannot delete protected file: {file_path}")
        return False, "protected-file"

    if dry_run:
        print(f"  [DRY RUN] Would delete: {file_path}")
        print(f"            Reason: {reason}")
        if file_path.exists():
            print(f"            Size: {file_path.stat().st_size} bytes")
        return True, "dry-run"

    if not file_path.exists():
        print(f"  File already deleted: {file_path}")
        return True, "already-deleted"

    # Backup before deletion
    try:
        rel_path = Path(os.path.relpath(file_path))
        backup_path = backup_dir / rel_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(file_path), str(backup_path))
        print(f"  Backed up to: {backup_path}")
    except Exception as e:
        print(f"  Error backing up file before deletion: {e}")
        print("  Aborting delete — cannot proceed without backup.")
        return False, str(e)

    try:
        file_size = file_path.stat().st_size
        file_path.unlink()

        print(f"  Deleted: {file_path}")
        print(f"  Reason: {reason}")
        print(f"  Freed: {file_size} bytes")
        return True, "deleted"
    except Exception as e:
        print(f"  Error deleting file: {e}")
        return False, str(e)


def execute_code_edit(operation: dict, backup_dir: Path, dry_run: bool) -> Tuple[bool, str]:
    """Apply find-replace edits to existing file."""
    file_path = Path(operation['path'])
    edits = operation.get('edits', [])

    if not validate_path(str(file_path)):
        return False, "path-validation-failed"

    if not file_path.exists():
        print(f"  File not found: {file_path}")
        return False, "file-not-found"

    # Backup original (preserve directory structure)
    if not dry_run:
        try:
            rel_path = Path(os.path.relpath(file_path))
            backup_path = backup_dir / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(file_path), str(backup_path))
            print(f"  Backed up to: {backup_path}")
        except Exception as e:
            print(f"  Error backing up file: {e}")
            print("  Aborting edit — cannot proceed without backup.")
            return False, str(e)

    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  Error reading file: {e}")
        return False, str(e)

    modified_content = content
    edits_applied = 0

    for j, edit in enumerate(edits, 1):
        find_pattern = edit.get('find', '')

        if not find_pattern:
            print(f"  Edit {j}: No 'find' pattern specified")
            continue

        if find_pattern not in modified_content:
            print(f"  Edit {j}: Pattern not found (may have been changed by previous edit)")
            continue

        if 'add_after' in edit:
            modified_content = modified_content.replace(
                find_pattern, find_pattern + edit['add_after'], 1
            )
            print(f"  Edit {j}: Added {len(edit['add_after'])} chars after pattern")
            edits_applied += 1

        elif 'add_before' in edit:
            modified_content = modified_content.replace(
                find_pattern, edit['add_before'] + find_pattern, 1
            )
            print(f"  Edit {j}: Added {len(edit['add_before'])} chars before pattern")
            edits_applied += 1

        elif 'replace' in edit:
            modified_content = modified_content.replace(
                find_pattern, edit['replace'], 1
            )
            print(f"  Edit {j}: Replaced pattern with {len(edit['replace'])} chars")
            edits_applied += 1

        elif edit.get('delete'):
            modified_content = modified_content.replace(find_pattern, '', 1)
            print(f"  Edit {j}: Deleted pattern")
            edits_applied += 1

        else:
            print(f"  Edit {j}: No action specified (add_after, add_before, replace, delete)")

    if edits_applied < len(edits):
        logger.warning(
            "Only %d of %d edits applied for %s", edits_applied, len(edits), file_path
        )
        print(f"  WARNING: Only {edits_applied}/{len(edits)} edits applied")

    if edits_applied == 0 and len(edits) > 0:
        print(f"  FAILED: No edits could be applied")
        return False, "no-edits-applied"

    byte_size = len(modified_content.encode('utf-8'))

    if dry_run:
        print(f"  [DRY RUN] Would write {byte_size} bytes to: {file_path}")
        if content != modified_content:
            show_diff(str(file_path), content, modified_content)
        return True, "dry-run"
    else:
        try:
            file_path.write_text(modified_content, encoding='utf-8')
            print(f"  Written {byte_size} bytes, {edits_applied}/{len(edits)} edits applied")
            if edits_applied < len(edits):
                return False, "partial-edits"
            return True, "edited"
        except Exception as e:
            print(f"  Error writing file: {e}")
            return False, str(e)


def execute_json_config(config_file: str, dry_run: bool = False) -> bool:
    """
    Execute JSON operations config.

    Args:
        config_file: Path to JSON config file
        dry_run: If True, preview changes without applying

    Returns:
        True if all operations succeeded
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            raw_config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return False

    config = normalize_config(raw_config)
    plan_name = config.get('plan', 'unknown')
    operations = config.get('operations', [])
    config_format = "MODERN" if 'operations' in raw_config else "LEGACY"

    print(f"Plan: {plan_name}")
    print(f"Format: {config_format}")
    print(f"Operations: {len(operations)}")

    if dry_run:
        print("DRY RUN MODE - No changes will be made\n")
    else:
        print()

    # Acquire execution lock (non-dry-run only)
    lock = None
    if not dry_run:
        lock = ExecutionLock()
        if not lock.acquire():
            print("Error: Another CodeManifest executor is running.")
            print(f"If this is stale, remove {LOCK_FILE}")
            return False

    try:
        return _execute_operations(config, operations, plan_name, config_format, dry_run)
    finally:
        if lock:
            lock.release()


def _execute_operations(config: dict, operations: list, plan_name: str,
                        config_format: str, dry_run: bool) -> bool:
    """Internal execution logic, called with lock held."""
    # Create backup directory (sanitize plan name for safe filesystem path)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    safe_plan_name = re.sub(r'[^a-zA-Z0-9_-]', '_', plan_name)
    backup_dir = Path("backups") / f"{safe_plan_name}-{timestamp}"

    if not dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"Backup directory: {backup_dir}\n")

    # Collect file lists for manifest
    files_to_backup = []
    files_to_create = []

    for operation in operations:
        op_type = operation.get('type', '')
        file_path = operation.get('path', '')
        if op_type in ('code_edit', 'file_delete') and file_path:
            files_to_backup.append(os.path.relpath(file_path))
        elif op_type == 'file_create' and file_path:
            files_to_create.append(os.path.relpath(file_path))

    if not dry_run:
        if not create_manifest(backup_dir, plan_name, files_to_backup, files_to_create):
            return False
        print()

    # Execute operations with transaction tracking
    txn = OperationTransaction(backup_dir)
    success_count = 0
    error_count = 0
    stats = {'file_create': 0, 'file_delete': 0, 'code_edit': 0}

    for i, operation in enumerate(operations, 1):
        op_type = operation.get('type', 'unknown')
        file_path = operation.get('path', 'unknown')

        print(f"[{i}/{len(operations)}] {op_type.upper()}: {file_path}")

        if op_type == 'file_create':
            success, status = execute_file_create(operation, backup_dir, dry_run)
            if success:
                stats['file_create'] += 1
                if status == "created":
                    txn.record_created(str(file_path))
        elif op_type == 'file_delete':
            success, status = execute_file_delete(operation, backup_dir, dry_run)
            if success:
                stats['file_delete'] += 1
                if status == "deleted":
                    txn.record_modified(str(file_path))
        elif op_type == 'code_edit':
            success, status = execute_code_edit(operation, backup_dir, dry_run)
            if success:
                stats['code_edit'] += 1
                if status == "edited":
                    txn.record_modified(str(file_path))
        else:
            print(f"  Unknown operation type: {op_type}")
            success = False

        if success:
            success_count += 1
        else:
            error_count += 1
            if not dry_run:
                txn.rollback()
            break

        print()

    # Summary
    print()
    print("-" * 50)
    print(f"{'DRY RUN COMPLETE' if dry_run else 'EXECUTION COMPLETE'}")
    print(f"Operations: {len(operations)} total")
    print(f"  file_create: {stats['file_create']}")
    print(f"  file_delete: {stats['file_delete']}")
    print(f"  code_edit:   {stats['code_edit']}")
    if not dry_run:
        print(f"Successful: {success_count}")
        print(f"Errors:     {error_count}")
        print(f"Backups:    {backup_dir}")
    print("-" * 50)

    return error_count == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Execute JSON operations config (v3.0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflow (always validate first):
  1. Validate: python3 scripts/validate-config-json.py ops.json
  2. Dry run:  python3 scripts/execute-json-ops.py ops.json --dry-run
  3. Execute:  python3 scripts/execute-json-ops.py ops.json

Operation Types:
  file_create: Create new file with content
  file_delete: Delete file (backed up first, with reason required)
  code_edit:   Edit existing file (find-replace patterns)

Edit Actions:
  add_after:  Insert content after matching pattern
  add_before: Insert content before matching pattern
  replace:    Replace matching pattern with new content
  delete:     Remove matching pattern

Safety:
  - Every modified/deleted file is backed up before changes
  - Backup manifest generated for restore-backup.py compatibility
  - Dry run mode available (--dry-run)
        """
    )
    parser.add_argument('config', help='Path to JSON operations config file')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    args = parser.parse_args()

    success = execute_json_config(args.config, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

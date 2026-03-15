#!/usr/bin/env python3
"""
execute-json-ops.py - Execute JSON operations config (v2.2)

Purpose: Execute file create, delete, and code edit operations
Usage: python3 scripts/execute-json-ops.py path/to/ops.json [--dry-run]

Supports Two Formats:
  - LEGACY: {"plan": "...", "files": [...]} - Code edits only
  - MODERN: {"plan": "...", "operations": [...]} - file_create, file_delete, code_edit

Features:
  - Auto-detects format and normalizes to modern format internally
  - Automatic backup before all operations (including deleted files)
  - Backup manifest generation (compatible with restore-backup.py)
  - Dry-run mode for previewing changes without applying them
  - Automatic rollback on failure (restores from backup)
"""

import argparse
import fnmatch
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

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


def create_manifest(backup_dir: Path, plan_name: str, files_to_backup: List[str], files_to_create: List[str]) -> None:
    """Create manifest.json for backup compatibility with restore-backup.py."""
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
    except Exception as e:
        print(f"  Warning: Could not create manifest: {e}")


def execute_file_create(operation: dict, backup_dir: Path, dry_run: bool) -> Tuple[bool, str]:
    """Create new file with specified content."""
    file_path = Path(operation['path'])
    content = operation['content']

    if dry_run:
        print(f"  [DRY RUN] Would create: {file_path}")
        print(f"            Size: {len(content)} bytes, Lines: {content.count(chr(10)) + 1}")
        return True, "dry-run"

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        print(f"  Created: {file_path}")
        print(f"  Size: {len(content)} bytes, Lines: {content.count(chr(10)) + 1}")
        return True, "created"
    except Exception as e:
        print(f"  Error creating file: {e}")
        return False, str(e)


def execute_file_delete(operation: dict, backup_dir: Path, dry_run: bool) -> Tuple[bool, str]:
    """Back up then delete specified file."""
    file_path = Path(operation['path'])
    reason = operation.get('reason', '')

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

    try:
        rel_path = Path(os.path.relpath(file_path))
        backup_path = backup_dir / rel_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(file_path), str(backup_path))
        print(f"  Backed up to: {backup_path}")

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

    if not file_path.exists():
        print(f"  File not found: {file_path}")
        return False, "file-not-found"

    # Backup original (preserve directory structure)
    if not dry_run:
        rel_path = Path(os.path.relpath(file_path))
        backup_path = backup_dir / rel_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(file_path), str(backup_path))
        print(f"  Backed up to: {backup_path}")

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

        elif 'delete' in edit:
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

    if dry_run:
        print(f"  [DRY RUN] Would write {len(modified_content)} bytes to: {file_path}")
        return True, "dry-run"
    else:
        try:
            file_path.write_text(modified_content, encoding='utf-8')
            print(f"  Written {len(modified_content)} bytes, {edits_applied}/{len(edits)} edits applied")
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

    # Create backup directory (sanitize plan name for safe filesystem path)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
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
        create_manifest(backup_dir, plan_name, files_to_backup, files_to_create)
        print()

    # Execute operations
    success_count = 0
    error_count = 0
    stats = {'file_create': 0, 'file_delete': 0, 'code_edit': 0}
    files_modified: List[str] = []
    files_created: List[str] = []

    for i, operation in enumerate(operations, 1):
        op_type = operation.get('type', 'unknown')
        file_path = operation.get('path', 'unknown')

        print(f"[{i}/{len(operations)}] {op_type.upper()}: {file_path}")

        if op_type == 'file_create':
            success, status = execute_file_create(operation, backup_dir, dry_run)
            if success:
                stats['file_create'] += 1
                if status == "created":
                    files_created.append(str(file_path))
        elif op_type == 'file_delete':
            success, status = execute_file_delete(operation, backup_dir, dry_run)
            if success:
                stats['file_delete'] += 1
                if status == "deleted":
                    files_modified.append(str(file_path))
        elif op_type == 'code_edit':
            success, status = execute_code_edit(operation, backup_dir, dry_run)
            if success:
                stats['code_edit'] += 1
                if status == "edited":
                    files_modified.append(str(file_path))
        else:
            print(f"  Unknown operation type: {op_type}")
            success = False

        if success:
            success_count += 1
        else:
            error_count += 1
            # Rollback on failure (only when actually modifying files)
            if not dry_run:
                print("\n  ROLLBACK: Restoring files from backup...")
                for fp in files_modified:
                    rel = Path(os.path.relpath(fp))
                    bp = backup_dir / rel
                    if bp.exists():
                        shutil.copy(str(bp), fp)
                        print(f"  Restored: {fp}")
                for fp in files_created:
                    if os.path.exists(fp):
                        os.unlink(fp)
                        print(f"  Removed: {fp}")
                print("  ROLLBACK COMPLETE")
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
        description='Execute JSON operations config (v2.1)',
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

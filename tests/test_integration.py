"""End-to-end integration test: validate -> execute -> restore."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import importlib
validator = importlib.import_module("validate-config-json")
executor = importlib.import_module("execute-json-ops")
restore = importlib.import_module("restore-backup")


class TestFullPipeline:
    """Chain validate -> execute -> restore end-to-end."""

    def test_validate_execute_restore_code_edit(self, tmp_path, monkeypatch):
        """Full round-trip: validate, execute code_edit, then restore."""
        monkeypatch.chdir(tmp_path)

        # Create a source file
        src = tmp_path / "src"
        src.mkdir()
        app = src / "app.py"
        original_content = 'VERSION = "1.0.0"\n\ndef greet(name):\n    return "Hello, " + name\n'
        app.write_text(original_content)

        # Create ops.json
        ops_dir = tmp_path / "operations" / "integration-test"
        ops_dir.mkdir(parents=True)
        config = {
            "plan": "integration-test",
            "operations": [
                {
                    "type": "code_edit",
                    "path": str(app),
                    "edits": [
                        {"find": 'VERSION = "1.0.0"', "replace": 'VERSION = "2.0.0"'},
                        {"find": '"Hello, " + name', "replace": 'f"Hello, {name}!"'},
                    ],
                }
            ],
        }
        config_path = ops_dir / "ops.json"
        config_path.write_text(json.dumps(config))

        # Step 1: Validate
        is_valid, errors = validator.validate_json_config(str(config_path))
        assert is_valid, f"Validation failed: {errors}"

        # Step 2: Execute
        result = executor.execute_json_config(str(config_path), dry_run=False)
        assert result is True

        # Verify changes applied
        modified = app.read_text()
        assert 'VERSION = "2.0.0"' in modified
        assert 'f"Hello, {name}!"' in modified

        # Step 3: Find backup and restore
        backups = restore.list_backups("backups")
        assert len(backups) == 1

        restore_result = restore.restore_from_backup(backups[0], force=True)
        assert restore_result is True

        # Verify original content restored
        assert app.read_text() == original_content

    def test_validate_execute_restore_file_operations(self, tmp_path, monkeypatch):
        """Full round-trip with file_create and file_delete."""
        monkeypatch.chdir(tmp_path)

        # Create a file to be deleted
        old_file = tmp_path / "old_util.py"
        old_file.write_text("# deprecated module\nold_func = True\n")

        new_file_path = tmp_path / "new_util.py"

        config = {
            "plan": "file-ops-test",
            "operations": [
                {
                    "type": "file_create",
                    "path": str(new_file_path),
                    "content": "# new utility module\ndef helper():\n    return True\n",
                },
                {
                    "type": "file_delete",
                    "path": str(old_file),
                    "reason": "Replaced by new_util.py with improved implementation",
                },
            ],
        }
        config_path = tmp_path / "ops.json"
        config_path.write_text(json.dumps(config))

        # Validate
        is_valid, errors = validator.validate_json_config(str(config_path))
        assert is_valid, f"Validation failed: {errors}"

        # Execute
        result = executor.execute_json_config(str(config_path), dry_run=False)
        assert result is True
        assert new_file_path.exists()
        assert not old_file.exists()

        # Restore
        backups = restore.list_backups("backups")
        assert len(backups) == 1
        restore_result = restore.restore_from_backup(backups[0], force=True)
        assert restore_result is True

        # Old file restored, new file removed
        assert old_file.exists()
        assert not new_file_path.exists()

    def test_dry_run_does_not_modify(self, tmp_path, monkeypatch):
        """Dry run through validate -> execute should not touch files."""
        monkeypatch.chdir(tmp_path)

        app = tmp_path / "app.py"
        original = 'x = 1\n'
        app.write_text(original)

        config = {
            "plan": "dry-run-test",
            "operations": [
                {
                    "type": "code_edit",
                    "path": str(app),
                    "edits": [{"find": "x = 1", "replace": "x = 99"}],
                }
            ],
        }
        config_path = tmp_path / "ops.json"
        config_path.write_text(json.dumps(config))

        # Validate
        is_valid, _ = validator.validate_json_config(str(config_path))
        assert is_valid

        # Dry-run execute
        result = executor.execute_json_config(str(config_path), dry_run=True)
        assert result is True

        # File unchanged
        assert app.read_text() == original
        # No backups created
        assert not os.path.exists("backups")

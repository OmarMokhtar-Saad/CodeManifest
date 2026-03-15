"""Tests for execute-json-ops.py."""

import json
import logging
import os
import sys
import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Import with hyphens in filename
import importlib
executor = importlib.import_module("execute-json-ops")


class TestSymlinkBypass:
    """BUG 1: Executor path handling."""

    def test_execute_resolves_paths(self, tmp_project):
        """Executor should handle paths correctly."""
        sample = tmp_project / "sample.py"
        sample.write_text('x = 1\n')

        config = {
            "plan": "test-plan",
            "files": [
                {
                    "path": str(sample),
                    "edits": [{"find": "x = 1", "replace": "x = 2"}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        result = executor.execute_json_config(str(config_path), dry_run=True)
        assert result is True


class TestProtectedFileInExecutor:
    """BUG 2: No is_protected_file() in executor."""

    def test_protected_file_blocked(self, tmp_project):
        """Protected files should be blocked from deletion."""
        gitignore = tmp_project / ".gitignore"
        gitignore.write_text("*.pyc\n")

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "file_delete",
                    "path": str(gitignore),
                    "reason": "Want to remove gitignore for some reason",
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        result = executor.execute_json_config(str(config_path), dry_run=False)
        assert result is False
        # File should still exist
        assert gitignore.exists()

    def test_protected_makefile_blocked(self, tmp_project):
        """Makefile should be protected from deletion."""
        makefile = tmp_project / "Makefile"
        makefile.write_text("all:\n\techo hello\n")

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "file_delete",
                    "path": str(makefile),
                    "reason": "Removing Makefile to simplify project",
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        result = executor.execute_json_config(str(config_path), dry_run=False)
        assert result is False
        assert makefile.exists()

    @pytest.mark.parametrize(
        "filename",
        [
            "package-lock.json",
            "yarn.lock",
            "setup.cfg",
            "Pipfile",
            "Pipfile.lock",
            "tsconfig.json",
        ],
    )
    def test_new_protected_patterns(self, filename):
        """ENH 1: New protected patterns should be recognized by executor."""
        assert executor.is_protected_file(filename)

    def test_normal_file_deletable(self, tmp_project):
        """Non-protected files should be deletable."""
        normal = tmp_project / "old-util.py"
        normal.write_text("old_function = True\n")

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "file_delete",
                    "path": str(normal),
                    "reason": "Replaced by new implementation in new-util.py",
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        result = executor.execute_json_config(str(config_path), dry_run=False)
        assert result is True
        assert not normal.exists()


class TestPartialEditsWarning:
    """BUG 6: Partial edits succeed silently."""

    def test_partial_edits_emit_warning(self, tmp_project, caplog):
        """When not all edits apply, a WARNING log should be emitted."""
        sample = tmp_project / "sample.py"
        sample.write_text('x = 1\ny = 2\n')

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "code_edit",
                    "path": str(sample),
                    "edits": [
                        {"find": "x = 1", "replace": "x = 10"},
                        {"find": "NONEXISTENT_PATTERN", "replace": "something"},
                    ],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        with caplog.at_level(logging.WARNING):
            result = executor.execute_json_config(str(config_path), dry_run=False)

        assert result is True
        assert any("1 of 2" in r.message for r in caplog.records)

    def test_all_edits_applied_no_warning(self, tmp_project, caplog):
        """When all edits apply, no WARNING should be emitted."""
        sample = tmp_project / "sample.py"
        sample.write_text('x = 1\ny = 2\n')

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "code_edit",
                    "path": str(sample),
                    "edits": [
                        {"find": "x = 1", "replace": "x = 10"},
                        {"find": "y = 2", "replace": "y = 20"},
                    ],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        with caplog.at_level(logging.WARNING):
            result = executor.execute_json_config(str(config_path), dry_run=False)

        assert result is True
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) == 0


class TestKeyErrorOnMissingReason:
    """BUG 9: KeyError crash on missing reason."""

    def test_missing_reason_no_crash(self, tmp_project):
        """Executor should not crash if 'reason' key is missing."""
        deletable = tmp_project / "temp.txt"
        deletable.write_text("temp content\n")

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "file_delete",
                    "path": str(deletable),
                    # No 'reason' key
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        # Should not raise KeyError
        result = executor.execute_json_config(str(config_path), dry_run=True)
        assert isinstance(result, bool)

    def test_with_reason_still_works(self, tmp_project):
        """Executor should still work when 'reason' is provided."""
        deletable = tmp_project / "old.py"
        deletable.write_text("old code\n")

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "file_delete",
                    "path": str(deletable),
                    "reason": "Replaced by new implementation in new module",
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        result = executor.execute_json_config(str(config_path), dry_run=False)
        assert result is True
        assert not deletable.exists()


class TestExecutorSmoke:
    """Smoke tests for executor."""

    def test_dry_run_legacy(self, tmp_project):
        """Legacy format dry run should succeed."""
        sample = tmp_project / "app.py"
        sample.write_text('VERSION = "1.0.0"\n')

        config = {
            "plan": "test-plan",
            "files": [
                {
                    "path": str(sample),
                    "edits": [{"find": 'VERSION = "1.0.0"', "replace": 'VERSION = "2.0.0"'}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        result = executor.execute_json_config(str(config_path), dry_run=True)
        assert result is True

    def test_execute_code_edit(self, tmp_project):
        """Code edit should modify file content."""
        sample = tmp_project / "app.py"
        sample.write_text('VERSION = "1.0.0"\n')

        config = {
            "plan": "test-plan",
            "files": [
                {
                    "path": str(sample),
                    "edits": [{"find": 'VERSION = "1.0.0"', "replace": 'VERSION = "2.0.0"'}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        result = executor.execute_json_config(str(config_path), dry_run=False)
        assert result is True
        assert 'VERSION = "2.0.0"' in sample.read_text()

    def test_file_create(self, tmp_project):
        """file_create operation should create new file."""
        new_file = tmp_project / "created.py"

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "file_create",
                    "path": str(new_file),
                    "content": "new_var = True\n",
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        result = executor.execute_json_config(str(config_path), dry_run=False)
        assert result is True
        assert new_file.exists()
        assert new_file.read_text() == "new_var = True\n"

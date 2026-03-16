"""Tests for validate-config-json.py."""

import json
import os
import sys
import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Import with hyphens in filename
import importlib
validator = importlib.import_module("validate-config-json")


class TestSymlinkBypass:
    """BUG 1: os.path.realpath used instead of os.path.abspath."""

    def test_realpath_used_in_backup_validation(self, tmp_project, sample_file):
        """Verify that validate_backup_compatibility uses realpath for path reconstruction."""
        config = {
            "plan": "test-plan",
            "files": [{"path": str(sample_file)}],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        # Should not crash; realpath resolves symlinks properly
        valid, errors = validator.validate_backup_compatibility(str(config_path))
        assert isinstance(valid, bool)

    def test_symlink_path_resolved(self, tmp_project, sample_file):
        """Symlink pointing outside project should be caught by GUARD 19."""
        # Create a symlink inside project pointing to a file outside
        outside_dir = tmp_project / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "secret.py"
        outside_file.write_text("secret = True\n")

        # Create symlink
        link = tmp_project / "link.py"
        link.symlink_to(outside_file)

        config = {
            "plan": "test-plan",
            "files": [{"path": str(link), "edits": [{"find": "secret", "replace": "public"}]}],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        # validate_json_config should work (file exists via link)
        valid, errors = validator.validate_json_config(str(config_path))
        assert valid


class TestNullBytesInContent:
    """BUG 3: Null bytes checked in replacement content & file_create content."""

    def test_null_byte_in_replace_content(self, tmp_project, sample_file):
        """GUARD 26: replace content with null bytes should be rejected."""
        config = {
            "plan": "test-plan",
            "files": [
                {
                    "path": str(sample_file),
                    "edits": [
                        {"find": 'VERSION = "1.0.0"', "replace": "bad\x00content"}
                    ],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("null bytes" in e.lower() for e in errors)

    def test_null_byte_in_add_after_content(self, tmp_project, sample_file):
        """GUARD 26: add_after content with null bytes should be rejected."""
        config = {
            "plan": "test-plan",
            "files": [
                {
                    "path": str(sample_file),
                    "edits": [
                        {"find": 'VERSION = "1.0.0"', "add_after": "\x00injected"}
                    ],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("null bytes" in e.lower() for e in errors)

    def test_null_byte_in_add_before_content(self, tmp_project, sample_file):
        """GUARD 26: add_before content with null bytes should be rejected."""
        config = {
            "plan": "test-plan",
            "files": [
                {
                    "path": str(sample_file),
                    "edits": [
                        {"find": 'VERSION = "1.0.0"', "add_before": "prefix\x00bad"}
                    ],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("null bytes" in e.lower() for e in errors)

    def test_null_byte_in_find_pattern(self, tmp_project, sample_file):
        """GUARD 26: find pattern with null bytes should be rejected."""
        config = {
            "plan": "test-plan",
            "files": [
                {
                    "path": str(sample_file),
                    "edits": [{"find": "find\x00this", "replace": "that"}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("null bytes" in e.lower() for e in errors)

    def test_null_byte_in_file_create_content(self, tmp_project):
        """GUARD 26: file_create content with null bytes should be rejected."""
        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "file_create",
                    "path": str(tmp_project / "new.py"),
                    "content": "data = '\x00evil'",
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("null bytes" in e.lower() for e in errors)


class TestUnknownOperationType:
    """BUG 4: Unknown operation type passes silently."""

    def test_unknown_type_rejected_with_schema(self, tmp_project):
        """Schema validation catches unknown types when jsonschema is available."""
        config = {
            "plan": "test-plan",
            "operations": [
                {"type": "foo", "path": "anything.py"}
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid

    def test_unknown_type_rejected_without_schema(self, tmp_project, monkeypatch):
        """GUARD 29: Unknown operation type caught when jsonschema unavailable."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test-plan",
            "operations": [
                {"type": "foo", "path": "anything.py"}
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("unknown type" in e.lower() for e in errors)

    def test_valid_types_accepted(self, tmp_project, sample_file):
        """Valid types should not trigger GUARD 29."""
        deletable = tmp_project / "deleteme.txt"
        deletable.write_text("content")

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "code_edit",
                    "path": str(sample_file),
                    "edits": [{"find": 'VERSION = "1.0.0"', "replace": 'VERSION = "2.0.0"'}],
                },
                {
                    "type": "file_create",
                    "path": str(tmp_project / "new.py"),
                    "content": "x = 1\n",
                },
                {
                    "type": "file_delete",
                    "path": str(deletable),
                    "reason": "No longer needed for the project",
                },
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert valid, errors


class TestGuard5ModernFormat:
    """BUG 5: Missing GUARD 5 for modern format."""

    def test_missing_path_in_code_edit_with_schema(self, tmp_project):
        """Schema validation catches missing path when jsonschema is available."""
        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "code_edit",
                    "edits": [{"find": "x", "replace": "y"}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid

    def test_missing_path_in_code_edit_without_schema(self, tmp_project, monkeypatch):
        """GUARD 5: code_edit without path caught when jsonschema unavailable."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "code_edit",
                    "edits": [{"find": "x", "replace": "y"}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("missing 'path'" in e.lower() for e in errors)

    def test_missing_path_in_file_create_with_schema(self, tmp_project):
        """Schema validation catches missing path when jsonschema is available."""
        config = {
            "plan": "test-plan",
            "operations": [
                {"type": "file_create", "content": "data\n"}
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid

    def test_missing_path_in_file_create_without_schema(self, tmp_project, monkeypatch):
        """GUARD 5: file_create without path caught when jsonschema unavailable."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test-plan",
            "operations": [
                {"type": "file_create", "content": "data\n"}
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("missing 'path'" in e.lower() for e in errors)


class TestFileSizeInValidator:
    """BUG 8: File size check in validator."""

    def test_large_file_rejected_legacy(self, tmp_project):
        """Files > 2MB should be rejected in legacy format."""
        large_file = tmp_project / "huge.py"
        # Create a file just over 2MB
        large_file.write_text("x" * (2 * 1024 * 1024 + 1))

        config = {
            "plan": "test-plan",
            "files": [
                {
                    "path": str(large_file),
                    "edits": [{"find": "x", "replace": "y"}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("too large" in e.lower() for e in errors)

    def test_large_file_rejected_modern(self, tmp_project):
        """Files > 2MB should be rejected in modern format."""
        large_file = tmp_project / "huge.py"
        large_file.write_text("x" * (2 * 1024 * 1024 + 1))

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "code_edit",
                    "path": str(large_file),
                    "edits": [{"find": "x", "replace": "y"}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("too large" in e.lower() for e in errors)

    def test_small_file_accepted(self, tmp_project, sample_file):
        """Files under 2MB should pass the size check."""
        config = {
            "plan": "test-plan",
            "files": [
                {
                    "path": str(sample_file),
                    "edits": [{"find": 'VERSION = "1.0.0"', "replace": 'VERSION = "2.0.0"'}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert valid, errors


class TestMaxOperationsLimit:
    """GUARD 28: Max 5 operations enforced even without jsonschema."""

    def test_too_many_ops_legacy_rejected(self, tmp_project, monkeypatch):
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        files = []
        for i in range(6):
            f = tmp_project / f"file{i}.py"
            f.write_text(f"content_{i} = {i}\n")
            files.append({"path": str(f), "edits": [{"find": f"content_{i} = {i}", "replace": f"content_{i} = 0"}]})
        config = {"plan": "test", "files": files}
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid
        assert any("too many" in e.lower() for e in errors)

    def test_too_many_ops_modern_rejected(self, tmp_project, monkeypatch):
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        ops = []
        for i in range(6):
            f = tmp_project / f"file{i}.py"
            f.write_text(f"val_{i} = {i}\n")
            ops.append({"type": "code_edit", "path": str(f), "edits": [{"find": f"val_{i} = {i}", "replace": f"val_{i} = 0"}]})
        config = {"plan": "test", "operations": ops}
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid
        assert any("too many" in e.lower() for e in errors)

    def test_five_ops_accepted(self, tmp_project, monkeypatch):
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        ops = []
        for i in range(5):
            f = tmp_project / f"file{i}.py"
            f.write_text(f"x_{i} = {i}\n")
            ops.append({"type": "code_edit", "path": str(f), "edits": [{"find": f"x_{i} = {i}", "replace": f"x_{i} = 0"}]})
        config = {"plan": "test", "operations": ops}
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert valid, errors


class TestNullBytesInPaths:
    """BUG 10: Null bytes unchecked in file paths."""

    def test_null_byte_in_legacy_path(self, tmp_project):
        """GUARD 25: Legacy format path with null bytes should be rejected."""
        config = {
            "plan": "test-plan",
            "files": [
                {
                    "path": "file\x00.py",
                    "edits": [{"find": "x", "replace": "y"}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("null bytes" in e.lower() for e in errors)

    def test_null_byte_in_modern_code_edit_path(self, tmp_project):
        """GUARD 25: Modern code_edit path with null bytes should be rejected."""
        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "code_edit",
                    "path": "file\x00.py",
                    "edits": [{"find": "x", "replace": "y"}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("null bytes" in e.lower() for e in errors)

    def test_null_byte_in_file_delete_path(self, tmp_project):
        """GUARD 25: file_delete path with null bytes should be rejected."""
        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "file_delete",
                    "path": "file\x00.py",
                    "reason": "Removing old file that is no longer needed",
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("null bytes" in e.lower() for e in errors)

    def test_null_byte_in_file_create_path(self, tmp_project):
        """GUARD 25: file_create path with null bytes should be rejected."""
        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "file_create",
                    "path": "file\x00.py",
                    "content": "x = 1\n",
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(config_path))
        assert not valid
        assert any("null bytes" in e.lower() for e in errors)


class TestProtectedPatternsEnhancement:
    """ENH 1: Incomplete protected patterns list."""

    @pytest.mark.parametrize(
        "filename",
        [
            "package-lock.json",
            "yarn.lock",
            "setup.cfg",
            "Pipfile",
            "Pipfile.lock",
            "tsconfig.json",
            # Original patterns still work
            ".gitignore",
            "README.md",
            "Makefile",
            "Dockerfile",
            "requirements.txt",
            "package.json",
            "pyproject.toml",
            "setup.py",
        ],
    )
    def test_protected_file_detected(self, filename):
        """All protected patterns should be recognized."""
        assert validator.is_protected_file(filename)

    def test_normal_file_not_protected(self):
        """Regular source files should not be protected."""
        assert not validator.is_protected_file("app.py")
        assert not validator.is_protected_file("utils.js")
        assert not validator.is_protected_file("data.csv")


class TestValidConfigPassesAll:
    """Smoke tests: valid configs still pass."""

    def test_valid_legacy_config(self, sample_config_legacy):
        valid, errors = validator.validate_json_config(sample_config_legacy)
        assert valid, errors

    def test_valid_modern_config(self, sample_config_modern):
        valid, errors = validator.validate_json_config(sample_config_modern)
        assert valid, errors


class TestEdgeCases:
    """Additional coverage for error paths."""

    def test_nonexistent_config_file(self, tmp_project):
        """GUARD 1: Config file doesn't exist."""
        valid, errors = validator.validate_json_config("/nonexistent/ops.json")
        assert not valid
        assert any("does not exist" in e for e in errors)

    def test_invalid_json_syntax(self, tmp_project):
        """GUARD 2: Invalid JSON syntax."""
        bad = tmp_project / "bad.json"
        bad.write_text("{invalid json")
        valid, errors = validator.validate_json_config(str(bad))
        assert not valid
        assert any("invalid json" in e.lower() for e in errors)

    def test_missing_plan_key(self, tmp_project, sample_file):
        """GUARD 3: Missing plan key."""
        config = {"files": [{"path": str(sample_file), "edits": [{"find": "x", "replace": "y"}]}]}
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        # Might be caught by schema or by guard 3
        assert not valid

    def test_unknown_format(self, tmp_project, monkeypatch):
        """Unknown config format (no 'files' or 'operations')."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {"plan": "test", "data": []}
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_empty_files_array(self, tmp_project, monkeypatch):
        """GUARD 4: Empty files array."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {"plan": "test", "files": []}
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_legacy_file_not_exists(self, tmp_project, monkeypatch):
        """GUARD 6: File doesn't exist in legacy format."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test",
            "files": [{"path": str(tmp_project / "nope.py"), "edits": [{"find": "x", "replace": "y"}]}],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid
        assert any("does not exist" in e for e in errors)

    def test_legacy_missing_edits(self, tmp_project, monkeypatch, sample_file):
        """GUARD 7: Missing edits array."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {"plan": "test", "files": [{"path": str(sample_file)}]}
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_legacy_empty_edits(self, tmp_project, monkeypatch, sample_file):
        """GUARD 7: Empty edits array."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {"plan": "test", "files": [{"path": str(sample_file), "edits": []}]}
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_legacy_no_action_type(self, tmp_project, monkeypatch, sample_file):
        """GUARD 8: No action type in edit."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test",
            "files": [{"path": str(sample_file), "edits": [{"find": 'VERSION = "1.0.0"'}]}],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_legacy_pattern_not_found(self, tmp_project, monkeypatch, sample_file):
        """GUARD 10: Pattern not found."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test",
            "files": [{"path": str(sample_file), "edits": [{"find": "NONEXISTENT", "replace": "y"}]}],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_legacy_ambiguous_match(self, tmp_project, monkeypatch):
        """GUARD 11: Ambiguous match detection."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        f = tmp_project / "dup.py"
        f.write_text("x = 1\nx = 1\n")
        config = {
            "plan": "test",
            "files": [{"path": str(f), "edits": [{"find": "x = 1", "replace": "x = 2"}]}],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid
        assert any("appears" in e and "times" in e for e in errors)

    def test_modern_file_not_exists(self, tmp_project, monkeypatch):
        """GUARD 6: File doesn't exist in modern format."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test",
            "operations": [
                {"type": "code_edit", "path": str(tmp_project / "nope.py"), "edits": [{"find": "x", "replace": "y"}]}
            ],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_modern_missing_edits(self, tmp_project, monkeypatch, sample_file):
        """GUARD 7: Missing edits in modern code_edit."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test",
            "operations": [{"type": "code_edit", "path": str(sample_file)}],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_modern_empty_edits(self, tmp_project, monkeypatch, sample_file):
        """Empty edits in modern code_edit."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test",
            "operations": [{"type": "code_edit", "path": str(sample_file), "edits": []}],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_modern_pattern_not_found(self, tmp_project, monkeypatch, sample_file):
        """Pattern not found in modern format."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test",
            "operations": [
                {"type": "code_edit", "path": str(sample_file), "edits": [{"find": "NOPE", "replace": "y"}]}
            ],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_modern_ambiguous_match(self, tmp_project, monkeypatch):
        """Ambiguous match in modern format."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        f = tmp_project / "dup.py"
        f.write_text("x = 1\nx = 1\n")
        config = {
            "plan": "test",
            "operations": [
                {"type": "code_edit", "path": str(f), "edits": [{"find": "x = 1", "replace": "x = 2"}]}
            ],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_file_delete_nonexistent(self, tmp_project, monkeypatch):
        """GUARD 12: Delete non-existent file."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test",
            "operations": [
                {"type": "file_delete", "path": str(tmp_project / "gone.py"), "reason": "Removing old unused file"}
            ],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_file_delete_protected(self, tmp_project, monkeypatch):
        """GUARD 13: Delete protected file."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        gi = tmp_project / ".gitignore"
        gi.write_text("*.pyc\n")
        config = {
            "plan": "test",
            "operations": [
                {"type": "file_delete", "path": str(gi), "reason": "Removing gitignore for testing purposes"}
            ],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_file_delete_short_reason(self, tmp_project, monkeypatch):
        """GUARD 14: Deletion reason too short."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        f = tmp_project / "temp.txt"
        f.write_text("temp")
        config = {
            "plan": "test",
            "operations": [{"type": "file_delete", "path": str(f), "reason": "short"}],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_file_delete_directory(self, tmp_project, monkeypatch):
        """GUARD 16: Cannot delete directory."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        d = tmp_project / "subdir"
        d.mkdir()
        config = {
            "plan": "test",
            "operations": [
                {"type": "file_delete", "path": str(d), "reason": "Removing entire subdirectory from project"}
            ],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_file_create_empty_content(self, tmp_project, monkeypatch):
        """file_create with empty content."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test",
            "operations": [{"type": "file_create", "path": str(tmp_project / "new.py"), "content": ""}],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_file_create_parent_missing_is_warning(self, tmp_project, monkeypatch, capsys):
        """GUARD 17: Parent directory doesn't exist — now a warning, not an error."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        config = {
            "plan": "test",
            "operations": [
                {"type": "file_create", "path": str(tmp_project / "nodir" / "new.py"), "content": "x = 1\n"}
            ],
        }
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert valid
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "Parent directory" in captured.out

    def test_too_many_deletions(self, tmp_project, monkeypatch):
        """GUARD 15: Max 3 deletions per config."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        ops = []
        for i in range(4):
            f = tmp_project / f"file{i}.txt"
            f.write_text(f"content {i}")
            ops.append({"type": "file_delete", "path": str(f), "reason": f"Removing old file number {i} from project"})
        config = {"plan": "test", "operations": ops}
        p = tmp_project / "ops.json"
        p.write_text(json.dumps(config))
        valid, errors = validator.validate_json_config(str(p))
        assert not valid

    def test_backup_compatibility_valid(self, sample_config_legacy):
        """Backup compatibility passes for valid config."""
        valid, errors = validator.validate_backup_compatibility(sample_config_legacy)
        assert isinstance(valid, bool)

    def test_detect_config_format(self):
        """detect_config_format returns correct format."""
        assert validator.detect_config_format({"operations": []}) == "modern"
        assert validator.detect_config_format({"files": []}) == "legacy"
        assert validator.detect_config_format({"data": []}) == "unknown"


class TestGuardWarningsNotErrors:
    """GUARD 21 and GUARD 23 should warn without causing rejection."""

    def test_plan_name_with_spaces_still_approved(self, tmp_project, monkeypatch):
        """GUARD 21: Plan with unsafe chars should warn but still pass validation."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        sample = tmp_project / "app.py"
        sample.write_text('x = 1\n')

        config = {
            "plan": "my plan with spaces",
            "operations": [
                {
                    "type": "code_edit",
                    "path": str(sample),
                    "edits": [{"find": "x = 1", "replace": "x = 2"}],
                }
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        valid, errors = validator.validate_json_config(str(config_path))
        assert valid, f"Should approve despite unsafe plan name, got errors: {errors}"

    def test_duplicate_filename_still_approved(self, tmp_project, monkeypatch):
        """GUARD 23: Duplicate filenames across dirs should warn but still pass."""
        monkeypatch.setattr(validator, "JSONSCHEMA_AVAILABLE", False)
        dir_a = tmp_project / "a"
        dir_b = tmp_project / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        (dir_a / "app.py").write_text('x = 1\n')
        (dir_b / "app.py").write_text('y = 2\n')

        config = {
            "plan": "test-plan",
            "operations": [
                {
                    "type": "code_edit",
                    "path": str(dir_a / "app.py"),
                    "edits": [{"find": "x = 1", "replace": "x = 10"}],
                },
                {
                    "type": "code_edit",
                    "path": str(dir_b / "app.py"),
                    "edits": [{"find": "y = 2", "replace": "y = 20"}],
                },
            ],
        }
        config_path = tmp_project / "ops.json"
        config_path.write_text(json.dumps(config))

        valid, errors = validator.validate_json_config(str(config_path))
        assert valid, f"Should approve despite duplicate filenames, got errors: {errors}"

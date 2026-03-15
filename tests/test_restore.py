"""Tests for restore-backup.py."""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import importlib
restore = importlib.import_module("restore-backup")


class TestGuard1BackupExists:
    def test_nonexistent_backup_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = restore.restore_from_backup("/nonexistent/backup", force=True)
        assert result is False


class TestGuard2IsDirectory:
    def test_file_not_directory_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "not-a-dir"
        f.write_text("data")
        result = restore.restore_from_backup(str(f), force=True)
        assert result is False


class TestGuard3ManifestExists:
    def test_missing_manifest_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        backup = tmp_path / "backup-dir"
        backup.mkdir()
        result = restore.restore_from_backup(str(backup), force=True)
        assert result is False


class TestGuard4ManifestValid:
    def test_invalid_json_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        backup = tmp_path / "backup-dir"
        backup.mkdir()
        (backup / "manifest.json").write_text("{invalid")
        result = restore.restore_from_backup(str(backup), force=True)
        assert result is False


class TestGuard7BackupFileExists:
    def test_missing_backup_file_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        backup = tmp_path / "backup-dir"
        backup.mkdir()
        manifest = {"files": ["src/app.py"], "created_files": []}
        (backup / "manifest.json").write_text(json.dumps(manifest))
        # No actual backup file for src/app.py
        result = restore.restore_from_backup(str(backup), force=True)
        assert result is False


class TestGuard11PathTraversal:
    def test_traversal_path_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        backup = tmp_path / "backup-dir"
        backup.mkdir()
        manifest = {"files": ["../../etc/passwd"], "created_files": []}
        (backup / "manifest.json").write_text(json.dumps(manifest))
        result = restore.restore_from_backup(str(backup), force=True)
        assert result is False

    def test_absolute_path_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        backup = tmp_path / "backup-dir"
        backup.mkdir()
        manifest = {"files": ["/etc/passwd"], "created_files": []}
        (backup / "manifest.json").write_text(json.dumps(manifest))
        result = restore.restore_from_backup(str(backup), force=True)
        assert result is False

    def test_safe_relative_path_accepted(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Create the original file
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("modified")

        # Create backup
        backup = tmp_path / "backup-dir"
        backup.mkdir()
        (backup / "src").mkdir()
        (backup / "src" / "app.py").write_text("original")
        manifest = {"files": ["src/app.py"], "created_files": []}
        (backup / "manifest.json").write_text(json.dumps(manifest))

        result = restore.restore_from_backup(str(backup), force=True)
        assert result is True
        assert (src / "app.py").read_text() == "original"


class TestSuccessfulRestore:
    def test_restore_modifies_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("modified content")

        backup = tmp_path / "backup-dir"
        backup.mkdir()
        (backup / "src").mkdir()
        (backup / "src" / "app.py").write_text("original content")
        manifest = {"files": ["src/app.py"], "created_files": []}
        (backup / "manifest.json").write_text(json.dumps(manifest))

        result = restore.restore_from_backup(str(backup), force=True)
        assert result is True
        assert (src / "app.py").read_text() == "original content"

    def test_restore_removes_created_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        created = tmp_path / "new-file.py"
        created.write_text("should be removed")

        backup = tmp_path / "backup-dir"
        backup.mkdir()
        manifest = {"files": [], "created_files": ["new-file.py"]}
        (backup / "manifest.json").write_text(json.dumps(manifest))

        result = restore.restore_from_backup(str(backup), force=True)
        assert result is True
        assert not created.exists()


class TestDryRun:
    def test_dry_run_no_changes(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("current content")

        backup = tmp_path / "backup-dir"
        backup.mkdir()
        (backup / "src").mkdir()
        (backup / "src" / "app.py").write_text("old content")
        manifest = {"files": ["src/app.py"], "created_files": []}
        (backup / "manifest.json").write_text(json.dumps(manifest))

        result = restore.restore_from_backup(str(backup), force=True, dry_run=True)
        assert result is True
        # File should NOT be changed
        assert (src / "app.py").read_text() == "current content"


class TestListBackups:
    def test_list_finds_backups(self, tmp_path):
        b1 = tmp_path / "backups" / "plan-20240101"
        b1.mkdir(parents=True)
        (b1 / "manifest.json").write_text('{"files": []}')

        b2 = tmp_path / "backups" / "plan-20240102"
        b2.mkdir()
        (b2 / "manifest.json").write_text('{"files": []}')

        result = restore.list_backups(str(tmp_path / "backups"))
        assert len(result) == 2

    def test_list_empty_dir(self, tmp_path):
        (tmp_path / "backups").mkdir()
        result = restore.list_backups(str(tmp_path / "backups"))
        assert len(result) == 0

    def test_list_nonexistent_dir(self, tmp_path):
        result = restore.list_backups(str(tmp_path / "nope"))
        assert len(result) == 0

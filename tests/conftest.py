"""Shared fixtures for CodeManifest tests."""

import json
import os
import pytest


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Create a temporary project directory and chdir into it."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def sample_file(tmp_project):
    """Create a small sample file in the temp project."""
    f = tmp_project / "sample.py"
    f.write_text('VERSION = "1.0.0"\n\ndef greet(name):\n    return "Hello, " + name\n')
    return f


@pytest.fixture
def sample_config_legacy(tmp_project, sample_file):
    """Create a valid legacy-format config."""
    config = {
        "plan": "test-plan",
        "files": [
            {
                "path": str(sample_file),
                "edits": [
                    {
                        "find": 'VERSION = "1.0.0"',
                        "replace": 'VERSION = "2.0.0"',
                    }
                ],
            }
        ],
    }
    config_path = tmp_project / "ops.json"
    config_path.write_text(json.dumps(config))
    return str(config_path)


@pytest.fixture
def sample_config_modern(tmp_project, sample_file):
    """Create a valid modern-format config."""
    config = {
        "plan": "test-plan",
        "operations": [
            {
                "type": "code_edit",
                "path": str(sample_file),
                "edits": [
                    {
                        "find": 'VERSION = "1.0.0"',
                        "replace": 'VERSION = "2.0.0"',
                    }
                ],
            }
        ],
    }
    config_path = tmp_project / "ops.json"
    config_path.write_text(json.dumps(config))
    return str(config_path)

# CodeManifest

![CI](https://github.com/OmarMokhtar-Saad/CodeManifest/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A declarative execution engine for AI-assisted code changes. The AI describes changes in a structured JSON file; Python applies them deterministically with validation, backup, and rollback.

## Table of Contents

- [Overview](#overview)
- [Why Use It](#why-use-it)
- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Add to Your Project](#add-to-your-project)
- [The ops.json Format](#the-opsjson-format)
- [Scripts Reference](#scripts-reference)
- [Security](#security)
- [Integration Guide](#integration-guide)
- [Requirements](#requirements)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

CodeManifest separates **planning** (what the AI does) from **execution** (what Python does). Instead of letting an AI edit files directly, you have it produce a small JSON manifest (`ops.json`) describing the exact changes. A Python script then validates and applies those changes, with full backup and automatic rollback on failure.

This is the same pattern used by infrastructure-as-code tools: declare the desired state, validate it, then execute it.

```
AI reads files + produces ops.json       Python validates + executes deterministically
────────────────────────────────         ──────────────────────────────────────────────
Thinks once, writes a plan               29-guard validation before any file is touched
Costs ~2,500 tokens                      Backs up every file, applies changes in sequence
Done.                                    Rolls back automatically on failure
```

---

## Why Use It

**Reduced token usage.** The AI produces a compact JSON plan instead of rewriting entire files. In measured production use, this reduces token consumption by 77-92% compared to direct AI code editing.

**Deterministic execution.** The `find` pattern must match the file content exactly. If the AI guessed wrong, the validator rejects the plan before any file is touched.

**Safe by default.** Every modified or deleted file is backed up before changes. Operations run inside a transaction; if any step fails, all changes are rolled back automatically. Backups are never deleted.

**Auditable.** Every ops.json is a reviewable artifact. Code review becomes reading a list of exact find-replace operations with predictable diffs.

**Works with any AI tool.** The JSON format is model-agnostic. Setup prompts are provided for Claude Code, Cursor, GitHub Copilot, ChatGPT, Gemini, and others. The scripts also work without AI for manual use.

**Works with any language.** The scripts operate on plain text files. Python, TypeScript, Java, Go, Swift, Kotlin, Ruby, or any other text-based codebase.

---

## How It Works

```
User request
     |
     v
AI reads files + produces ops.json
     |
     v
validate-config-json.py  ---- REJECTED (with fix suggestions)
     |
  APPROVED
     |
     v
execute-json-ops.py
  |-- acquires execution lock
  |-- backs up all target files
  |-- writes manifest.json
  |-- applies operations in sequence
  |-- shows diff preview (in dry-run mode)
  +-- rolls back automatically on any failure
     |
     v
Changes applied. Backup preserved.
     |
     v  (if recovery needed)
restore-backup.py  ---- restores from backup in one command
```

---

## Quick Start

```bash
git clone https://github.com/OmarMokhtar-Saad/CodeManifest.git
cd CodeManifest

# Optional: enable JSON schema validation
pip3 install jsonschema

# Validate -> preview with diff -> execute
python3 scripts/validate-config-json.py examples/04-modern-code-edit.json
python3 scripts/execute-json-ops.py examples/04-modern-code-edit.json --dry-run
python3 scripts/execute-json-ops.py examples/04-modern-code-edit.json

# Run the test suite
pip3 install pytest
python3 -m pytest tests/ -v
```

The dry-run shows a unified diff of what would change, without modifying any files.

---

## Add to Your Project

### Option A: One-prompt setup (recommended)

Paste one of these prompts into your AI tool. It downloads the scripts, creates the configuration files for your tool, and runs a verification test.

| AI Tool | Prompt | What it sets up |
|---------|--------|-----------------|
| **Claude Code** | [setup-claude-code.md](prompts/setup-claude-code.md) | Scripts + 3 slash-command skills + CLAUDE.md |
| **Cursor** | [setup-cursor.md](prompts/setup-cursor.md) | Scripts + `.cursor/rules/` config |
| **GitHub Copilot** | [setup-copilot.md](prompts/setup-copilot.md) | Scripts + `copilot-instructions.md` |
| **ChatGPT / GPT-4** | [setup-chatgpt.md](prompts/setup-chatgpt.md) | System prompt for ops.json generation |
| **Any AI tool** | [setup-universal.md](prompts/setup-universal.md) | Auto-detects tool, configures accordingly |

Each prompt downloads scripts via `curl` from GitHub. You do not need to clone this repository into your project.

Already set up? Run [integration-test.md](prompts/integration-test.md) to verify.

### Option B: Manual setup

**1. Download the scripts:**

```bash
mkdir -p scripts
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/validate-config-json.py -o scripts/validate-config-json.py
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/execute-json-ops.py -o scripts/execute-json-ops.py
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/restore-backup.py -o scripts/restore-backup.py
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/operations-schema.json -o scripts/operations-schema.json
```

On systems without `curl`, use `wget` or clone the repo and copy the `scripts/` directory.

**2. Configure your AI tool.**

Add the following to your tool's instruction file (CLAUDE.md, `.cursor/rules/`, `.github/copilot-instructions.md`, or system prompt):

```
All code changes must use the ops.json pattern. Do not edit files directly.

Workflow:
1. Read every target file first
2. Create ops.json: {"plan": "name", "operations": [{"type": "code_edit", "path": "file", "edits": [{"find": "exact text", "replace": "new text"}]}]}
3. Validate: python3 scripts/validate-config-json.py ops.json
4. Dry-run:  python3 scripts/execute-json-ops.py ops.json --dry-run
5. Execute:  python3 scripts/execute-json-ops.py ops.json
```

**3. Use it:**

```bash
python3 scripts/validate-config-json.py operations/my-plan/ops.json       # Must say APPROVED
python3 scripts/execute-json-ops.py operations/my-plan/ops.json --dry-run  # Preview with diff
python3 scripts/execute-json-ops.py operations/my-plan/ops.json            # Apply changes

# If recovery is needed:
python3 scripts/restore-backup.py --list
python3 scripts/restore-backup.py --backup backups/my-plan-<timestamp>
```

For tool-specific details (Claude Code skills, Cursor rules, Copilot instructions), see [Integration Guide](#integration-guide).

---

## The ops.json Format

### Modern format (preferred)

Supports `code_edit`, `file_create`, and `file_delete` operations:

```json
{
  "plan": "add-logging-remove-debug",
  "operations": [
    {
      "type": "code_edit",
      "path": "src/app.py",
      "edits": [
        {
          "find": "def start():\n    setup()",
          "replace": "def start():\n    logger.info('Starting')\n    setup()"
        }
      ]
    },
    {
      "type": "file_create",
      "path": "src/logger.py",
      "content": "import logging\n\nlogger = logging.getLogger(__name__)\n"
    },
    {
      "type": "file_delete",
      "path": "src/debug_helper.py",
      "reason": "Replaced by structured logging in logger.py"
    }
  ]
}
```

### Legacy format

Supports code edits only. Use modern format for new projects:

```json
{
  "plan": "bump-version",
  "files": [
    {
      "path": "src/version.py",
      "edits": [
        { "find": "VERSION = \"1.0.0\"", "replace": "VERSION = \"1.1.0\"" }
      ]
    }
  ]
}
```

### Edit actions

| Action | Description |
|--------|-------------|
| `replace` | Replace the matched text with new content |
| `add_after` | Insert content immediately after the match |
| `add_before` | Insert content immediately before the match |
| `delete` | Remove the matched text (set to `true`) |

### Constraints

| Rule | Limit |
|------|-------|
| Operations per config | 5 max (split into parts if more) |
| File deletions per config | 3 max |
| `find` pattern in file | Must appear exactly once |
| Extra JSON fields | Not allowed (strict schema) |
| Newlines in strings | Use `\n` escape |

For plans exceeding 5 operations, split into `part1-ops.json`, `part2-ops.json`, and execute in order.

---

## Scripts Reference

### `validate-config-json.py`

Pre-flight validator with 29 safety guards. Returns exit code 0 (approved) or 1 (rejected with actionable errors).

```bash
python3 scripts/validate-config-json.py path/to/ops.json
```

| Guard category | Count | Checks |
|----------------|-------|--------|
| Code editing | 11 | File existence, JSON syntax, required fields, pattern exists in file, ambiguous match detection |
| File operations | 7 | Overwrite protection, protected files, deletion reason, parent directory, max deletions |
| Backup safety | 6 | Path format, path reconstruction, plan name safety, collision detection, nested paths |
| Security | 5 | Null byte rejection, file size limit (2 MB), operation type validation |

### `execute-json-ops.py`

Transactional executor with automatic backup, diff preview, and rollback.

```bash
python3 scripts/execute-json-ops.py path/to/ops.json --dry-run   # Preview with diff
python3 scripts/execute-json-ops.py path/to/ops.json              # Apply changes
```

**Behavior:**
- Acquires an execution lock to prevent concurrent runs
- Creates `backups/{plan-name}-{timestamp}/` with a manifest
- Backs up every file before modification or deletion
- Shows a unified diff preview during `--dry-run`
- Applies operations in sequence within a transaction
- Rolls back all changes automatically if any operation fails

### `restore-backup.py`

One-command recovery with 12 safety guards.

```bash
python3 scripts/restore-backup.py --list                                       # List backups
python3 scripts/restore-backup.py --backup backups/my-plan-20240101-120000     # Restore
python3 scripts/restore-backup.py --backup backups/my-plan-20240101-120000 --force  # Skip prompt
```

Backups are never deleted automatically. They serve as an audit trail.

---

## Security

The executor enforces path confinement, rejecting any operation that resolves outside the project root (including through symlinked parent directories). Null bytes in paths and content are rejected. Protected files (`.gitignore`, `*.md`, `Makefile`, `Dockerfile`, `requirements.txt`, `package.json`, `pyproject.toml`, and others) cannot be deleted.

The validator should always run before the executor. The full 29-guard validation (max operations, file size limits, ambiguous match detection) is enforced by the validator. The executor includes path validation and protected-file checks, but relies on the validator for the complete safety model.

For vulnerability reporting, see [SECURITY.md](SECURITY.md).

---

## Integration Guide

### Claude Code

```bash
cp -r scripts/ your-project/scripts/
cp -r .claude/ your-project/.claude/
cp templates/CLAUDE.md.template your-project/CLAUDE.md
# Edit CLAUDE.md with your project name and test command
```

Provides three slash commands: `/generate-ops`, `/validate-ops`, `/execute-ops`.

### Cursor

```bash
cp -r scripts/ your-project/scripts/
```

Create `.cursor/rules/ops-config.mdc` with the ops.json workflow instructions. See [setup-cursor.md](prompts/setup-cursor.md) for the full file content.

### GitHub Copilot

```bash
cp -r scripts/ your-project/scripts/
```

Create `.github/copilot-instructions.md` with the ops.json workflow. See [setup-copilot.md](prompts/setup-copilot.md) for the full file content.

### ChatGPT / Gemini / Other tools

Copy `scripts/` into your project. Add the ops.json workflow to your system prompt or custom instructions. See [setup-chatgpt.md](prompts/setup-chatgpt.md) for a ready-to-use prompt.

ChatGPT and Gemini produce the ops.json; you run the scripts locally.

### Without AI

The scripts work standalone. Write ops.json by hand and run the three commands:

```bash
python3 scripts/validate-config-json.py ops.json
python3 scripts/execute-json-ops.py ops.json --dry-run
python3 scripts/execute-json-ops.py ops.json
```

---

## Requirements

| Requirement | Notes |
|-------------|-------|
| Python 3.9+ | No external packages required for core functionality |
| macOS / Linux | Full support including file locking via `fcntl` |
| Windows | Scripts run; execution locking is not enforced (no `fcntl`) |
| `jsonschema` | Optional. Enables strict JSON schema validation. `pip3 install jsonschema` |
| `pytest` | Optional. For running the test suite. `pip3 install pytest` |

**CI tested:** Python 3.9, 3.10, 3.11, 3.12, 3.13 on Ubuntu with ruff linting, 115 tests, minimum 75% coverage enforced.

---

## Project Structure

```
CodeManifest/
├── scripts/
│   ├── validate-config-json.py      29-guard pre-flight validator
│   ├── execute-json-ops.py          Transactional executor with backup + diff preview
│   ├── restore-backup.py            One-command recovery (12 safety guards)
│   └── operations-schema.json       Strict JSON schema (used by validator)
│
├── tests/                           115 tests across 4 files
│   ├── conftest.py                  Shared fixtures
│   ├── test_validator.py            Validator tests (all 29 guards)
│   ├── test_executor.py             Executor tests (edits, rollback, lock, diff, paths)
│   ├── test_restore.py              Restore tests (guards, path traversal, round-trip)
│   └── test_integration.py          End-to-end: validate -> execute -> restore
│
├── examples/
│   ├── sample/                      Files the examples operate on
│   ├── 01-simple-edit.json          Single edit, legacy format
│   ├── 02-multi-file-edit.json      Two files, legacy format
│   ├── 03-file-operations.json      File create + delete, modern format
│   └── 04-modern-code-edit.json     Code edit, modern format
│
├── prompts/                         One-prompt setup for each AI tool
│   ├── setup-claude-code.md
│   ├── setup-cursor.md
│   ├── setup-copilot.md
│   ├── setup-chatgpt.md
│   ├── setup-universal.md
│   └── integration-test.md
│
├── .claude/skills/                  Claude Code slash commands
├── skills/                          Generic skill files (any LLM)
├── templates/                       CLAUDE.md and AGENTS.md templates
│
├── .github/workflows/ci.yml        CI on Python 3.9/3.10/3.11/3.12/3.13 + ruff
├── LICENSE                          MIT
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
└── CLAUDE.md                        Project context for AI-assisted development
```

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

This repository uses its own ops.json pattern for code changes. For security issues, see [SECURITY.md](SECURITY.md).

---

## License

[MIT](LICENSE)

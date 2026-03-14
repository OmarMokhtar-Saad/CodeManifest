# AI Ops Config Pattern

Cut AI token costs 77–92% by separating planning from execution.

Instead of asking the AI to write code, ask it to describe changes in a compact JSON file (`ops.json`). A Python script executes the changes deterministically — no AI needed for the execution step.

---

## How It Works

```
AI Planner --> ops.json --> Validator (Python) --> Executor (Python) --> Done
```

The AI (expensive) handles only the planning phase. Everything after is a deterministic Python script.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/ai-ops-config.git
cd ai-ops-config

# 2. (Optional) Install schema validation
pip install jsonschema

# 3. Try the examples
python scripts/validate-config-json.py examples/01-simple-edit.json
python scripts/execute-json-ops.py examples/01-simple-edit.json --dry-run
python scripts/execute-json-ops.py examples/01-simple-edit.json
```

---

## The ops.json Format

**Simple edit (legacy format):**

```json
{
  "plan": "bump-version",
  "files": [
    {
      "path": "src/version.py",
      "edits": [
        {
          "find": "VERSION = \"1.0.0\"",
          "replace": "VERSION = \"1.1.0\""
        }
      ]
    }
  ]
}
```

**Mixed operations (modern format):**

```json
{
  "plan": "add-logging-remove-debug",
  "operations": [
    {
      "type": "code_edit",
      "path": "src/app.py",
      "edits": [
        {
          "find": "def start():",
          "add_after": "\n    logger.info('Application starting')"
        }
      ]
    },
    {
      "type": "file_delete",
      "path": "src/debug_helper.py",
      "reason": "Debug helper no longer needed in production"
    }
  ]
}
```

### Edit Actions

| Action | Description |
|---|---|
| `replace` | Replace matched text with new content |
| `add_after` | Insert content after matched text |
| `add_before` | Insert content before matched text |
| `delete` | Remove matched text |

### Constraints

- Max 5 operations per config
- Max 3 file deletions per config
- `find` pattern must appear exactly once in the file
- Protected files cannot be deleted (`.md`, `.gitignore`, `package.json`, etc.)

---

## Scripts

### `validate-config-json.py`
24 safety guards before any file is touched.

```bash
python scripts/validate-config-json.py path/to/ops.json
# -> APPROVED  (exit 0)
# -> REJECTED  (exit 1, with errors)
```

Guards include: file existence, JSON syntax, find pattern exists in file, ambiguous match detection, protected file check, overwrite protection, path safety.

### `execute-json-ops.py`
Safe executor with auto-backup and rollback.

```bash
# Preview changes without applying
python scripts/execute-json-ops.py path/to/ops.json --dry-run

# Apply changes
python scripts/execute-json-ops.py path/to/ops.json
```

Every modified or deleted file is backed up to `backups/<plan>-<timestamp>/` before changes are applied. A `manifest.json` is written for restore compatibility.

### `restore-backup.py`
One-command recovery.

```bash
# List available backups
python scripts/restore-backup.py --list

# Restore from a specific backup
python scripts/restore-backup.py --backup backups/my-plan-20240101-120000

# Skip confirmation prompt
python scripts/restore-backup.py --backup backups/my-plan-20240101-120000 --force
```

---

## Recommended Workflow

```bash
# Step 1: Validate
python scripts/validate-config-json.py my-plan/ops.json

# Step 2: Dry run
python scripts/execute-json-ops.py my-plan/ops.json --dry-run

# Step 3: Execute
python scripts/execute-json-ops.py my-plan/ops.json

# Step 4: Verify your changes work (run your tests)
# ...

# If something went wrong:
python scripts/restore-backup.py --list
python scripts/restore-backup.py --backup backups/my-plan-20240101-120000
```

---

## Setting Up with Claude Code (or any LLM)

Copy `templates/CLAUDE.md.template` to your project root as `CLAUDE.md` and fill in your project name.

This tells the AI:
- Its job ends at producing `ops.json`
- It must NOT write code directly
- The exact format and constraints to follow

The AI reads the template and produces ops.json files instead of writing code. You validate and execute them deterministically.

Works with any instruction-following LLM: Claude, GPT-4, Gemini, Cursor, Copilot Workspace.

---

## Token Savings

| Approach | Tokens Used | vs Baseline |
|---|---|---|
| Verbose AI implementation | ~15,000 | baseline |
| Ops Config Pattern | ~1,200 | 92% less |
| Full workflow (plan + review + execute) | ~3,000 | 77% less |

The AI pays token cost only for the planning phase. The execution phase costs zero AI tokens.

---

## Requirements

- Python 3.8+
- Git (for relative path resolution in backups)
- `jsonschema` library (optional, for schema validation): `pip install jsonschema`

No other dependencies. All scripts use the Python standard library.

---

## Project Structure

```
ai-ops-config/
├── scripts/
│   ├── validate-config-json.py   # 24-guard validator
│   ├── execute-json-ops.py       # Safe executor with auto-backup
│   ├── restore-backup.py         # One-command recovery
│   └── operations-schema.json   # JSON Schema (used by validator)
├── examples/
│   ├── sample/                   # Sample files for running examples
│   ├── 01-simple-edit.json       # Single file edit (legacy format)
│   ├── 02-multi-file-edit.json   # Multiple files (legacy format)
│   └── 03-file-operations.json  # Create + delete (modern format)
└── templates/
    └── CLAUDE.md.template        # Starter CLAUDE.md for your project
```

---

## License

MIT

# codemanifest

Python scripts and AI skills for the Operations Config Pattern —
cutting AI token costs 77-92% by separating planning (AI) from execution (Python).

## Project Structure

```
scripts/    - The 3 Python scripts (validate, execute, restore) + JSON schema
skills/     - AI skill markdown files (generic, copy into any project)
examples/   - Runnable examples with sample files
templates/  - CLAUDE.md.template for wiring the pattern into a new project
```

## What This Repo Contains

- **Scripts** are production-ready, language-agnostic Python. No dependencies except optional `jsonschema`.
- **Skills** are markdown files. Copy them into `.claude/skills/<name>/SKILL.md` for Claude Code,
  or paste the content into a system prompt for any other LLM.
- **Examples** are self-contained and runnable from the repo root.

## Development Commands

```bash
# Test the validator against all examples
python3 scripts/validate-config-json.py examples/01-simple-edit.json
python3 scripts/validate-config-json.py examples/02-multi-file-edit.json
python3 scripts/validate-config-json.py examples/03-file-operations.json

# Dry-run an example
python3 scripts/execute-json-ops.py examples/01-simple-edit.json --dry-run

# Run an example (modifies examples/sample/ files)
python3 scripts/execute-json-ops.py examples/01-simple-edit.json

# List and restore backups after running examples
python3 scripts/restore-backup.py --list
python3 scripts/restore-backup.py --backup backups/<dir>
```

## AI-Assisted Code Changes (MANDATORY)

When asked to make ANY code change, you MUST use the ops.json pipeline.
Do NOT use Edit/Write tools directly. No exceptions.

### Step 1: `/generate-ops` — Create ops.json

Invoke the skill: `/generate-ops <task description>`

Or manually: read every target file, create `operations/{plan-name}/ops.json` using MODERN format.

### Step 2: `/validate-ops` — Run the validator

Invoke the skill: `/validate-ops operations/{plan-name}/ops.json`

Must output `-> APPROVED`. If REJECTED, fix ops.json and re-validate.

### Step 3: `/execute-ops` — Dry run then apply

Invoke the skill: `/execute-ops operations/{plan-name}/ops.json`

Runs dry-run first, then real execution, then verifies with tests.

### Skills (slash commands)

| Command | Purpose |
|---------|---------|
| `/generate-ops <task>` | Read files and create ops.json |
| `/validate-ops <path>` | Run validator + dry-run |
| `/execute-ops <path>` | Execute ops.json with backup |

### ops.json format (MODERN — preferred)

```json
{
  "plan": "plan-name",
  "operations": [
    {
      "type": "code_edit",
      "path": "src/app.py",
      "edits": [
        {
          "find": "exact text to find",
          "replace": "replacement text"
        }
      ]
    },
    {
      "type": "file_create",
      "path": "src/new_module.py",
      "content": "def new_function():\n    pass\n"
    },
    {
      "type": "file_delete",
      "path": "src/old_module.py",
      "reason": "Replaced by new_module.py with improved implementation"
    }
  ]
}
```

### Operation types

| Type | Required fields | Description |
|------|----------------|-------------|
| `code_edit` | `type`, `path`, `edits` | Edit existing file (find + replace/add_after/add_before/delete) |
| `file_create` | `type`, `path`, `content` | Create new file |
| `file_delete` | `type`, `path`, `reason` | Delete file (reason min 10 chars) |

### Edit actions

| Action | Description |
|--------|-------------|
| `replace` | Replace matched text with new content |
| `add_after` | Insert content after matched text |
| `add_before` | Insert content before matched text |
| `delete` | Remove matched text (set to `true`) |

### Legacy format (also supported)

```json
{
  "plan": "plan-name",
  "files": [
    {
      "path": "src/app.py",
      "edits": [{ "find": "old", "replace": "new" }]
    }
  ]
}
```

Legacy only supports code edits. Use modern format for file_create/file_delete.

### Constraints

- Max 5 operations per config (split into parts if more)
- Max 3 file deletions per config
- `find` must be unique in the file (appear exactly once)
- No extra fields — schema uses `additionalProperties: false`
- Protected files cannot be deleted: `*.md`, `.gitignore`, `package.json`, `pyproject.toml`, etc.

### Folder structure

```
operations/
  <plan-name>/
    ops.json
backups/
  <plan-name>-<timestamp>/
    manifest.json
```

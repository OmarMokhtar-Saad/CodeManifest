# ai-ops-config

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

## AI-Assisted Changes to This Repo

All code changes use the ops.json pattern (dogfooding).

Workflow:
1. Validate: `python3 scripts/validate-config-json.py path/to/ops.json`
2. Dry run:  `python3 scripts/execute-json-ops.py path/to/ops.json --dry-run`
3. Execute:  `python3 scripts/execute-json-ops.py path/to/ops.json`

### ops.json format

```json
{
  "plan": "plan-name",
  "files": [
    {
      "path": "scripts/validate-config-json.py",
      "edits": [
        {
          "find": "exact text to find",
          "replace": "replacement text"
        }
      ]
    }
  ]
}
```

### Constraints

- Max 5 operations per config
- Max 3 file deletions per config
- `find` must be unique in the file
- Protected: `*.md`, `.gitignore`, `examples/sample/*` (do not delete sample files)

### Folder structure

```
operations/
  <plan-name>/
    ops.json
backups/
  <plan-name>-<timestamp>/
    manifest.json
```

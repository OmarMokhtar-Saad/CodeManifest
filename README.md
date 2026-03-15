# AI Ops Config Pattern

**Cut AI coding costs by 77–92% by separating what AI does best (planning) from what Python does best (execution).**

Instead of asking the AI to write code directly, you ask it to describe changes in a compact JSON file.
A Python script executes those changes deterministically — with automatic backup, validation, and rollback built in.

> Proven across 50+ production plans. Zero data loss. Every rollback worked.

---

## The Problem

Every developer using AI for code changes hits the same wall:

- The AI re-reads entire files on every request — even for a 3-line change
- It re-reasons about context, writes the code, explains it, then you review it
- A single bug fix burns 10,000–20,000 tokens
- Multiply that across a real codebase and the cost compounds fast

The root cause: **the AI is doing both the thinking and the typing.** Only one of those needs to be expensive.

---

## The Solution

Give the AI one job: **describe the change in JSON.**
Give Python the other job: **execute it.**

```
AI (expensive, thinks once)         Python (free, runs deterministically)
─────────────────────────           ──────────────────────────────────────
Reads the files                     Validates the JSON (24 guards)
Identifies exact find patterns      Backs up every touched file
Writes ops.json                     Applies the changes
Stops.                              Reports results / rolls back on failure
```

The AI pays token cost once — for the planning phase.
Execution costs zero AI tokens.

---

## How It Works

```
User request
     |
     v
AI reads files + produces ops.json
     |
     v
validate-config-json.py  ──── REJECTED (with fix suggestions)
     |
  APPROVED
     |
     v
execute-json-ops.py
  ├── backs up all target files
  ├── writes manifest.json
  ├── applies operations in sequence
  └── rolls back automatically on any failure
     |
     v
Changes applied. Backup preserved.
     |
     v  (if anything went wrong)
restore-backup.py  ──── full recovery in one command
```

---

## Token Savings

Measured on real production plans:

| Approach | Tokens Used | Savings |
|---|---|---|
| AI writes code directly | ~15,000 | — |
| Ops Config Pattern (execution only) | ~1,200 | **92% less** |
| Full workflow (plan + validate + execute) | ~3,000 | **77% less** |

The planning phase (AI reading files and writing ops.json) costs ~2,500 tokens.
The execution phase (Python running the script) costs 0 tokens.

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/OmarMokhtar-Saad/CodeManifest.git
cd CodeManifest

# Optional: enable JSON schema validation and tests
pip3 install jsonschema pytest

# Try the examples (they run against real files in examples/sample/)
python3 scripts/validate-config-json.py examples/01-simple-edit.json
python3 scripts/execute-json-ops.py examples/01-simple-edit.json --dry-run
python3 scripts/execute-json-ops.py examples/01-simple-edit.json

# Run the test suite
python3 -m pytest tests/ -v
```

Expected output after execution:

```
Plan: simple-edit-example
Format: LEGACY
Operations: 1

Backup directory: backups/simple-edit-example-20240101-120000

[1/1] CODE_EDIT: examples/sample/app.py
  Backed up to: backups/simple-edit-example-20240101-120000/...
  Edit 1: Replaced pattern with 20 chars
  Written 67 bytes, 1/1 edits applied

--------------------------------------------------
EXECUTION COMPLETE
Operations: 1 total
  code_edit: 1
Successful: 1
Errors:     0
--------------------------------------------------
```

---

## The ops.json Format

### Modern Format (preferred) — create, edit, and delete

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
          "replace": "def start():\n    logger.info('Application starting')\n    setup()"
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

### Legacy Format — code edits only

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

Legacy format only supports code edits. Use modern format for file_create/file_delete.

### Edit Actions

| Action | What it does |
|---|---|
| `replace` | Replace the matched text with new content |
| `add_after` | Insert content immediately after the matched text |
| `add_before` | Insert content immediately before the matched text |
| `delete` | Remove the matched text entirely |

### Rules

| Rule | Value |
|---|---|
| Max operations per config | 5 |
| Max file deletions per config | 3 |
| `find` pattern occurrences in file | Exactly 1 (ambiguous = rejected) |
| Extra JSON fields | Not allowed (strict schema) |
| Newlines in `find`/`replace` | Must use `\n` escape |

### Splitting large plans

If a task requires more than 5 operations, split into numbered parts:

```
operations/
  my-plan/
    part1-ops.json    (operations 1-5)
    part2-ops.json    (operations 6-10)
```

Execute in order: `part1` first, then `part2`.

---

## Scripts Reference

### `validate-config-json.py`

Runs 29 safety guards before any file is touched. Returns exit code 0 (approved) or 1 (rejected with errors).

```bash
python3 scripts/validate-config-json.py path/to/ops.json
```

**Guard categories:**

| Category | Guards | What they check |
|---|---|---|
| Code editing | 11 | File existence, JSON syntax, required fields, find pattern exists in file, ambiguous match detection |
| File operations | 7 | Overwrite protection, protected file check, parent directory existence, deletion reason, directory check |
| Backup safety | 6 | Path format consistency, path reconstruction, filename collision detection, nested directory handling |
| Security | 5 | Null byte rejection in paths and content, file size limits, operation type validation |

### `execute-json-ops.py`

Safe executor with automatic backup before every operation.

```bash
# Preview changes without touching any files
python3 scripts/execute-json-ops.py path/to/ops.json --dry-run

# Apply changes
python3 scripts/execute-json-ops.py path/to/ops.json
```

**What it does automatically:**
- Creates `backups/{plan-name}-{timestamp}/` before any changes
- Backs up every file it will modify or delete
- Writes a `manifest.json` listing all backed-up files
- Applies all operations in sequence
- Rolls back automatically if any operation fails

### `restore-backup.py`

One-command recovery with 10 safety guards.

```bash
# List all available backups
python3 scripts/restore-backup.py --list

# Restore with confirmation prompt
python3 scripts/restore-backup.py --backup backups/my-plan-20240101-120000

# Restore without prompt (CI/automation)
python3 scripts/restore-backup.py --backup backups/my-plan-20240101-120000 --force
```

The restore script never deletes backups — they are preserved as an audit trail.

---

## Recommended Workflow

```bash
# 1. Validate
python3 scripts/validate-config-json.py operations/my-plan/ops.json

# 2. Preview (no files touched)
python3 scripts/execute-json-ops.py operations/my-plan/ops.json --dry-run

# 3. Execute
python3 scripts/execute-json-ops.py operations/my-plan/ops.json

# 4. Run your tests
# pytest / npm test / ./gradlew test / go test ./... etc.

# 5. If something went wrong — full recovery in one command
python3 scripts/restore-backup.py --backup backups/my-plan-<timestamp>
```

---

## Integration Guide

### What you're copying

| What | Where it goes | Purpose |
|---|---|---|
| `scripts/` | `your-project/scripts/` | The 3 Python scripts + JSON schema (required) |
| `.claude/skills/` | `your-project/.claude/skills/` | Slash commands for Claude Code (optional) |
| `templates/CLAUDE.md.template` | `your-project/CLAUDE.md` | Project instructions for the AI (recommended) |

The **scripts** are the core — they work standalone with any AI or no AI at all.
The **skills** and **CLAUDE.md** teach the AI to use the scripts automatically.

---

### Claude Code

**Setup (3 minutes):**

```bash
# From inside the CodeManifest repo:
cp -r scripts/ your-project/scripts/
cp -r .claude/ your-project/.claude/
cp templates/CLAUDE.md.template your-project/CLAUDE.md
# Edit CLAUDE.md: fill in your project name and test command
```

**What you get — 3 slash commands:**

| Command | What it does |
|---|---|
| `/generate-ops <task>` | AI reads target files, creates `operations/{plan}/ops.json` |
| `/validate-ops <path>` | Runs `validate-config-json.py` + dry-run, reports APPROVED/REJECTED |
| `/execute-ops <path>` | Runs dry-run, real execution, verifies with tests |

Each prints `[SKILL: name]` tags so you can verify the skill was invoked.

**How to use:**

```
You: "Add logging to src/app.py"

Claude automatically:
1. /generate-ops → reads files, creates operations/add-logging/ops.json
2. /validate-ops → runs validator, reports APPROVED
3. /execute-ops → dry-run, execute, verify with tests
```

Or invoke each step manually: type `/generate-ops` in Claude Code's prompt.

---

### Cursor

**Setup:**

```bash
cp -r scripts/ your-project/scripts/
```

Create `.cursor/rules/ops-config.mdc` in your project:

```markdown
---
description: Use ops.json pattern for all code changes
globs: **/*
alwaysApply: true
---

When asked to make ANY code change:

1. Read every target file first
2. Create an ops.json file with this format:
   {
     "plan": "plan-name",
     "operations": [
       {"type": "code_edit", "path": "file.py", "edits": [{"find": "exact text", "replace": "new text"}]}
     ]
   }
3. Run: python3 scripts/validate-config-json.py ops.json
4. Run: python3 scripts/execute-json-ops.py ops.json --dry-run
5. Run: python3 scripts/execute-json-ops.py ops.json

Do NOT edit files directly. Always use ops.json.
```

---

### GitHub Copilot

**Setup:**

```bash
cp -r scripts/ your-project/scripts/
```

Create `.github/copilot-instructions.md` in your project:

```markdown
## Code Change Instructions

All code changes must use the ops.json pattern. Do not edit files directly.

Workflow:
1. Read every target file first
2. Produce an ops.json describing changes in this format:
   - "plan": plan name
   - "operations": array of {"type": "code_edit"/"file_create"/"file_delete", "path": "...", ...}
   - For edits: {"find": "exact text from file", "replace": "new text"}
3. Run: python3 scripts/validate-config-json.py <ops.json>
4. Run: python3 scripts/execute-json-ops.py <ops.json> --dry-run
5. Run: python3 scripts/execute-json-ops.py <ops.json>

Rules:
- find pattern must match EXACTLY (copy from file, don't guess)
- find pattern must appear exactly once in the file
- Max 5 operations per config
- Use \n for newlines in JSON strings
```

---

### ChatGPT / GPT-4 / GPT-4o

**Setup:** Copy `scripts/` into your project. Then add this to your **Custom Instructions** or **System Prompt**:

```
You are a code change planner. When asked to implement changes:

1. Ask the user to paste the contents of each target file
2. Produce an ops.json file describing the exact changes:
   {
     "plan": "plan-name",
     "operations": [
       {
         "type": "code_edit",
         "path": "relative/path/to/file",
         "edits": [{"find": "exact text from file", "replace": "new text"}]
       }
     ]
   }
3. Tell the user to run:
   python3 scripts/validate-config-json.py ops.json
   python3 scripts/execute-json-ops.py ops.json --dry-run
   python3 scripts/execute-json-ops.py ops.json

Rules:
- "find" must be copied EXACTLY from the file (preserve whitespace)
- "find" must appear exactly once in the file
- Use \n for newlines, \t for tabs in JSON strings
- Max 5 operations per config
- For file creation: {"type": "file_create", "path": "...", "content": "..."}
- For file deletion: {"type": "file_delete", "path": "...", "reason": "min 10 chars"}
```

**Note:** ChatGPT can't run the scripts — it produces the ops.json, you run the scripts locally.

---

### Google Gemini

**Setup:** Same as ChatGPT. Add the same instructions to your Gemini system prompt or Google AI Studio instructions. Gemini produces ops.json, you run the scripts locally.

---

### Windsurf / Aider / Other AI coding tools

**Setup:**

```bash
cp -r scripts/ your-project/scripts/
```

Create a `.ai-instructions` or equivalent config file with:

```
All code changes use the ops.json pattern.
Do NOT edit files directly. Produce ops.json instead.

Format:
{"plan": "name", "operations": [{"type": "code_edit", "path": "file", "edits": [{"find": "exact", "replace": "new"}]}]}

After creating ops.json, run:
python3 scripts/validate-config-json.py ops.json
python3 scripts/execute-json-ops.py ops.json
```

The instruction file name varies by tool — check your tool's docs for where to put system instructions.

---

### No AI — manual usage

The scripts work without any AI. Write ops.json by hand:

```bash
# 1. Create ops.json manually
cat > ops.json << 'EOF'
{
  "plan": "my-change",
  "operations": [
    {
      "type": "code_edit",
      "path": "src/app.py",
      "edits": [{"find": "old_value = 1", "replace": "old_value = 2"}]
    }
  ]
}
EOF

# 2. Validate
python3 scripts/validate-config-json.py ops.json

# 3. Execute
python3 scripts/execute-json-ops.py ops.json --dry-run
python3 scripts/execute-json-ops.py ops.json
```

---

## Adopting in Your Project — Summary

| Your AI tool | What to copy | What to configure |
|---|---|---|
| **Claude Code** | `scripts/` + `.claude/` + `CLAUDE.md` | Edit CLAUDE.md with project name and test command |
| **Cursor** | `scripts/` | Create `.cursor/rules/ops-config.mdc` |
| **GitHub Copilot** | `scripts/` | Create `.github/copilot-instructions.md` |
| **ChatGPT / GPT-4** | `scripts/` | Add to Custom Instructions or system prompt |
| **Gemini** | `scripts/` | Add to system instructions |
| **Other AI tools** | `scripts/` | Add to your tool's instruction file |
| **No AI** | `scripts/` | Nothing — write ops.json manually |

**Optional for all:** Add protected files for your stack in `scripts/validate-config-json.py` → `PROTECTED_PATTERNS`:

```python
# Already included: .gitignore, *.md, Makefile, Dockerfile, requirements.txt,
#   package.json, package-lock.json, yarn.lock, pyproject.toml, setup.py,
#   setup.cfg, Pipfile, Pipfile.lock, tsconfig.json
# Add for your stack:
#   Java:  "build.gradle.kts", "settings.gradle.kts", "gradlew", "pom.xml"
#   iOS:   "Podfile", "Podfile.lock"
#   CI/CD: ".github/workflows/*.yml", ".gitlab-ci.yml"
```

---

## Why This Works Beyond Cost

**Deterministic** — The `find` pattern is exact. If the AI guessed wrong, the validator rejects it before any file is touched. No "AI interpreted my intent slightly wrong" surprises after the fact.

**Auditable** — Every ops.json is a file in version control. Code review is reading a list of exact find-replace operations. Diffs are predictable.

**Reversible** — Full backup before every change. Restore any plan in one command. The backup is never deleted automatically.

**Composable** — Chain multiple ops.json files for large refactors. Each part executes atomically with its own backup. One part failing does not corrupt others.

**LLM-agnostic** — The pattern works with any instruction-following model. Claude, GPT-4, Gemini, Cursor, Copilot Workspace — the ops.json format is plain JSON.

**Language-agnostic** — The scripts operate on plain text files. Java, Python, TypeScript, Go, Swift, Kotlin, Ruby — any text-based codebase works.

---

## Requirements

| Requirement | Notes |
|---|---|
| Python 3.6+ | No external packages required |
| Any OS | macOS, Linux, Windows — cross-platform path handling |
| `jsonschema` | Optional. Enables strict schema validation. `pip3 install jsonschema` |
| `pytest` | Optional. For running the test suite. `pip3 install pytest` |

**Zero npm. Zero pip installs for core functionality.** Everything runs on Python's standard library.

**CI tested:** Python 3.9, 3.11, 3.12 on Ubuntu. 80 tests, 77% coverage.

---

## Project Structure

```
CodeManifest/
├── scripts/
│   ├── validate-config-json.py    29-guard pre-flight validator
│   ├── execute-json-ops.py        Safe executor with auto-backup + manifest
│   ├── restore-backup.py          One-command recovery with 10 safety guards
│   └── operations-schema.json     Strict JSON Schema (used by validator)
│
├── .claude/skills/                Claude Code slash commands (copy to your project)
│   ├── generate-operations-config/SKILL.md   /generate-ops — AI produces ops.json
│   ├── validate-operations-config/SKILL.md   /validate-ops — AI validates ops.json
│   └── execute-operations-config/SKILL.md    /execute-ops  — AI runs executor
│
├── skills/                        Generic skill files (for any LLM)
│   ├── generate-operations-config.md
│   ├── validate-operations-config.md
│   └── execute-operations-config.md
│
├── tests/                         80 tests, 77% coverage
│   ├── conftest.py                Shared fixtures
│   ├── test_validator.py          Validator tests (all 29 guards)
│   └── test_executor.py           Executor tests (protected files, partial edits, etc.)
│
├── examples/
│   ├── sample/                    Real files the examples run against
│   ├── 01-simple-edit.json        Single file, single edit (legacy format)
│   ├── 02-multi-file-edit.json    Two files, two edits (legacy format)
│   └── 03-file-operations.json    File create + file delete (modern format)
│
├── templates/
│   └── CLAUDE.md.template         Drop into any project to activate the pattern
│
├── .github/workflows/ci.yml      CI: validate examples + run tests on Python 3.9/3.11/3.12
│
└── CLAUDE.md                      Project context for AI-assisted development
```

---

## License

MIT — use freely in personal and commercial projects.

---

## Contributing

The scripts, skills, and examples are all plain text files.
This repo dogfoods its own pattern — contributions use ops.json for code changes.

See `CLAUDE.md` for the development workflow.

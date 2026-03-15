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

## Making the AI Generate ops.json Automatically

By default, you need to manually ask the AI to produce ops.json.
The skills in `skills/` eliminate that — they teach the AI its role once, so it applies the pattern automatically on every request.

### What a skill is

A skill is a markdown file that gives the AI a precise role and decision tree.
The AI reads it before responding, then follows it exactly.

```
skills/
├── generate-operations-config.md   # AI produces ops.json, does NOT write code
├── validate-operations-config.md   # AI reviews ops.json before execution
└── execute-operations-config.md    # AI runs the executor script
```

### Claude Code setup

**Step 1:** Copy the scripts and skills into your project:

```bash
# Copy scripts
cp -r scripts/ your-project/scripts/

# Copy the pre-configured .claude/skills/ directory
cp -r .claude/ your-project/.claude/
```

This gives you three slash commands that Claude Code recognizes automatically:

| Slash command | What it does |
|---|---|
| `/generate-ops <task>` | AI reads files and creates `ops.json` (never writes code directly) |
| `/validate-ops <path>` | Runs the validator script + dry-run, reports APPROVED/REJECTED |
| `/execute-ops <path>` | Runs dry-run, then real execution, then verifies with tests |

Each skill prints `[SKILL: name]` tags so you can verify it was invoked.

**Step 2:** Add a `CLAUDE.md` to your project:

```bash
cp templates/CLAUDE.md.template your-project/CLAUDE.md
# Edit: fill in your project name and test command
```

**Step 3:** Use it:

```
You: "Add logging to src/app.py"

Claude automatically:
1. /generate-ops → reads files, creates operations/add-logging/ops.json
2. /validate-ops → runs validator, reports APPROVED
3. /execute-ops → dry-run, execute, verify with tests
```

### Other LLMs (GPT-4, Gemini, Cursor, Copilot)

Paste the skill content into your system prompt or instruction file.
The concepts are identical — only the invocation mechanism differs.

```
System prompt addition:
"When asked to implement any code change, follow this workflow:
 1. Read every target file first.
 2. Produce ops.json describing the exact changes (MODERN format with operations/type).
 3. Stop. Do NOT write code directly.
 [paste contents of .claude/skills/generate-operations-config/SKILL.md here]"
```

---

## Adopting in Your Project

**4 steps, under 5 minutes:**

```bash
# Step 1: Copy scripts + skills into your project
cp -r scripts/ your-project/scripts/
cp -r .claude/ your-project/.claude/

# Step 2: Set up CLAUDE.md
cp templates/CLAUDE.md.template your-project/CLAUDE.md
# Edit: fill in your project name and test command

# Step 3: (Optional) Add your stack's protected files
# Open scripts/validate-config-json.py → find PROTECTED_PATTERNS
# Already included: .gitignore, *.md, Makefile, Dockerfile, requirements.txt,
#   package.json, package-lock.json, yarn.lock, pyproject.toml, setup.py,
#   setup.cfg, Pipfile, Pipfile.lock, tsconfig.json
# Add more for your stack:
#   Java/Gradle: "build.gradle.kts", "settings.gradle.kts", "gradlew"
#   iOS:         "Podfile", "Podfile.lock"
#   CI/CD:       ".github/workflows/*.yml"

# Step 4: Test it — ask Claude to make a small change
# Claude will use /generate-ops, /validate-ops, /execute-ops automatically
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

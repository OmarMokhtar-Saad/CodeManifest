# CodeManifest Setup — Claude Code

Set up the Operations Config Pattern in this project. Download scripts, create skill files, create CLAUDE.md, and run an integration test.

---

## Step 1: Download Scripts

```bash
mkdir -p scripts
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/validate-config-json.py -o scripts/validate-config-json.py
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/execute-json-ops.py -o scripts/execute-json-ops.py
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/restore-backup.py -o scripts/restore-backup.py
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/shared.py -o scripts/shared.py
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/operations-schema.json -o scripts/operations-schema.json
```

If curl is unavailable:

```bash
git clone --depth 1 https://github.com/OmarMokhtar-Saad/CodeManifest.git /tmp/codemanifest-setup
cp /tmp/codemanifest-setup/scripts/* scripts/
rm -rf /tmp/codemanifest-setup
```

Verify all 4 files exist:

```bash
ls scripts/validate-config-json.py scripts/execute-json-ops.py scripts/restore-backup.py scripts/operations-schema.json
```

---

## Step 2: Create Claude Code Skills

Create 3 skill files in `.claude/skills/`.

### Skill 1: generate-operations-config

```bash
mkdir -p .claude/skills/generate-operations-config
```

Create `.claude/skills/generate-operations-config/SKILL.md` with this exact content:

~~~markdown
---
name: generate-operations-config
description: Tells the AI how to produce an ops.json file for any code change task
---

# Generate Operations Config Skill

**Purpose**: Produce a token-efficient `ops.json` file instead of writing code directly.

**Rule**: Your output for ANY code change is `ops.json`. You do NOT write code. You do NOT edit files.

---

## JSON Schema Reference

### Two Supported Formats

**LEGACY** (code edits only):
```json
{
  "plan": "plan-name",
  "files": [
    {
      "path": "relative/path/to/file.py",
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

**MODERN** (create, delete, edit):
```json
{
  "plan": "plan-name",
  "operations": [
    {
      "type": "file_create",
      "path": "src/new_module.py",
      "content": "def new_function():\n    pass\n"
    },
    {
      "type": "code_edit",
      "path": "src/app.py",
      "edits": [
        {
          "find": "VERSION = \"1.0.0\"",
          "replace": "VERSION = \"1.1.0\""
        }
      ]
    },
    {
      "type": "file_delete",
      "path": "src/old_module.py",
      "reason": "Replaced by new_module.py with improved implementation"
    }
  ]
}
```

---

## Operation Types

### `file_create`
Create a new file.
- Required: `type`, `path`, `content`
- The file must NOT already exist
- Parent directory must exist
- Content must not be empty

### `file_delete`
Delete a file (backed up automatically before deletion).
- Required: `type`, `path`, `reason`
- The file must exist
- The file must not be protected (see Protected Files below)
- `reason` must be at least 10 characters
- Max 3 deletions per config

### `code_edit`
Edit an existing file using find-replace patterns.
- Required: `type`, `path`, `edits`
- File must exist
- Each edit requires a `find` pattern and one action

**Edit Actions**:

| Action | Description |
|---|---|
| `replace` | Replace the matched text with new content |
| `add_after` | Insert content immediately after the matched text |
| `add_before` | Insert content immediately before the matched text |
| `delete` | Remove the matched text (set to `true`) |

---

## JSON Escape Sequences

| In file | In JSON string |
|---|---|
| newline | `\n` |
| tab | `\t` |
| double quote | `\"` |
| backslash | `\\` |

---

## Constraints

- **Max 5 operations** per config (any mix of create/delete/edit)
- **Max 3 deletions** per config
- If task needs more than 5 operations, split into `part1-ops.json`, `part2-ops.json`, etc.
- **No extra fields** — the schema uses `additionalProperties: false`

**Forbidden fields** (will fail validation):
- `description`, `metadata`, `author`, `old_code`, `new_code`, `action`
- Mixing `files` and `operations` in the same config

---

## Protected Files (Cannot Be Deleted)

Default list (already enforced by `validate-config-json.py`):
```
.gitignore, *.md, Makefile, Dockerfile, docker-compose.yml
requirements.txt, package.json, pyproject.toml, setup.py
```

---

## Workflow

### Step 1: Read Every Target File First

**This is the most important step.** The `find` pattern must match the file content exactly.

For every file you will edit:
1. Read the entire file
2. Copy the exact text block you want to target
3. Convert to JSON string (replace newlines with `\n`, tabs with `\t`)
4. Use that as the `find` pattern

**Never guess what the code looks like. Never paraphrase. Copy exactly.**

### Step 2: Check File Count

```
total operations = file_create + file_delete + code_edit

if total > 5:
    parts = ceil(total / 5)
    create part1-ops.json, part2-ops.json, etc.
```

### Step 3: Write ops.json

Create the config file at `operations/{plan-name}/ops.json`.

### Step 4: Verify Before Submitting

- [ ] Every target file was read before writing `find` patterns
- [ ] `find` patterns use correct JSON escape sequences
- [ ] `find` patterns are unique in their file (appear exactly once)
- [ ] Max 5 operations per config
- [ ] No forbidden/extra fields
- [ ] File paths are correct (files exist for edits/deletes)

---

## Common Patterns

### Adding an import

```json
{
  "find": "import os\nimport sys",
  "replace": "import os\nimport sys\nimport logging"
}
```

### Adding code inside a function

```json
{
  "find": "def start():\n    setup()",
  "replace": "def start():\n    logger.info('Starting')\n    setup()"
}
```

### Fixing an ambiguous pattern

If `find` matches multiple places, expand the context to make it unique:

```json
{
  "find": "def process_user(user):\n    validate(user)\n    save(user)",
  "replace": "def process_user(user):\n    validate(user)\n    log(user)\n    save(user)"
}
```

---

## Next Step

After generating ops.json, the Validator reviews it using the `validate-operations-config` skill.
~~~

### Skill 2: validate-operations-config

```bash
mkdir -p .claude/skills/validate-operations-config
```

Create `.claude/skills/validate-operations-config/SKILL.md` with this exact content:

~~~markdown
---
name: validate-operations-config
description: Tells the AI how to review an ops.json before execution
---

# Validate Operations Config Skill

**Purpose**: Review `ops.json` files for correctness before execution.

**Rule**: Reject any plan without a valid ops.json. No exceptions.

---

## Mandatory Rejection Rules

Immediately reject if:

1. No `operations/{plan-name}/` folder exists
2. Folder exists but no `*.json` files inside
3. Any config has more than 5 operations
4. JSON syntax is invalid
5. `find` pattern is empty (`""`)
6. `find` pattern does not exist in the target file
7. Attempting to delete a protected file

---

## Validation Order

```
1. ops.json file exists?
   NO  -> REJECT immediately
   YES |

2. JSON syntax valid?
   NO  -> REJECT with syntax error location
   YES |

3. Operations count <= 5?
   NO  -> REJECT, request split into parts
   YES |

4. Run automated validator:
   python3 scripts/validate-config-json.py ops.json
   FAIL -> REJECT with errors + fix suggestions
   PASS |

5. Manual checklist (below)
   ANY FAIL -> REJECT with specific fix
   ALL PASS |

6. APPROVE
```

---

## Automated Validator

Always run first:

```bash
python3 scripts/validate-config-json.py operations/{plan-name}/ops.json
```

Expected output when valid:
```
Validating: ops.json

  JSON syntax valid
  All required fields present
  All file paths valid
  All find patterns exist in files

-> APPROVED
```

If it fails, provide the exact error message to the Planner with a fix suggestion.

---

## Manual Checklist

Even after automated validator passes:

**Structure**
- [ ] `plan` field is present and matches the folder name
- [ ] No extra fields (schema uses `additionalProperties: false`)
- [ ] No mixing of `files` and `operations` in the same config

**File Paths**
- [ ] All paths point to existing files (for `code_edit` and `file_delete`)
- [ ] Parent directories exist (for `file_create`)
- [ ] No protected files targeted for deletion

**Find Patterns**
- [ ] Every `find` pattern exists in the target file
- [ ] Every `find` pattern appears exactly once (not ambiguous)
- [ ] JSON escape sequences are correct (`\n` for newlines, `\t` for tabs)

**Logic**
- [ ] Changes make sense for the stated goal
- [ ] No unintended side effects

---

## Fix Suggestion Format

For every issue found, provide:

```
Issue: [title]
Location: ops.json, operation N, edit M
File: path/to/file
Problem: what is wrong
Fix: exact steps to correct it

Before:
  [current incorrect JSON]

After:
  [corrected JSON]
```

---

## Common Issues and Fixes

### Pattern not found in file

**Cause**: AI guessed the code instead of reading the file.

**Fix**:
```
1. Read the target file
2. Copy the exact text block (preserve all whitespace)
3. Convert newlines to \n, tabs to \t
4. Update the find pattern
```

### Pattern matches multiple locations

**Cause**: Find pattern is too short/generic.

**Fix**: Expand the context to include surrounding code that makes it unique.

### Extra fields causing schema rejection

**Cause**: AI added non-standard fields like `description`, `old_code`, `metadata`.

**Fix**: Remove all fields not in the allowed list:
- Top level: `plan`, `files` OR `plan`, `operations`
- Per operation: `type`, `path`, `content`/`edits`/`reason`
- Per edit: `find`, `add_after`/`add_before`/`replace`/`delete`

---

## Decision Matrix

| Condition | Action |
|---|---|
| No ops.json | REJECT immediately |
| Invalid JSON | REJECT with line number |
| > 5 operations | REJECT, request split |
| Validator passes + all checks OK | APPROVE |
| Validator passes + minor issues | REJECT with specific fixes |
| Validator fails | REJECT with fix suggestions |

---

## Next Step

After approval, execution follows the `execute-operations-config` skill.
~~~

### Skill 3: execute-operations-config

```bash
mkdir -p .claude/skills/execute-operations-config
```

Create `.claude/skills/execute-operations-config/SKILL.md` with this exact content:

~~~markdown
---
name: execute-operations-config
description: Tells the AI how to run the executor script for an approved ops.json
---

# Execute Operations Config Skill

**Purpose**: Execute an approved `ops.json` using the Python executor script.

**Rule**: When `ops.json` exists for a plan, NEVER use Edit/Write tools to implement manually.
Run the script. That's it.

**Token cost**: ~500 tokens. Manual implementation: ~20,000 tokens. This is why the skill exists.

---

## Core Command

```bash
# For a single-part plan:
python3 scripts/execute-json-ops.py operations/{plan-name}/ops.json

# For a multi-part plan:
for part in $(ls operations/{plan-name}/part*.json | sort); do
  python3 scripts/execute-json-ops.py "$part" || exit 1
done
```

---

## Full Workflow

### Step 1: Confirm ops.json is validated

Config must have passed `validate-config-json.py` before execution.

```bash
python3 scripts/validate-config-json.py operations/{plan-name}/ops.json
```

If not yet validated, run validation first.

### Step 2: Dry run

Always preview before applying:

```bash
python3 scripts/execute-json-ops.py operations/{plan-name}/ops.json --dry-run
```

Expected output:
```
Plan: my-plan-name
Format: LEGACY
Operations: 3

DRY RUN MODE - No changes will be made

[1/3] CODE_EDIT: src/app.py
  [DRY RUN] Would write 1240 bytes to: src/app.py

[2/3] CODE_EDIT: src/config.py
  [DRY RUN] Would write 890 bytes to: src/config.py

[3/3] FILE_CREATE: src/logger.py
  [DRY RUN] Would create: src/logger.py

--------------------------------------------------
DRY RUN COMPLETE
```

Review: operations list correct? File paths right? Operation count expected?

### Step 3: Execute

```bash
python3 scripts/execute-json-ops.py operations/{plan-name}/ops.json
```

The script automatically:
1. Creates `backups/{plan-name}-{timestamp}/` with copies of every file it will touch
2. Writes `manifest.json` for restore compatibility
3. Applies all operations in sequence
4. Reports results

### Step 4: Verify

```bash
# Check what changed
git diff

# [TODO - replace with your project's test command]
# Python:     pytest
# Node.js:    npm test
# Java/Maven: mvn test
# Java/Gradle: ./gradlew test
# Go:         go test ./...
```

### Step 5: Report

```
Implementation Complete

Operations: N/N successful
Files modified: X
Files created: Y
Files deleted: Z
Backup: backups/{plan-name}-{timestamp}/

Changes:
1. [file] - [what changed]
2. [file] - [what changed]
```

---

## Error Handling

### If a find pattern is not found

```
Edit 2: Pattern not found (may have been changed by previous edit)
```

**What happened**: The `find` pattern doesn't match current file content.
**What to do**:
1. The script stops — files are backed up and safe
2. Report to the Planner to fix the `find` pattern
3. Do NOT manually fix the file
4. Restore if needed: `python3 scripts/restore-backup.py --list`

### If an operation fails

The script backs up all files before starting. If any operation fails:
1. Files that were already modified: check the backup
2. Restore: `python3 scripts/restore-backup.py --backup backups/{plan-name}-{timestamp}`

---

## Rollback

If anything goes wrong after execution:

```bash
# List available backups
python3 scripts/restore-backup.py --list

# Restore from a specific backup
python3 scripts/restore-backup.py --backup backups/{plan-name}-20240101-120000

# Restore without confirmation prompt
python3 scripts/restore-backup.py --backup backups/{plan-name}-20240101-120000 --force
```

---

## Blocker: Do Not Edit Manually

If `ops.json` exists for the current plan, the Edit tool is BLOCKED.

```
BLOCKER: operations/{plan-name}/ops.json exists.

Manual edits are forbidden when an operations config is present.

Run: python3 scripts/execute-json-ops.py operations/{plan-name}/ops.json
```

The only exception: if you need to READ a file to understand context.
Reading is allowed. Editing is not.

---

## Quick Reference

```bash
# Validate
python3 scripts/validate-config-json.py operations/{plan}/ops.json

# Dry run
python3 scripts/execute-json-ops.py operations/{plan}/ops.json --dry-run

# Execute
python3 scripts/execute-json-ops.py operations/{plan}/ops.json

# List backups
python3 scripts/restore-backup.py --list

# Restore
python3 scripts/restore-backup.py --backup backups/{plan}-{timestamp}
```
~~~

---

## Step 3: Create CLAUDE.md

If a `CLAUDE.md` already exists in this project, **add** the following section to it. If it does not exist, create `CLAUDE.md` with this content:

```markdown
# Your Project Name

## AI-Assisted Code Changes

All implementation plans require an `ops.json` config file.
Plans without ops.json are rejected. No exceptions.

### Workflow

1. Validate: `python3 scripts/validate-config-json.py path/to/ops.json`
2. Dry run:  `python3 scripts/execute-json-ops.py path/to/ops.json --dry-run`
3. Execute:  `python3 scripts/execute-json-ops.py path/to/ops.json`
4. Restore:  `python3 scripts/restore-backup.py --backup backups/<backup-dir>`

### AI Role (MANDATORY)

When asked to make any code change:
1. Read every target file first
2. Produce `ops.json` describing the exact changes
3. Stop — do NOT write code directly

Follow the `generate-operations-config` skill for the full format reference.

### ops.json Format

```json
{
  "plan": "plan-name-in-kebab-case",
  "operations": [
    {
      "type": "code_edit",
      "path": "relative/path/to/file.py",
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

### Operation Types

- `code_edit` — edit existing file (find + replace/add_after/add_before/delete)
- `file_create` — create new file with content
- `file_delete` — delete file (requires `reason` field, min 10 chars)

### Constraints

- Maximum 5 operations per config (split into parts if more)
- Maximum 3 file deletions per config
- `find` pattern must appear exactly once in the file
- No extra fields — schema uses `additionalProperties: false`
- Protected files cannot be deleted (*.md, .gitignore, package.json, etc.)

### Skills (Claude Code)

If using Claude Code, register these skills in `.claude/skills/`:

| Trigger | Skill File | Purpose |
|---|---|---|
| Any code change request | `generate-operations-config.md` | AI produces ops.json |
| Plan review | `validate-operations-config.md` | AI validates ops.json |
| Plan execution | `execute-operations-config.md` | AI runs executor script |

### Folder Structure

```
operations/
  <plan-name>/
    ops.json         (or part1-ops.json, part2-ops.json for large plans)
backups/
  <plan-name>-<timestamp>/
    manifest.json
    <backed-up files>
```
```

---

## Step 4: Create AGENTS.md (Optional)

Create `AGENTS.md` for universal AI tool compatibility:

```markdown
# AGENTS.md

## Code Changes

All code changes use the **Operations Config Pattern**.
AI describes changes in `ops.json`. Python executes them.

**Scripts directory**: `scripts/`

## Workflow

1. **Read** every target file before writing any `find` pattern
2. **Generate** `ops.json` at `operations/{plan-name}/ops.json`
3. **Validate**: `python3 scripts/validate-config-json.py operations/{plan-name}/ops.json`
4. **Dry run**: `python3 scripts/execute-json-ops.py operations/{plan-name}/ops.json --dry-run`
5. **Execute**: `python3 scripts/execute-json-ops.py operations/{plan-name}/ops.json`

## ops.json Format

```json
{
  "plan": "plan-name",
  "operations": [
    {
      "type": "code_edit",
      "path": "relative/path/to/file",
      "edits": [
        {
          "find": "exact text to match",
          "replace": "replacement text"
        }
      ]
    }
  ]
}
```

## Edit Actions

| Action | Description |
|---|---|
| `replace` | Replace matched text with new content |
| `add_after` | Insert content after matched text |
| `add_before` | Insert content before matched text |
| `delete` | Remove matched text (set to `true`) |

## Operation Types

- `code_edit` — edit existing file (requires `path`, `edits`)
- `file_create` — create new file (requires `path`, `content`)
- `file_delete` — delete file (requires `path`, `reason` min 10 chars)

## Constraints

- Max **5 operations** per config (split into `part1-ops.json`, `part2-ops.json` if more)
- Max **3 deletions** per config
- `find` must appear **exactly once** in the target file
- No extra fields — schema enforces `additionalProperties: false`
- **Never** edit files directly when `ops.json` exists for the plan

## Restore

```bash
python3 scripts/restore-backup.py --list
python3 scripts/restore-backup.py --backup backups/{plan-name}-{timestamp}
```
```

---

## Step 5: Verify Installation

Confirm all files exist:

```bash
echo "=== Scripts ==="
ls scripts/validate-config-json.py scripts/execute-json-ops.py scripts/restore-backup.py scripts/operations-schema.json

echo "=== Skills ==="
ls .claude/skills/generate-operations-config/SKILL.md
ls .claude/skills/validate-operations-config/SKILL.md
ls .claude/skills/execute-operations-config/SKILL.md

echo "=== Config ==="
ls CLAUDE.md
ls AGENTS.md 2>/dev/null && echo "AGENTS.md present" || echo "AGENTS.md skipped (optional)"
```

All scripts and skills must be present. If any are missing, re-run the relevant step above.

---

## Step 6: Integration Test

Run a full round-trip test to verify everything works together.

### 6a. Find a source file

Find any source file in the project (`.py`, `.js`, `.ts`, `.java`, `.go`, `.rb`, `.rs`, `.swift`, `.kt`, `.c`, `.cpp`, `.html`, `.css`). Pick the first one you find. If the project has no source files, create a temporary one:

```bash
echo 'x = 1' > _codemanifest_test_file.py
```

Record the file path and its original content.

### 6b. Create test ops.json

```bash
mkdir -p operations/codemanifest-integration-test
```

Create `operations/codemanifest-integration-test/ops.json` with an `add_before` edit that inserts a comment as the first line. Adjust `path` and `find` to match the actual file:

```json
{
  "plan": "codemanifest-integration-test",
  "operations": [
    {
      "type": "code_edit",
      "path": "<FILE_PATH>",
      "edits": [
        {
          "find": "<FIRST_LINE_OF_FILE>",
          "add_before": "# CodeManifest integration test\n"
        }
      ]
    }
  ]
}
```

### 6c. Validate

```bash
python3 scripts/validate-config-json.py operations/codemanifest-integration-test/ops.json
```

**Expected**: `-> APPROVED`

### 6d. Dry run

```bash
python3 scripts/execute-json-ops.py operations/codemanifest-integration-test/ops.json --dry-run
```

**Expected**: `DRY RUN COMPLETE`

### 6e. Execute

```bash
python3 scripts/execute-json-ops.py operations/codemanifest-integration-test/ops.json
```

**Expected**: `EXECUTION COMPLETE` and `1 successful`

### 6f. Verify

Read the file and confirm `# CodeManifest integration test` appears at the top.

### 6g. Restore

```bash
python3 scripts/restore-backup.py --list
python3 scripts/restore-backup.py --backup backups/codemanifest-integration-test-* --force
```

Read the file and confirm it matches the original content.

### 6h. Clean up

```bash
rm -rf operations/codemanifest-integration-test
rm -f _codemanifest_test_file.py
```

---

## Step 7: Report

```
CodeManifest Setup — Claude Code
=================================
Scripts downloaded:        PASS / FAIL
Skills created (3):       PASS / FAIL
CLAUDE.md created:        PASS / FAIL
AGENTS.md created:        PASS / SKIPPED
Validate (-> APPROVED):   PASS / FAIL
Dry run (DRY RUN):        PASS / FAIL
Execute (1 successful):   PASS / FAIL
Comment inserted:         PASS / FAIL
Backup restored:          PASS / FAIL
File matches original:    PASS / FAIL
=================================
Result: ALL PASSED / X FAILED
```

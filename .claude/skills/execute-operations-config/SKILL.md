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
python scripts/execute-json-ops.py operations/{plan-name}/ops.json

# For a multi-part plan:
for part in $(ls operations/{plan-name}/part*.json | sort); do
  python scripts/execute-json-ops.py "$part" || exit 1
done
```

---

## Full Workflow

### Step 1: Confirm ops.json is validated

Config must have passed `validate-config-json.py` before execution.

```bash
python scripts/validate-config-json.py operations/{plan-name}/ops.json
```

If not yet validated, run validation first.

### Step 2: Dry run

Always preview before applying:

```bash
python scripts/execute-json-ops.py operations/{plan-name}/ops.json --dry-run
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
python scripts/execute-json-ops.py operations/{plan-name}/ops.json
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
# Ruby:       bundle exec rspec
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

## Multi-Part Execution

For plans split into multiple configs, order matters:
- part1 may CREATE files that part2 EDITs
- Execute sequentially, stop on failure

```bash
for part in $(ls operations/{plan-name}/part*.json | sort); do
  echo "Executing: $part"
  python scripts/execute-json-ops.py "$part"
  if [ $? -ne 0 ]; then
    echo "Part failed. Stopping."
    exit 1
  fi
done
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
4. Restore if needed: `python scripts/restore-backup.py --list`

### If an operation fails

The script backs up all files before starting. If any operation fails:
1. Files that were already modified: check the backup
2. Restore: `python scripts/restore-backup.py --backup backups/{plan-name}-{timestamp}`

---

## Rollback

If anything goes wrong after execution:

```bash
# List available backups
python scripts/restore-backup.py --list

# Restore from a specific backup
python scripts/restore-backup.py --backup backups/{plan-name}-20240101-120000

# Restore without confirmation prompt
python scripts/restore-backup.py --backup backups/{plan-name}-20240101-120000 --force
```

---

## Blocker: Do Not Edit Manually

If `ops.json` exists for the current plan, the Edit tool is BLOCKED.

```
BLOCKER: operations/{plan-name}/ops.json exists.

Manual edits are forbidden when an operations config is present.

Run: python scripts/execute-json-ops.py operations/{plan-name}/ops.json
```

The only exception: if you need to READ a file to understand context.
Reading is allowed. Editing is not.

---

## Quick Reference

```bash
# Validate
python scripts/validate-config-json.py operations/{plan}/ops.json

# Dry run
python scripts/execute-json-ops.py operations/{plan}/ops.json --dry-run

# Execute
python scripts/execute-json-ops.py operations/{plan}/ops.json

# List backups
python scripts/restore-backup.py --list

# Restore
python scripts/restore-backup.py --backup backups/{plan}-{timestamp}
```

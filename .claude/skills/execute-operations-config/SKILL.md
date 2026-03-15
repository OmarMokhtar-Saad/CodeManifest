---
name: execute-ops
description: Execute an approved ops.json — runs the executor script with backup. Use after /validate-ops.
argument-hint: "[path/to/ops.json]"
---

# /execute-ops — Execute Operations Config

When this skill is invoked, you MUST:

1. Print: `[SKILL: execute-ops] Executing: <path>`
2. Run dry-run first, then real execution
3. Verify the changes
4. Print: `[SKILL: execute-ops] Done — N operations applied, backup at backups/<dir>`

---

## Step 0: Find the scripts

Look for `SCRIPTS_DIR` in `CLAUDE.md`. If not found, search for `validate-config-json.py`:

```bash
find . -name "validate-config-json.py" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null
```

Use the directory where the scripts are found. Default: `scripts/`.

---

## Step 1: Dry-run (mandatory)

```bash
python3 <SCRIPTS_DIR>/execute-json-ops.py <path-to-ops.json> --dry-run
```

Show output. If any issues, STOP.

## Step 2: Execute

```bash
python3 <SCRIPTS_DIR>/execute-json-ops.py <path-to-ops.json>
```

Show full output.

## Step 3: Verify

Show the modified files to confirm changes applied:

```bash
cat <each-modified-file>
```

Run the project's test command (check CLAUDE.md for the test command):

```bash
# Default: python3 -m pytest tests/ -v
# Or whatever is specified in CLAUDE.md
```

## Step 4: Report

```
[SKILL: execute-ops] Done
  Operations: N/N successful
  Files modified: <list>
  Backup: backups/{plan-name}-{timestamp}/
  Tests: PASS (N passed)
```

## Rollback (if needed)

```bash
python3 <SCRIPTS_DIR>/restore-backup.py --list
python3 <SCRIPTS_DIR>/restore-backup.py --backup backups/{plan-name}-{timestamp} --force
```

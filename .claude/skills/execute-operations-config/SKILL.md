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

## Procedure

### Step 1: Dry-run (mandatory)

```bash
python3 scripts/execute-json-ops.py <path-to-ops.json> --dry-run
```

Show output. If any issues, STOP.

### Step 2: Execute

```bash
python3 scripts/execute-json-ops.py <path-to-ops.json>
```

Show full output.

### Step 3: Verify

Show the modified files to confirm changes applied:

```bash
cat <each-modified-file>
```

Run tests:

```bash
python3 -m pytest tests/ -v
```

### Step 4: Report

```
[SKILL: execute-ops] Done
  Operations: N/N successful
  Files modified: <list>
  Backup: backups/{plan-name}-{timestamp}/
  Tests: PASS (N passed)
```

## Rollback (if needed)

```bash
python3 scripts/restore-backup.py --list
python3 scripts/restore-backup.py --backup backups/{plan-name}-{timestamp} --force
```

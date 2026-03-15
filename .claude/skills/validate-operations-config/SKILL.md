---
name: validate-ops
description: Validate an ops.json config by running the validator and dry-run. Use after /generate-ops.
argument-hint: "[path/to/ops.json]"
---

# /validate-ops — Validate Operations Config

When this skill is invoked, you MUST:

1. Print: `[SKILL: validate-ops] Validating: <path>`
2. Run the validator and dry-run
3. Print: `[SKILL: validate-ops] Result: APPROVED` or `[SKILL: validate-ops] Result: REJECTED — <reason>`

---

## Step 0: Find the scripts

Look for `SCRIPTS_DIR` in `CLAUDE.md`. If not found, search for `validate-config-json.py`:

```bash
find . -name "validate-config-json.py" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null
```

Use the directory where the scripts are found. Default: `scripts/`.

---

## Step 1: Run the automated validator

```bash
python3 <SCRIPTS_DIR>/validate-config-json.py <path-to-ops.json>
```

Show the full output.

- If `-> APPROVED`: proceed to Step 2
- If `-> REJECTED`: print errors and STOP. Run `/generate-ops` again to fix.

## Step 2: Run dry-run

```bash
python3 <SCRIPTS_DIR>/execute-json-ops.py <path-to-ops.json> --dry-run
```

Show the full output. Confirm:
- Operation count matches expected
- File paths are correct
- No errors

## Step 3: Report verdict

```
[SKILL: validate-ops] Result: APPROVED
  Validator: PASSED
  Dry-run: N operations previewed, 0 errors
  Ready for: /execute-ops <path>
```

Or if failed:

```
[SKILL: validate-ops] Result: REJECTED
  Error: <specific error from validator>
  Fix: <what to change in ops.json>
```

## Next step

After approval, run `/execute-ops` to apply the changes.

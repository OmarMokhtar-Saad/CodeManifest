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
   NO  → REJECT immediately
   YES ↓

2. JSON syntax valid?
   NO  → REJECT with syntax error location
   YES ↓

3. Operations count ≤ 5?
   NO  → REJECT, request split into parts
   YES ↓

4. Run automated validator:
   python scripts/validate-config-json.py ops.json
   FAIL → REJECT with errors + fix suggestions
   PASS ↓

5. Manual checklist (below)
   ANY FAIL → REJECT with specific fix
   ALL PASS ↓

6. APPROVE
```

---

## Automated Validator

Always run first:

```bash
python scripts/validate-config-json.py operations/{plan-name}/ops.json
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

```json
// Before (ambiguous - matches multiple methods):
{
  "find": "validate(input);",
  "add_after": "\nlog(input);"
}

// After (unique - includes method signature):
{
  "find": "def process_input(input):\n    validate(input)\n    save(input)",
  "replace": "def process_input(input):\n    validate(input)\n    log(input)\n    save(input)"
}
```

### Extra fields causing schema rejection

**Cause**: AI added non-standard fields like `description`, `old_code`, `metadata`.

**Fix**: Remove all fields not in the allowed list:
- Top level: `plan`, `files` OR `plan`, `operations`
- Per operation: `type`, `path`, `content`/`edits`/`reason`
- Per edit: `find`, `add_after`/`add_before`/`replace`/`delete`

---

## Scoring Rubric

```
Config Quality (40 pts):
  + ops.json exists and valid:    15 pts
  + All file paths correct:       10 pts
  + Find patterns accurate:       10 pts
  + Actions appropriate:           5 pts

  - Missing ops.json:             -40 pts (auto-fail)
  - Config > 5 operations:        -15 pts
  - Empty find pattern:           -15 pts each
  - Ambiguous find pattern:       -10 pts each

Architecture quality:   30 pts (your project standards)
Security:               30 pts (your project standards)

Total: /100
```

**Approve if score ≥ 90%. Reject with fixes if < 90%.**

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

## Approval Template

```
## Review Result: APPROVED

Score: 95/100

Validation:
- ops.json exists and valid
- N operations (within 5-operation limit)
- All file paths exist
- All find patterns unique and verified
- JSON syntax valid

Execute with:
  python scripts/execute-json-ops.py operations/{plan-name}/ops.json
```

## Rejection Template

```
## Review Result: REJECTED

Score: 72/100

Issues:

Issue 1: Find pattern not found
Location: ops.json, operation 2, edit 1
File: src/app.py
Problem: Pattern "def old_method():" not in file
Fix:
  1. Read src/app.py
  2. Find the actual method name
  3. Copy exact text with correct whitespace
  4. Update find pattern with \n escapes

Required: Fix all issues above and re-submit.
```

---

## Next Step

After approval, execution follows the `execute-operations-config` skill.

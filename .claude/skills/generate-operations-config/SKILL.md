---
name: generate-ops
description: Generate an ops.json config for a code change task. Use when making ANY code change.
argument-hint: "[task description]"
---

# /generate-ops — Generate Operations Config

When this skill is invoked, you MUST:

1. Print: `[SKILL: generate-ops] Generating ops.json for: <task>`
2. Follow every step below exactly
3. Print: `[SKILL: generate-ops] Done — created operations/{plan-name}/ops.json`

---

## Step 0: Find the scripts

Look for `SCRIPTS_DIR` in `CLAUDE.md`. If not found, search for `validate-config-json.py`:

```bash
find . -name "validate-config-json.py" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null
```

Use the directory where the scripts are found for all commands. Default: `scripts/`.

---

## Step 1: Read every target file

For every file you will edit, READ THE ENTIRE FILE FIRST.
Copy the exact text for `find` patterns. Never guess. Never paraphrase.

## Step 2: Create ops.json

Create `operations/{plan-name}/ops.json` using the **MODERN format**:

```json
{
  "plan": "plan-name",
  "operations": [
    {
      "type": "code_edit",
      "path": "path/to/file.py",
      "edits": [
        {
          "find": "exact text copied from file",
          "replace": "new text"
        }
      ]
    }
  ]
}
```

## Step 3: Self-check before finishing

- [ ] Every `find` pattern was copied from an actual file read
- [ ] `find` patterns are unique in their file (appear exactly once)
- [ ] JSON escape sequences correct (`\n` for newlines, `\t` for tabs)
- [ ] Max 5 operations per config
- [ ] Used MODERN format (operations/type), NOT legacy (files)

---

## Operation types

| Type | Required fields | Description |
|------|----------------|-------------|
| `code_edit` | `type`, `path`, `edits` | Edit existing file |
| `file_create` | `type`, `path`, `content` | Create new file |
| `file_delete` | `type`, `path`, `reason` | Delete file (reason min 10 chars) |

## Edit actions

| Action | Description |
|--------|-------------|
| `replace` | Replace matched text |
| `add_after` | Insert content after match |
| `add_before` | Insert content before match |
| `delete` | Remove matched text (set to `true`) |

## Constraints

- Max 5 operations per config (split into parts if more)
- Max 3 deletions per config
- No extra fields — schema uses `additionalProperties: false`
- Protected files cannot be deleted

## Next step

After generating, run `/validate-ops` to validate the config.

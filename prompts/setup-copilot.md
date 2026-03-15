# CodeManifest Setup — GitHub Copilot

Set up the Operations Config Pattern in this project for GitHub Copilot. Download scripts, create `.github/copilot-instructions.md`, and run an integration test.

---

## Step 1: Download Scripts

```bash
mkdir -p scripts
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/validate-config-json.py -o scripts/validate-config-json.py
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/execute-json-ops.py -o scripts/execute-json-ops.py
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/restore-backup.py -o scripts/restore-backup.py
curl -sL https://raw.githubusercontent.com/OmarMokhtar-Saad/CodeManifest/main/scripts/operations-schema.json -o scripts/operations-schema.json
```

If curl is unavailable:

```bash
git clone --depth 1 https://github.com/OmarMokhtar-Saad/CodeManifest.git /tmp/codemanifest-setup
cp /tmp/codemanifest-setup/scripts/* scripts/
rm -rf /tmp/codemanifest-setup
```

Verify:

```bash
ls scripts/validate-config-json.py scripts/execute-json-ops.py scripts/restore-backup.py scripts/operations-schema.json
```

---

## Step 2: Create Copilot Instructions

```bash
mkdir -p .github
```

Create `.github/copilot-instructions.md` with this exact content:

~~~markdown
# Operations Config Pattern

All code changes use ops.json. AI describes changes in JSON. Python executes them.

## Rule

When asked to make ANY code change:
1. Read every target file first
2. Produce `ops.json` describing the exact changes
3. Stop — do NOT write code directly

## Workflow

1. Validate: `python scripts/validate-config-json.py path/to/ops.json`
2. Dry run:  `python scripts/execute-json-ops.py path/to/ops.json --dry-run`
3. Execute:  `python scripts/execute-json-ops.py path/to/ops.json`
4. Restore:  `python scripts/restore-backup.py --backup backups/<backup-dir>`

## ops.json Format

Place configs at `operations/{plan-name}/ops.json`.

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

## Operation Types

- `code_edit` — edit existing file (find + replace/add_after/add_before/delete)
- `file_create` — create new file (requires `path`, `content`)
- `file_delete` — delete file (requires `path`, `reason` min 10 chars)

## Edit Actions

| Action | Description |
|---|---|
| `replace` | Replace matched text with new content |
| `add_after` | Insert content after matched text |
| `add_before` | Insert content before matched text |
| `delete` | Remove matched text (set to `true`) |

## Constraints

- Max 5 operations per config (split into parts if more)
- Max 3 deletions per config
- `find` must appear exactly once in the target file
- No extra fields — schema uses `additionalProperties: false`
- Protected files cannot be deleted (*.md, .gitignore, package.json, etc.)
- Never edit files directly when ops.json exists for the plan

## JSON Escape Sequences

| In file | In JSON |
|---|---|
| newline | `\n` |
| tab | `\t` |
| double quote | `\"` |
| backslash | `\\` |

## Folder Structure

```
operations/
  <plan-name>/
    ops.json
backups/
  <plan-name>-<timestamp>/
    manifest.json
```
~~~

---

## Step 3: Create AGENTS.md (Optional)

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
3. **Validate**: `python scripts/validate-config-json.py operations/{plan-name}/ops.json`
4. **Dry run**: `python scripts/execute-json-ops.py operations/{plan-name}/ops.json --dry-run`
5. **Execute**: `python scripts/execute-json-ops.py operations/{plan-name}/ops.json`

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
python scripts/restore-backup.py --list
python scripts/restore-backup.py --backup backups/{plan-name}-{timestamp}
```
```

---

## Step 4: Verify + Test + Report

### Verify installation

```bash
echo "=== Scripts ==="
ls scripts/validate-config-json.py scripts/execute-json-ops.py scripts/restore-backup.py scripts/operations-schema.json

echo "=== Copilot Instructions ==="
ls .github/copilot-instructions.md

echo "=== AGENTS.md ==="
ls AGENTS.md 2>/dev/null && echo "AGENTS.md present" || echo "AGENTS.md skipped (optional)"
```

### Integration test

Find any source file in the project (`.py`, `.js`, `.ts`, `.java`, `.go`, etc.). If none exist, create a temporary one:

```bash
echo 'x = 1' > _codemanifest_test_file.py
```

Record the file path and original content. Then:

**Create test ops.json** — adjust `path` and `find` to match the actual file:

```bash
mkdir -p operations/codemanifest-integration-test
```

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

**Validate** — expect `-> APPROVED`:

```bash
python3 scripts/validate-config-json.py operations/codemanifest-integration-test/ops.json
```

**Dry run** — expect `DRY RUN COMPLETE`:

```bash
python3 scripts/execute-json-ops.py operations/codemanifest-integration-test/ops.json --dry-run
```

**Execute** — expect `EXECUTION COMPLETE` and `1 successful`:

```bash
python3 scripts/execute-json-ops.py operations/codemanifest-integration-test/ops.json
```

**Verify** — read the file, confirm `# CodeManifest integration test` appears at the top.

**Restore** — restore backup and confirm file matches original:

```bash
python3 scripts/restore-backup.py --list
python3 scripts/restore-backup.py --backup backups/codemanifest-integration-test-* --force
```

**Clean up**:

```bash
rm -rf operations/codemanifest-integration-test
rm -f _codemanifest_test_file.py
```

### Report

```
CodeManifest Setup — GitHub Copilot
=====================================
Scripts downloaded:         PASS / FAIL
Copilot instructions:       PASS / FAIL
AGENTS.md created:          PASS / SKIPPED
Validate (-> APPROVED):     PASS / FAIL
Dry run (DRY RUN):          PASS / FAIL
Execute (1 successful):     PASS / FAIL
Comment inserted:           PASS / FAIL
Backup restored:            PASS / FAIL
File matches original:      PASS / FAIL
=====================================
Result: ALL PASSED / X FAILED
```

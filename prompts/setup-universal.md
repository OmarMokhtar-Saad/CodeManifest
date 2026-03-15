# CodeManifest Setup — Universal (Any AI Tool)

Set up the Operations Config Pattern in this project for any AI tool with terminal access. Downloads scripts, auto-detects your tool and creates the appropriate config, and runs an integration test.

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

## Step 2: Auto-Detect Tool and Create Config

Check which AI tool config directories already exist and create the appropriate instruction file. If none are detected, create `AGENTS.md` as the universal default.

### Detection logic

```bash
# Check for existing tool configs
if [ -d ".claude" ]; then
  echo "Detected: Claude Code"
elif [ -d ".cursor" ]; then
  echo "Detected: Cursor"
elif [ -d ".github" ]; then
  echo "Detected: GitHub Copilot (or GitHub project)"
else
  echo "No specific tool detected — using AGENTS.md"
fi
```

### If Claude Code detected

Follow the full Claude Code setup: create 3 skill files in `.claude/skills/` and a `CLAUDE.md`. See `prompts/setup-claude-code.md` for the complete skill file contents. As a minimal setup, create `CLAUDE.md` with the content below and `AGENTS.md`.

### If Cursor detected

```bash
mkdir -p .cursor/rules
```

Create `.cursor/rules/codemanifest.mdc` — see `prompts/setup-cursor.md` for the full `.mdc` file content. The key content is the instruction block below.

### If GitHub Copilot detected

```bash
mkdir -p .github
```

Create `.github/copilot-instructions.md` — see `prompts/setup-copilot.md` for the full file content. The key content is the instruction block below.

### Default: Create AGENTS.md

For any tool (or as a universal fallback), create `AGENTS.md`:

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

## Step 3: Verify + Test + Report

### Verify installation

```bash
echo "=== Scripts ==="
ls scripts/validate-config-json.py scripts/execute-json-ops.py scripts/restore-backup.py scripts/operations-schema.json

echo "=== Config files ==="
ls AGENTS.md 2>/dev/null && echo "AGENTS.md present"
ls CLAUDE.md 2>/dev/null && echo "CLAUDE.md present"
ls .cursor/rules/codemanifest.mdc 2>/dev/null && echo "Cursor rule present"
ls .github/copilot-instructions.md 2>/dev/null && echo "Copilot instructions present"
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
CodeManifest Setup — Universal
================================
Scripts downloaded:        PASS / FAIL
Tool detected:             [Claude Code / Cursor / Copilot / None]
Config created:            PASS / FAIL
AGENTS.md created:         PASS / FAIL
Validate (-> APPROVED):    PASS / FAIL
Dry run (DRY RUN):         PASS / FAIL
Execute (1 successful):    PASS / FAIL
Comment inserted:          PASS / FAIL
Backup restored:           PASS / FAIL
File matches original:     PASS / FAIL
================================
Result: ALL PASSED / X FAILED
```

# CodeManifest Setup — ChatGPT / GPT-4

Set up the Operations Config Pattern for use with ChatGPT or GPT-4. Since ChatGPT has no terminal access, this prompt has three parts: manual setup, a system prompt to paste, and a manual test.

---

## Part A: Manual Setup (You Run These Commands)

Open a terminal in your project directory and run:

```bash
# Download scripts
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

Optionally create an `AGENTS.md` file (copy the template from `templates/AGENTS.md.template` in the CodeManifest repo).

---

## Part B: System Prompt for ChatGPT

Copy everything below the line and paste it into ChatGPT's **Custom Instructions** or as a system message in the API. This teaches the AI to produce ops.json instead of writing code.

---

### START OF SYSTEM PROMPT — copy from here

You use the **Operations Config Pattern** for all code changes. You describe changes in a JSON file called `ops.json`. You do NOT write code directly. You do NOT edit files.

#### Your workflow

1. The user shows you a file or describes a change
2. You produce `ops.json` with the exact changes
3. The user runs validation and execution scripts locally

#### ops.json format

```json
{
  "plan": "plan-name-in-kebab-case",
  "operations": [
    {
      "type": "code_edit",
      "path": "relative/path/to/file.py",
      "edits": [
        {
          "find": "exact text to find in the file",
          "replace": "replacement text"
        }
      ]
    }
  ]
}
```

#### Operation types

- `code_edit` — edit existing file. Each edit needs `find` (exact text) and one action: `replace`, `add_after`, `add_before`, or `delete` (set to `true`).
- `file_create` — create new file. Requires `path` and `content`.
- `file_delete` — delete file. Requires `path` and `reason` (min 10 chars).

#### Rules

- `find` must be the **exact text** from the file (copy-paste, never guess)
- `find` must appear **exactly once** in the target file
- Max **5 operations** per config (split into parts if more)
- Max **3 deletions** per config
- No extra fields — only `plan`, `operations`, `type`, `path`, `edits`, `find`, `replace`/`add_after`/`add_before`/`delete`, `content`, `reason`
- Use JSON escape sequences: `\n` for newlines, `\t` for tabs, `\"` for quotes, `\\` for backslashes

#### Output format

When the user asks for a code change:
1. Ask them to paste the current file content (so you can write accurate `find` patterns)
2. Produce the ops.json
3. Tell them to save it as `operations/{plan-name}/ops.json` and run:
   ```
   python scripts/validate-config-json.py operations/{plan-name}/ops.json
   python scripts/execute-json-ops.py operations/{plan-name}/ops.json --dry-run
   python scripts/execute-json-ops.py operations/{plan-name}/ops.json
   ```

If anything goes wrong, they can restore with:
```
python scripts/restore-backup.py --list
python scripts/restore-backup.py --backup backups/{plan-name}-{timestamp} --force
```

### END OF SYSTEM PROMPT — stop copying here

---

## Part C: Manual Test

Test the full round-trip to verify everything works.

### 1. Pick a test file

Choose any source file in your project, or create one:

```bash
echo 'x = 1' > _codemanifest_test_file.py
```

### 2. Ask ChatGPT to generate ops.json

Paste the file content into ChatGPT and ask:

> "Add a comment `# CodeManifest integration test` as the first line of this file. Produce ops.json."

### 3. Save and run

Save ChatGPT's output as `operations/codemanifest-integration-test/ops.json`:

```bash
mkdir -p operations/codemanifest-integration-test
# Paste the JSON into this file
```

Then run the workflow:

```bash
# Validate — expect "-> APPROVED"
python3 scripts/validate-config-json.py operations/codemanifest-integration-test/ops.json

# Dry run — expect "DRY RUN COMPLETE"
python3 scripts/execute-json-ops.py operations/codemanifest-integration-test/ops.json --dry-run

# Execute — expect "EXECUTION COMPLETE, 1 successful"
python3 scripts/execute-json-ops.py operations/codemanifest-integration-test/ops.json
```

### 4. Verify and restore

Check that the comment was added to the file, then restore:

```bash
python3 scripts/restore-backup.py --list
python3 scripts/restore-backup.py --backup backups/codemanifest-integration-test-* --force
```

### 5. Clean up

```bash
rm -rf operations/codemanifest-integration-test
rm -f _codemanifest_test_file.py
```

### Result

```
CodeManifest Setup — ChatGPT
==============================
Scripts downloaded:        PASS / FAIL
System prompt configured:  PASS / FAIL (manual)
ChatGPT produced ops.json: PASS / FAIL
Validate (-> APPROVED):    PASS / FAIL
Dry run (DRY RUN):         PASS / FAIL
Execute (1 successful):    PASS / FAIL
Comment inserted:          PASS / FAIL
Backup restored:           PASS / FAIL
==============================
Result: ALL PASSED / X FAILED
```

# CodeManifest Integration Test

Run this prompt to verify that CodeManifest is correctly set up in your project.

---

## Prerequisites

Check that the required scripts exist before running the test.

```bash
# Verify scripts are present
ls scripts/validate-config-json.py scripts/execute-json-ops.py scripts/restore-backup.py scripts/operations-schema.json
```

If any script is missing, run the setup prompt for your AI tool first (see `prompts/README.md`).

---

## Test: Full Round-Trip

Execute these steps in order. Every step must succeed.

### Step 1: Find a source file

Find any source file in the project (`.py`, `.js`, `.ts`, `.java`, `.go`, `.rb`, `.rs`, `.swift`, `.kt`, `.c`, `.cpp`, `.html`, `.css`). Pick the first one you find. If the project has no source files, create a temporary one:

```bash
echo 'x = 1' > _codemanifest_test_file.py
```

Record the file path and its original content.

### Step 2: Create test ops.json

Create `operations/codemanifest-integration-test/ops.json` with an `add_before` edit that inserts a comment as the first line of the file:

```bash
mkdir -p operations/codemanifest-integration-test
```

The ops.json should look like this (adjust `path` and `find` to match the actual file):

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

Replace `<FILE_PATH>` with the actual path and `<FIRST_LINE_OF_FILE>` with the exact first line of the file.

### Step 3: Validate

```bash
python3 scripts/validate-config-json.py operations/codemanifest-integration-test/ops.json
```

**Expected**: Output contains `-> APPROVED`

### Step 4: Dry run

```bash
python3 scripts/execute-json-ops.py operations/codemanifest-integration-test/ops.json --dry-run
```

**Expected**: Output contains `DRY RUN COMPLETE`

### Step 5: Execute

```bash
python3 scripts/execute-json-ops.py operations/codemanifest-integration-test/ops.json
```

**Expected**: Output contains `EXECUTION COMPLETE` and `1 successful`

### Step 6: Verify the change

Read the file and confirm the comment `# CodeManifest integration test` appears at the top.

### Step 7: Restore backup

```bash
python3 scripts/restore-backup.py --list
```

Find the backup for `codemanifest-integration-test` and restore it:

```bash
python3 scripts/restore-backup.py --backup backups/codemanifest-integration-test-* --force
```

Read the file again and confirm it matches the original content from Step 1.

### Step 8: Clean up

```bash
rm -rf operations/codemanifest-integration-test
```

If you created `_codemanifest_test_file.py` in Step 1, delete it too:

```bash
rm -f _codemanifest_test_file.py
```

---

## Report

Print the result:

```
CodeManifest Integration Test
=============================
Validate (-> APPROVED):    PASS / FAIL
Dry run (DRY RUN COMPLETE): PASS / FAIL
Execute (1 successful):    PASS / FAIL
Comment inserted:          PASS / FAIL
Backup restored:           PASS / FAIL
File matches original:     PASS / FAIL
=============================
Result: ALL PASSED / X FAILED
```

If any step failed, report the exact error output.

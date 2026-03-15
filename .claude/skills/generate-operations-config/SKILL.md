---
name: generate-operations-config
description: Tells the AI how to produce an ops.json file for any code change task
---

# Generate Operations Config Skill

**Purpose**: Produce a token-efficient `ops.json` file instead of writing code directly.

**Rule**: Your output for ANY code change is `ops.json`. You do NOT write code. You do NOT edit files.

---

## JSON Schema Reference

### Two Supported Formats

**LEGACY** (code edits only):
```json
{
  "plan": "plan-name",
  "files": [
    {
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

**MODERN** (create, delete, edit):
```json
{
  "plan": "plan-name",
  "operations": [
    {
      "type": "file_create",
      "path": "src/new_module.py",
      "content": "def new_function():\n    pass\n"
    },
    {
      "type": "code_edit",
      "path": "src/app.py",
      "edits": [
        {
          "find": "VERSION = \"1.0.0\"",
          "replace": "VERSION = \"1.1.0\""
        }
      ]
    },
    {
      "type": "file_delete",
      "path": "src/old_module.py",
      "reason": "Replaced by new_module.py with improved implementation"
    }
  ]
}
```

---

## Operation Types

### `file_create`
Create a new file.
- Required: `type`, `path`, `content`
- The file must NOT already exist
- Parent directory must exist
- Content must not be empty

### `file_delete`
Delete a file (backed up automatically before deletion).
- Required: `type`, `path`, `reason`
- The file must exist
- The file must not be protected (see Protected Files below)
- `reason` must be at least 10 characters
- Max 3 deletions per config

### `code_edit`
Edit an existing file using find-replace patterns.
- Required: `type`, `path`, `edits`
- File must exist
- Each edit requires a `find` pattern and one action

**Edit Actions**:

| Action | Description |
|---|---|
| `replace` | Replace the matched text with new content |
| `add_after` | Insert content immediately after the matched text |
| `add_before` | Insert content immediately before the matched text |
| `delete` | Remove the matched text (set to `true`) |

---

## JSON Escape Sequences

| In file | In JSON string |
|---|---|
| newline | `\n` |
| tab | `\t` |
| double quote | `\"` |
| backslash | `\\` |

---

## Constraints

- **Max 5 operations** per config (any mix of create/delete/edit)
- **Max 3 deletions** per config
- If task needs more than 5 operations, split into `part1-ops.json`, `part2-ops.json`, etc.
- **No extra fields** — the schema uses `additionalProperties: false`

**Forbidden fields** (will fail validation):
- `description`, `metadata`, `author`, `old_code`, `new_code`, `action`
- Mixing `files` and `operations` in the same config

---

## Protected Files (Cannot Be Deleted)

Default list (already enforced by `validate-config-json.py`):
```
.gitignore, *.md, Makefile, Dockerfile, docker-compose.yml
requirements.txt, package.json, pyproject.toml, setup.py
```

**[TODO - customize for your project]**
Open `scripts/validate-config-json.py` and add your critical files to `PROTECTED_PATTERNS`:

```python
# Examples by project type:

# Node.js
"package-lock.json", "yarn.lock", "tsconfig.json", "webpack.config.js"

# Python
"Pipfile", "Pipfile.lock", "setup.cfg", "tox.ini"

# Java/Gradle
"build.gradle", "build.gradle.kts", "settings.gradle.kts", "gradlew"

# Java/Maven
"pom.xml"

# iOS/macOS
"*.xcodeproj", "Podfile", "Podfile.lock"

# CI/CD
".github/workflows/*.yml", ".gitlab-ci.yml", "Jenkinsfile"
```

---

## Workflow

### Step 1: Read Every Target File First

**This is the most important step.** The `find` pattern must match the file content exactly.

For every file you will edit:
1. Read the entire file
2. Copy the exact text block you want to target
3. Convert to JSON string (replace newlines with `\n`, tabs with `\t`)
4. Use that as the `find` pattern

**Never guess what the code looks like. Never paraphrase. Copy exactly.**

### Step 2: Check File Count

```
total operations = file_create + file_delete + code_edit

if total > 5:
    parts = ceil(total / 5)
    create part1-ops.json, part2-ops.json, etc.
```

### Step 3: Write ops.json

Create the config file at `operations/{plan-name}/ops.json`.

### Step 4: Verify Before Submitting

- [ ] Every target file was read before writing `find` patterns
- [ ] `find` patterns use correct JSON escape sequences
- [ ] `find` patterns are unique in their file (appear exactly once)
- [ ] Max 5 operations per config
- [ ] No forbidden/extra fields
- [ ] File paths are correct (files exist for edits/deletes)

---

## Common Patterns

### Adding an import

```json
{
  "find": "import os\nimport sys",
  "replace": "import os\nimport sys\nimport logging"
}
```

### Adding code inside a function

```json
{
  "find": "def start():\n    setup()",
  "replace": "def start():\n    logger.info('Starting')\n    setup()"
}
```

### Fixing an ambiguous pattern

If `find` matches multiple places, expand the context to make it unique:

```json
{
  "find": "def process_user(user):\n    validate(user)\n    save(user)",
  "replace": "def process_user(user):\n    validate(user)\n    log(user)\n    save(user)"
}
```

---

## Example Complete Config

```json
{
  "plan": "add-request-logging",
  "files": [
    {
      "path": "src/middleware.py",
      "edits": [
        {
          "find": "def before_request():\n    pass",
          "replace": "def before_request():\n    logger.info(f'Request: {request.method} {request.path}')"
        }
      ]
    },
    {
      "path": "src/app.py",
      "edits": [
        {
          "find": "import os",
          "replace": "import os\nimport logging\n\nlogger = logging.getLogger(__name__)"
        }
      ]
    }
  ]
}
```

---

## Next Step

After generating ops.json, the Validator reviews it using the `validate-operations-config` skill.

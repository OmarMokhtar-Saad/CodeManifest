# Skills

Skills are markdown files that give the AI a precise role and decision tree for a specific task.
They are what make the AI generate `ops.json` **automatically** instead of writing code directly.

## Available Skills

| Slash command | Skill file | Purpose |
|---|---|---|
| `/generate-ops` | `generate-operations-config` | AI reads files and produces `ops.json` |
| `/validate-ops` | `validate-operations-config` | AI runs validator + dry-run, reports APPROVED/REJECTED |
| `/execute-ops` | `execute-operations-config` | AI runs executor with backup, verifies with tests |

Each skill prints `[SKILL: name]` tags so you can verify it was invoked.

## Setup — Claude Code

Copy the `.claude/skills/` directory from this repo into your project:

```bash
cp -r .claude/ your-project/.claude/
```

This creates:

```
your-project/
└── .claude/
    └── skills/
        ├── generate-operations-config/SKILL.md
        ├── validate-operations-config/SKILL.md
        └── execute-operations-config/SKILL.md
```

Claude Code auto-discovers these as slash commands. No registry file needed.

Then add a `CLAUDE.md` to your project (see `templates/CLAUDE.md.template`).

## Setup — Other LLMs (GPT-4, Gemini, Cursor, Copilot)

Use the generic skill files in `skills/` as part of your **system prompt** or **instruction file**.
The concepts are identical — only the invocation mechanism differs.

```
System prompt addition:
"When asked to implement code changes, produce an ops.json file describing
the exact changes using the MODERN format (operations/type). Do NOT write
code directly.
[paste contents of skills/generate-operations-config.md here]"
```

## How it works

```
User: "Add logging to src/app.py"
         |
   CLAUDE.md says: use ops.json pipeline
         |
   /generate-ops → reads files, creates ops.json
         |
   /validate-ops → runs validator, APPROVED
         |
   /execute-ops  → dry-run, execute, verify
         |
   Done. Changes applied with backup.
```

# Skills

Skills are markdown files that give the AI a precise role and decision tree for a specific task.
They are what make the AI generate `ops.json` **automatically** instead of writing code directly.

## How Skills Work

When the AI receives a request, your `CLAUDE.md` routes it to the correct skill.
The AI reads the skill file first, then produces the expected output — and stops.

```
User request
    |
CLAUDE.md (traffic controller)
    |
Loads matching skill
    |
AI follows skill instructions
    |
Produces ops.json (not code)
```

## Available Skills

| Skill | File | Purpose |
|---|---|---|
| Generate | `generate-operations-config.md` | AI produces `ops.json` from a task description |
| Validate | `validate-operations-config.md` | AI reviews `ops.json` before execution |
| Execute | `execute-operations-config.md` | AI runs the Python executor script |

## Setup (Claude Code)

These skills use Claude Code's `Skill` tool system.

1. Place these files anywhere in your repo (e.g., `.claude/skills/<name>/SKILL.md`)
2. Register them in `.claude/skills/skills-registry.json`
3. Reference them in your `CLAUDE.md`

See `templates/CLAUDE.md.template` for the minimal wiring needed.

## Setup (Other LLMs)

For GPT-4, Gemini, Cursor, or any other LLM:

Use the skill content as part of your **system prompt** or **instruction file**.
The concepts are identical — only the invocation mechanism differs.

Example system prompt addition:
```
When asked to implement code changes, follow the generate-operations-config skill:
produce an ops.json file describing the changes, do NOT write code directly.
```

## Why This Matters

Without skills, you have to manually remind the AI to use ops.json every time.
With skills, the AI automatically knows its role, constraints, and output format
for every request — zero manual prompting needed.

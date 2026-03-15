# Setup Prompts

Copy-paste a prompt into your AI tool. It sets up CodeManifest and runs a verification test automatically.

## Which prompt should I use?

| Your AI Tool | Prompt File | What it does |
|---|---|---|
| Claude Code | [setup-claude-code.md](setup-claude-code.md) | Scripts + 3 skills + CLAUDE.md, runs test |
| Cursor | [setup-cursor.md](setup-cursor.md) | Scripts + `.cursor/rules/` rule, runs test |
| GitHub Copilot | [setup-copilot.md](setup-copilot.md) | Scripts + `copilot-instructions.md`, runs test |
| ChatGPT / GPT-4 | [setup-chatgpt.md](setup-chatgpt.md) | Manual setup + system prompt for ops.json |
| Any AI tool | [setup-universal.md](setup-universal.md) | Auto-detects tool, sets up accordingly |

## Already set up?

Paste [integration-test.md](integration-test.md) to run a standalone verification test.

## How it works

Each prompt is self-contained. It downloads the scripts via `curl`, creates the configuration files for your specific tool, and runs a full round-trip integration test (create ops.json, validate, dry-run, execute, verify, restore, clean up).

# Contributing to CodeManifest

Thank you for your interest in contributing to CodeManifest! This project dogfoods its own pattern — contributions use ops.json for code changes.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/CodeManifest.git
   cd CodeManifest
   ```
3. Install development dependencies:
   ```bash
   pip install pytest coverage jsonschema
   ```
4. Run the test suite to make sure everything works:
   ```bash
   python3 -m pytest tests/ -v
   ```

## Making Changes

### Using the ops.json pattern (preferred)

This repo uses its own tools for code changes:

1. Create an `ops.json` describing your changes
2. Validate: `python3 scripts/validate-config-json.py ops.json`
3. Dry-run: `python3 scripts/execute-json-ops.py ops.json --dry-run`
4. Execute: `python3 scripts/execute-json-ops.py ops.json`

### Direct edits

For documentation, tests, or new files, direct edits are fine.

## Code Style

- Python 3.9+ compatible
- No external dependencies for core scripts (standard library only)
- `jsonschema` is optional — code must work without it
- Keep functions focused and well-documented
- Add tests for new functionality

## Running Tests

```bash
# Full test suite
python3 -m pytest tests/ -v

# With coverage
coverage run -m pytest tests/ -v
coverage report --fail-under=75

# Validate all examples
python3 scripts/validate-config-json.py examples/01-simple-edit.json
python3 scripts/validate-config-json.py examples/02-multi-file-edit.json
python3 scripts/validate-config-json.py examples/03-file-operations.json
```

## Submitting Changes

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes and add tests
3. Ensure all tests pass and coverage stays above 75%
4. Push to your fork and open a Pull Request
5. Describe what your PR does and why

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include steps to reproduce for bugs
- Include Python version and OS information

## Security

If you discover a security vulnerability, please see [SECURITY.md](SECURITY.md) for responsible disclosure instructions.

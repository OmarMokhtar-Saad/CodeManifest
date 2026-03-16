# Changelog

All notable changes to CodeManifest are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [3.1.0] - 2026-03-16

### Changed
- Dry-run now fails when only partial edits apply (matches real execution semantics)
- `delete` action requires strict `True` value (rejects truthy non-booleans)
- `normalize_config()` validates legacy entries instead of raising KeyError
- Validator GUARD 19 now resolves symlinks (matches executor path confinement)
- GUARD 21 (plan name) and GUARD 23 (filename collision) are warnings, not errors
- Timestamps use UTC (ISO 8601 with timezone)

### Added
- `scripts/shared.py` — single source of truth for PROTECTED_PATTERNS and is_protected_file()
- `_validate_edits()` helper eliminates duplicated validation logic
- `--verbose` / `-v` flag on all three scripts
- `pyproject.toml` with project metadata and tool configuration
- `CHANGELOG.md`
- `examples/04-modern-code-edit.json`
- `tests/test_integration.py` — end-to-end validate/execute/restore tests
- CI: Python 3.10 in matrix, example 04 validation, restore smoke test, ruff linting

### Fixed
- Partial-edits rollback: file is now tracked for transaction rollback
- Symlink parent escape: `validate_path()` resolves full real path
- Restore backup source confinement (GUARD 12)
- `fcntl` import guarded for Windows compatibility
- `e.message` replaced with `getattr(e, 'message', str(e))`
- `UnicodeDecodeError` caught explicitly with clear message
- Broad `except Exception` narrowed in validator

## [3.0.0] - 2026-03-16

### Added
- `OperationTransaction` class for transactional rollback
- `ExecutionLock` with `fcntl` file locking
- Unified diff preview during `--dry-run`
- `CODE_OF_CONDUCT.md`

## [2.3.0] - 2026-03-16

### Added
- `validate_path()` in executor (path traversal, null bytes, symlinks)
- `PurePath.relative_to()` in restore script path validation
- `logging.basicConfig()` configuration
- `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`
- README badges, Table of Contents, Installation section

### Fixed
- Partial edits return `False` instead of silent success
- Manifest creation failure aborts execution
- `shutil.copy()` wrapped in try/except for backup safety
- Accurate byte counts using `len(content.encode('utf-8'))`
- Backup timestamp includes microseconds
- Version string unified to v2.3
- `delete` action uses `edit.get('delete')` instead of `'delete' in edit`

### Changed
- GUARD 17 (parent directory) changed from error to warning

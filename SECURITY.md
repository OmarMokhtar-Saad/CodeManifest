# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in CodeManifest, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the maintainer directly or use [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Model

CodeManifest operates on local files in the current working directory. The security model includes:

- **29 validation guards** that run before any file is touched
- **Path traversal protection** in both the validator and executor
- **Null byte rejection** in file paths and content
- **Protected file patterns** preventing deletion of critical files
- **File size limits** (2MB max) to prevent resource exhaustion
- **Operation count limits** (max 5 per config) to limit blast radius

### Important: Validator-Before-Executor Requirement

The executor (`execute-json-ops.py`) is designed to be run **after** the validator (`validate-config-json.py`). While the executor includes basic path validation and protected file checks, the full set of safety guards (max operations, file size limits, deletion reasons, ambiguous match detection) is enforced by the validator.

**Always run the validator before the executor**, especially in automated pipelines.

## Response Timeline

- Acknowledgment: within 48 hours
- Assessment: within 1 week
- Fix: as soon as possible, depending on severity

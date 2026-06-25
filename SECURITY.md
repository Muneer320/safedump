# Security Policy

## Reporting a Vulnerability

Safedump is designed to handle sensitive data (crash reports may contain
application state). If you discover a security vulnerability, please
**do not open a public issue**.

Instead, email the maintainer directly: **muneer.alam320@gmail.com**

You can expect:
- Acknowledgment within 48 hours
- Regular updates on progress
- Credit in the release notes (unless you prefer to remain anonymous)

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | ✅ Active development |
| < 0.1.0 | ❌ Pre-release only |

## Security Design

Safedump's security architecture is documented in the [Software Architecture Specification](docs/architecture.md#14-security-architecture).

Key security properties:

- **No network access** — Safedump never makes network connections
- **No pickle** — All serialization uses JSON only
- **Secret redaction** — Variable names and values are scrubbed before writing to disk
- **File permissions** — Reports saved with `0600` (owner read/write only)
- **No env var capture** — Environment variable values are never captured by default
- **`inspect.getattr_static()`** — Safe attribute access that doesn't execute descriptors

## What to Report

- Vulnerabilities that could leak secrets through crash reports
- Bypasses of the redaction system
- Path traversal in report filenames
- Any code execution path through object inspection
- Supply chain concerns in dependencies

## What NOT to Report

- Crashes caused by Safedump in your application (that's a bug — open an issue)
- Feature requests (use discussions)
- "Safedump captured too much data" when privacy tier is set high (that's configuration)

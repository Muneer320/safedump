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
| 2.1.x / current `main` | Current maintained code line |
| Older releases | Upgrade and reproduce against the current release when possible |

## Security Design

Safedump's security architecture is documented in the [Software Architecture Specification](docs/architecture.md#14-security-architecture).

Key security properties:

- **Local reports** — Capture does not upload reports or include telemetry. The optional viewer serves local browser connections; keep it on loopback.
- **No pickle** — All serialization uses JSON only
- **Secret redaction** — Variable names and values are scrubbed before writing to disk
- **File permissions** — Reports request `0600` and their directory `0700`; Windows access control follows the filesystem's ACLs.
- **No env var capture** — Environment variable values are never captured by default
- **`inspect.getattr_static()`** — Used for selected attribute inspection. Capture still runs inside the application process and is not a sandbox for hostile objects.

Redaction is not a guarantee of safe disclosure. Review every report, including exception messages, source context, paths and application-specific values. Tier 0 still includes source/context metadata. See the [privacy guide](docs/privacy.md) and [security boundaries](docs/security.md).

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

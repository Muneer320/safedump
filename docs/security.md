# Security and privacy boundaries

safedump writes exception diagnostics to the local filesystem. Capturing a report does not upload it or require an account. Reports can still contain sensitive application state: review them before moving them to a ticket, chat, shared directory or public repository.

## Redaction helps; review is still required

The sanitizer applies variable-name rules and credential-pattern matching before storage. Entropy detection is optional and disabled by default. Custom `RedactionRule` patterns and `before_capture` hooks let an application filter its own domain-specific data.

Redaction cannot recognize every secret or private value. Source context can contain literal credentials; exception messages, paths and ordinary-looking values can reveal private information. A redacted local variable does not mean its source-code literal has disappeared. Even tier 0 is not automatically safe to publish.

See [Privacy](privacy.md) for the current tier table. Tiers 2–4 add object attributes, crash-site globals and environment values respectively; increasing a tier changes the exposure. Presets override selected individual settings, as described in [Configuration](getting-started/configuration.md).

## Files and permissions

Reports use JSON, optionally compressed with gzip; the loader does not use pickle. Storage uses a temporary file and replacement rather than writing a partial final report in place. It requests owner-only file (`0600`) and directory (`0700`) modes. Windows ACLs and the destination filesystem determine effective access; POSIX mode values are not a cross-platform secrecy guarantee.

Protect the report directory, backups and exported HTML with the same care as application logs. HTML contains the captured data. Compression does not encrypt it. Use OS/storage access controls and a retention policy appropriate to the application.

## Optional local server

`safedump serve` starts a browser viewer on `127.0.0.1` by default. It accepts browser connections and exposes stored reports to clients that can reach it; it is not a remote upload service or a public authenticated dashboard. Keep it on loopback. Do not forward its port or use a shared report directory without understanding the access boundary.

Installation, package downloads and application-provided callbacks are separate from the capture library's local behavior. A custom `on_crash` callback can send data if the application implements that behavior.

## Capture is diagnostics, not isolation

The library runs inside the application process. It is not a sandbox for hostile objects, an encryption system or a collector for native core dumps. It attempts to preserve useful context while limiting expansion and handling capture failures; applications must still handle a missing report or failed destination.

## Before sharing

1. Choose the least detail needed and capture a synthetic reproduction when possible.
2. Inspect source lines, exception text, locals/globals, paths, environment and thread information.
3. Check the `redactions` records, then review the remaining values independently.
4. Share through an appropriately restricted channel and retain only what is needed.

For vulnerabilities, follow [the private reporting policy](https://github.com/Muneer320/safedump/blob/main/SECURITY.md); do not attach sensitive crash reports to public issues.

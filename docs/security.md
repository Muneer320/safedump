# Security & Privacy

Safedump is designed for **privacy-first** crash diagnostics. It
never sends data over the network and provides multiple layers of
secret redaction.

## Network Isolation

Safedump makes **zero** network calls. There is no telemetry, no
analytics, no phone-home mechanism. Crash reports are stored
exclusively on the local filesystem.

The only exception is the optional local web server (`safedump serve`),
which binds to `127.0.0.1` by default and never reaches the network.

## Secret Redaction

Safedump applies three layers of redaction before saving a report:

### 1. Variable Name Denylist

Variable names matching known secret patterns (e.g., `password`,
`token`, `api_key`, `secret`) are redacted by name. The denylist
contains 70+ common patterns.

### 2. Regex Credential Detection

Values matching credential patterns are redacted:

- AWS Access Keys (`AKIA...`)
- GitHub Personal Access Tokens (`ghp_...`)
- GitHub Fine-Grained Tokens (`github_pat_...`)
- Slack Bot Tokens (`xoxb-...`)
- Slack Webhook URLs
- JWT Tokens (Base64-encoded JSON Web Tokens)
- RSA Private Keys
- SSH Private Keys
- Generic credential patterns

### 3. Entropy Detection (opt-in)

When enabled, high-entropy strings (random-looking values like API
keys that don't match known patterns) are redacted based on Shannon
entropy. This detects novel secrets that the denylist and regex
patterns miss.

## File Permissions

- Report files: `0o600` (owner read/write only)
- Output directory: `0o700` (owner access only)

## Redaction Audit Trail

Every redaction is recorded in the report's `redactions` array:

```json
{
    "redactions": [
        {
            "location": "frames[0].locals.password",
            "reason": "matched pattern: ghp_[0-9a-zA-Z]{36}",
            "rule": "secret_pattern",
            "timestamp": "2026-07-30T12:00:00"
        }
    ]
}
```

This makes it clear what was redacted and why.

## Privacy Tiers

| Tier | Description | Captures |
|---|---|---|
| 0 | Minimal | Exception type, message, crash site |
| 1 | Default | + local variable values (short) |
| 2 | Verbose | + longer values, more collection items |
| 3 | Debug | + environment details |
| 4 | Full | + env variable names, argv |

## Best Practices

1. Always review crash reports before sharing publicly.
2. Use `configure(preset="production")` in production environments.
3. Enable entropy detection for defense-in-depth:
   `configure(enable_entropy_detection=True)`
4. Consider enabling compression for storage efficiency:
   `configure(compress=True)`

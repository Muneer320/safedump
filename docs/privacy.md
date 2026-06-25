# Privacy Guide

Safedump is designed to capture debugging context without compromising privacy. This guide explains what's captured at each tier and how to configure Safedump for your environment.

## Privacy Tiers

| Tier | Name | Captures | Safe to Share? |
|---|---|---|---|
| **0** | Minimal | Stack trace + exception info only | ✅ Yes |
| **1** | Standard (default) | Tier 0 + local variables with **mandatory redaction** | ✅ After visual review |
| **2** | Verbose | Tier 1 + instance attributes, function arguments | ⚠️ Review before sharing |
| **3** | Full | Tier 2 + globals (redacted), env var names | ⚠️ Review carefully |
| **4** | Debug | Everything including env var values | ❌ Never share without manual audit |

## What Gets Redacted (Tier 1+)

### Variable Name Denylist
Variables whose names contain these patterns are redacted:
`password`, `secret`, `token`, `key`, `api_key`, `credential`, `auth`,
`private_key`, `access_token`, `session_key`, `database_url`, and more.

Matching uses tiered logic: ≤3-char patterns match exactly, 4-char patterns match word boundaries, ≥5-char patterns match substrings. This prevents false positives like `keyboard` matching `key`.

### Credential Pattern Detection
String values matching known credential formats are redacted:
- AWS Access Keys (`AKIA...`)
- GitHub Tokens (`ghp_...`)
- Stripe Keys (`sk_live_...`)
- JWT Tokens (`eyJ...`)
- Generic API keys

### Custom Redaction Rules
Add domain-specific rules:
```python
safedump.configure(redaction_rules=[
    safedump.RedactionRule(r"PROPRIETARY-\d+", "[REDACTED]"),
    safedump.RedactionRule(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN REDACTED]", "values"),
])
```

## What Is NEVER Captured (by default)

- Environment variable **values** (names only, at Tier 3+)
- Command-line arguments (opt-in via `include_argv=True`)
- File contents
- Network traffic
- Keystrokes

## `before_capture` Hook

For maximum control, use the `before_capture` hook to scrub data before Safedump processes it:

```python
def my_scrubber(report):
    # Remove sensitive frames or values
    return report

safedump.configure(before_capture=my_scrubber)
```

## Report Security

- Files saved with `0600` permissions (owner read/write only)
- Directory saved with `0700` permissions
- No network access — reports never leave your machine
- Redaction audit trail in every report records what was redacted and why

## Sharing Guidance

1. **Always run `safedump view` first** — visually inspect the report
2. **Check the redactions section** — see what was automatically scrubbed
3. **Use Tier 0 for public sharing** — stack traces contain no variable data
4. **For bug reports** — Tier 1 reports are generally safe after visual review
5. **Never share Tier 4 reports** — they may contain environment variable values with credentials

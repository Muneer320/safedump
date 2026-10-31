# Privacy Guide

Safedump is designed to capture debugging context without compromising privacy. This guide explains what's captured at each tier and how to configure Safedump for your environment.

## Privacy Tiers

| Tier | Name | Captures | Safe to Share? |
|---|---|---|---|
| **0** | Minimal | Exception chain, stack/source context and basic runtime/path metadata. No variable values, no env var names, no argv | Review source, messages and paths |
| **1** | Standard (default) | Tier 0 + local variables (lists, dicts and strings as values; other objects as a short `repr`), env var **names** if `include_env_names`, argv if `include_argv`. Redaction is applied | Review all remaining values |
| **2** | Verbose | Tier 1 + objects expanded into their attributes (dataclass fields / instance `__dict__`), redacted the same way | ⚠️ Review before sharing |
| **3** | Full | Tier 2 + the module globals of the crash-site frame (modules, functions and classes are skipped), redacted | ⚠️ Review carefully |
| **4** | Debug | Tier 3 + environment variable **values**. Values whose name is on the denylist are replaced, and values matching secret patterns are scrubbed | ❌ Never share without manual audit |

Values are expanded up to `max_depth` levels and `max_collection_items` entries, and strings are cut to `max_string_length` characters. The cut happens **after** redaction, so a secret is never half-kept at the boundary.

## What Gets Redacted (Tier 1+)

### Variable Name Denylist
Variables whose names contain these patterns are redacted:
`password`, `secret`, `token`, `key`, `api_key`, `credential`, `auth`,
`private_key`, `access_token`, `session_key`, `database_url`, and more.

Matching uses tiered logic: ≤3-char patterns match exactly, 4-char patterns match word boundaries, ≥5-char patterns match substrings. This prevents false positives like `keyboard` matching `key`.

### Credential Pattern Detection
Credentials found anywhere in a string are replaced with `[REDACTED]`. The rest of the string is kept, so an exception message stays readable. The search covers local values, nested inside lists and dicts, exception messages, argv and env var values. Known formats:
- AWS Access Keys (`AKIA...`)
- GitHub Tokens (`ghp_...`)
- Stripe Keys (`sk_live_...`)
- JWT Tokens (`eyJ...`)
- Generic API keys

### Custom Redaction Rules
Add domain-specific rules:
```python
safedump.configure(
    redaction_rules=[
        safedump.RedactionRule(r"PROPRIETARY-\d+", "[REDACTED]"),
        safedump.RedactionRule(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN REDACTED]", "values"),
    ]
)
```

## What Is NEVER Captured (by default)

- Environment variable **values** (only at Tier 4)
- Command-line arguments (opt-in via `include_argv=True`)
- Arbitrary file contents (source lines around captured frames **are** included)
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

- Files request `0600` permissions and the directory requests `0700`; Windows effective access depends on filesystem ACLs
- Capture does not upload reports; exports, shared folders, backups and user callbacks can move their data
- Redaction audit trail in every report records what was redacted and why

## Sharing Guidance

1. **Always run `safedump view` first** — visually inspect the report
2. **Check the redactions section** — see what was automatically scrubbed
3. **Minimize captured detail** — tier 0 omits variable values but still contains source, messages and paths
4. **For bug reports** — review every remaining value and prefer a synthetic reproduction
5. **Never share Tier 4 reports** — they may contain environment variable values with credentials

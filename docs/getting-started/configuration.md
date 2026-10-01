# Configuration

Call `safedump.configure()` **before** `safedump.install()`.
All parameters are keyword-only.

```python
import safedump

safedump.configure(
    preset="production",
    output_dir="./crashes",
    privacy_tier=1,
)
safedump.install()
```

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `preset` | `None` | Quick configuration preset |
| `output_dir` | `$SAFEDUMP_DIR` or `~/.safedump` | Directory for crash reports |
| `privacy_tier` | `1` | Capture detail level (0-4), see [Privacy](../privacy.md) |
| `include_env_names` | `True` | Include env var names |
| `include_argv` | `False` | Include command-line args |
| `max_string_length` | `10000` | Max chars per captured string |
| `max_collection_items` | `100` | Max items from collections |
| `max_depth` | `5` | How many levels of nested values are expanded |
| `redaction_rules` | `[]` | Custom redaction patterns |
| `before_capture` | `None` | Pre-processing callback |
| `enable_entropy_detection` | `False` | Entropy-based secret detection |
| `entropy_threshold` | `4.5` | Entropy threshold (bits/char) |
| `compress` | `False` | Gzip compress crash reports |
| `on_crash` | `None` | Post-capture callback |

## Presets

A preset sets `privacy_tier`, `include_env_names`, `include_argv` and `max_depth`, overriding those arguments if you pass them too.

| Preset | Tier | Env var names | Argv | Depth |
|---|---|---|---|---|
| `production` | 1 | No | No | 5 |
| `development` | 2 | Yes | No | 10 |
| `debug` | 4 | Yes | Yes | 50 |
| `minimal` | 0 | No | No | 3 |

## Report directory

Reports go to `output_dir`. If you don't set it, Safedump uses the `SAFEDUMP_DIR`
environment variable, then `~/.safedump`. The CLI follows the same rule, and
also accepts `--dir`:

```bash
export SAFEDUMP_DIR=./crashes
safedump list            # reads ./crashes
safedump --dir ./other list
```

## Examples

### Production configuration

```python
safedump.configure(
    preset="production",
    compress=True,
    enable_entropy_detection=True,
)
```

### Custom output directory with notification

```python
def notify(path):
    import subprocess

    subprocess.Popen(["notify-send", f"Crash saved: {path}"])


safedump.configure(
    output_dir="/var/log/crashes",
    on_crash=notify,
)
```

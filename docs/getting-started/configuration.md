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
| `output_dir` | `~/.safedump` | Directory for crash reports |
| `privacy_tier` | `1` | Capture detail level (0-4) |
| `include_env_names` | `True` | Include env var names |
| `include_argv` | `False` | Include command-line args |
| `max_string_length` | `10000` | Max chars per captured string |
| `max_collection_items` | `100` | Max items from collections |
| `max_depth` | `5` | Max depth for serialization |
| `redaction_rules` | `[]` | Custom redaction patterns |
| `before_capture` | `None` | Pre-processing callback |
| `enable_entropy_detection` | `False` | Entropy-based secret detection |
| `entropy_threshold` | `4.5` | Entropy threshold (bits/char) |
| `compress` | `False` | Gzip compress crash reports |
| `on_crash` | `None` | Post-capture callback |

## Presets

| Preset | Tier | Env Vars | Argv | Depth |
|---|---|---|---|---|
| `production` | 1 | Yes | No | 5 |
| `development` | 2 | Yes | Yes | 10 |
| `debug` | 4 | Yes | Yes | 20 |
| `minimal` | 0 | No | No | 3 |

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

# Safedump + Flask

## Installation

```bash
pip install safedump[view]
```

No Flask-specific dependencies required. Works with any Flask version.

## Basic setup

Register a custom error handler that captures crash context before returning the error response:

```python
import safedump
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

safedump.configure(preset="production", output_dir="./crashes")

app = Flask(__name__)


@app.errorhandler(Exception)
def handle_unhandled(exc):
    """Capture crash context for all unhandled exceptions."""
    if isinstance(exc, HTTPException):
        return jsonify(error=exc.description), exc.code

    report_path = safedump.capture_exception(exc)
    app.logger.error("Crash report saved: %s", report_path)

    return jsonify(error="Internal server error", crash_id=report_path.stem), 500
```

For broader coverage (exceptions outside request handlers), add WSGI middleware:

```python
class SafedumpMiddleware:
    """WSGI middleware: captures exceptions that escape the app."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except Exception:
            safedump.capture_exception()
            raise


app.wsgi_app = SafedumpMiddleware(app.wsgi_app)
```

Combine both: middleware catches framework-level errors, error handler produces user-friendly responses.

## Recommended configuration for production

```python
import safedump

safedump.configure(
    preset="production",  # privacy tier 1, no env capture, no argv
    output_dir="/var/log/safedump",
    max_depth=5,
)
safedump.install()
```

- **`preset="production"`**: disables environment variable values and CLI argument capture.
- **Persist `output_dir`**: use a mounted volume so reports survive container restarts.
- **Rotate reports**: `safedump clean --older-than 30` via cron.
- **Never use privacy tier 4 in production**: it captures raw environment variable values.

### Attach request context

Enrich crash reports with request metadata:

```python
from flask import request, g


def add_request_context(report):
    try:
        report.metadata["request"] = {
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
        }
        if hasattr(g, "user_id"):
            report.metadata["user_id"] = g.user_id
    except RuntimeError:
        pass  # outside request context
    return report


safedump.configure(preset="production", before_capture=add_request_context)
```

## Complete working example

```python
# app.py
import safedump
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


def _add_request(report):
    try:
        report.metadata["request"] = {"method": request.method, "path": request.path}
    except RuntimeError:
        pass
    return report


safedump.configure(
    preset="production",
    output_dir="./crashes",
    before_capture=_add_request,
)
safedump.install()

app = Flask(__name__)


@app.errorhandler(Exception)
def handle_unhandled(exc):
    if isinstance(exc, HTTPException):
        return jsonify(error=exc.description), exc.code

    path = safedump.capture_exception(exc)
    app.logger.error("Crash report: %s", path)
    return jsonify(error="Internal server error"), 500


@app.route("/api/data")
def get_data():
    return jsonify([1, 2, 3])


if __name__ == "__main__":
    app.run()
```

## Testing instructions

Add a debug crash endpoint:

```python
@app.route("/__debug__/crash")
def trigger_crash():
    x = None
    return x.upper()  # AttributeError
```

```bash
flask run
curl http://localhost:5000/__debug__/crash
safedump view
```

Remove the debug endpoint before deploying to production.

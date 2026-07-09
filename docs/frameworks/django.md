# Safedump + Django

## Installation

```bash
pip install safedump[view]
```

Compatible with Django 3.2, 4.x, and 5.x.

## Basic setup

### Step 1: Middleware class

Create `middleware.py` in your Django project:

```python
# your_project/middleware.py
import safedump


class SafedumpMiddleware:
    """Captures unhandled exceptions and attaches crash IDs to requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        report_path = safedump.capture_exception(exception)
        request.safedump_crash_id = report_path.stem if report_path else None
        return None  # Let Django's default error handling continue
```

### Step 2: Register middleware

In `settings.py`, place it first so it wraps the entire request lifecycle:

```python
MIDDLEWARE = [
    "your_project.middleware.SafedumpMiddleware",
    # ...
]
```

### Step 3: Configure Safedump

In `settings.py` or your app config:

```python
import safedump
import os

safedump.configure(
    preset="production",
    output_dir=os.path.join(os.path.dirname(__file__), "..", "crashes"),
)
safedump.install()
```

### Step 4: Custom 500 handler (optional)

In `urls.py`, override the default error view to return a crash ID:

```python
from django.http import JsonResponse


def handler500(request):
    crash_id = getattr(request, "safedump_crash_id", None)
    return JsonResponse({"error": "Internal server error", "crash_id": crash_id}, status=500)
```

## Recommended configuration for production

```python
import safedump
import os

safedump.configure(
    preset="production",
    output_dir=os.environ.get("SAFEDUMP_DIR", "/var/log/safedump"),
    max_depth=5,
)
safedump.install()
```

- **Use `preset="production"`**: privacy tier 1, environment variable values excluded.
- **Absolute `output_dir`**: use a path outside the project root. Mount a volume in Docker.
- **Rotate reports**: `safedump clean --older-than 30` via cron or management command.
- **Environment variable for `output_dir`**: different paths per environment.

### Logging integration

Wire Safedump into Django's logging framework:

```python
import logging

logger = logging.getLogger("safedump")


class SafedumpLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        report_path = safedump.capture_exception(exception)
        logger.error(
            "Unhandled exception captured. Crash report: %s",
            report_path,
            exc_info=True,
            extra={"crash_report": str(report_path), "path": request.path},
        )
        return None
```

### AppConfig startup

Initialize Safedump once at startup via `AppConfig.ready()`:

```python
# your_project/apps.py
from django.apps import AppConfig


class YourProjectConfig(AppConfig):
    name = "your_project"

    def ready(self):
        import safedump
        import os

        safedump.configure(
            preset="production",
            output_dir=os.environ.get("SAFEDUMP_DIR", "/var/log/safedump"),
        )
        safedump.install()
```

## Complete working example

```
your_project/
├── middleware.py       # SafedumpMiddleware
├── apps.py             # AppConfig with safedump.init
├── settings.py         # MIDDLEWARE registration
├── urls.py             # handler500, debug crash endpoint
└── management/
    └── commands/
        └── cleancrashes.py  # Report rotation command
```

**`middleware.py`**:

```python
import safedump


class SafedumpMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        report_path = safedump.capture_exception(exception)
        request.safedump_crash_id = report_path.stem if report_path else None
        return None
```

**`management/commands/cleancrashes.py`**:

```python
from django.core.management.base import BaseCommand
import subprocess


class Command(BaseCommand):
    help = "Delete Safedump crash reports older than N days."

    def add_arguments(self, parser):
        parser.add_argument("--older-than", type=int, default=30)

    def handle(self, *args, **options):
        days = options["older_than"]
        subprocess.run(["safedump", "clean", "--older-than", str(days)], check=True)
        self.stdout.write(self.style.SUCCESS(f"Cleaned reports older than {days} days."))
```

## Testing instructions

Add a crash endpoint:

```python
# urls.py
from django.urls import path
from django.http import HttpResponse


def trigger_crash(request):
    x = None
    return HttpResponse(x.upper())  # AttributeError


urlpatterns = [
    path("__debug__/crash/", trigger_crash),
]
```

```bash
python manage.py runserver
curl http://localhost:8000/__debug__/crash/
safedump view
```

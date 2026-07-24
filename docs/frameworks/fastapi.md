# Safedump + FastAPI

## Installation

```bash
pip install safedump[view] fastapi uvicorn
```

## Basic setup

Register a FastAPI exception handler that captures crash context before returning an error response:

```python
import safedump
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

safedump.configure(preset="production", output_dir="./crashes")

app = FastAPI()


@app.exception_handler(Exception)
async def safedump_exception_handler(request: Request, exc: Exception):
    report_path = safedump.capture_exception(exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "crash_id": report_path.stem if report_path else None,
        },
    )
```

For broader coverage (startup failures, middleware errors), add ASGI middleware:

```python
from starlette.middleware.base import BaseHTTPMiddleware


class SafedumpMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except Exception:
            safedump.capture_exception()
            raise


app.add_middleware(SafedumpMiddleware)
```

### Lifespan integration

Install Safedump at startup and clean up at shutdown:

```python
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    safedump.configure(preset="production", output_dir="./crashes")
    safedump.install()
    yield
    safedump.uninstall()


app = FastAPI(lifespan=lifespan)
```

### Background task protection

FastAPI background tasks run after the response is sent: exceptions inside them are not caught by exception handlers:

```python
from fastapi import BackgroundTasks


def risky_job():
    try:
        dangerous_operation()
    except Exception:
        safedump.capture_exception()


@app.post("/process")
async def process(background_tasks: BackgroundTasks):
    background_tasks.add_task(risky_job)
    return {"status": "accepted"}
```

## Recommended configuration for production

```python
safedump.configure(
    preset="production",
    output_dir="/var/log/safedump",
    max_depth=5,
)
safedump.install()
```

- **`preset="production"`**: privacy tier 1, environment variable values excluded.
- **Persist `output_dir`**: mount a volume at `/var/log/safedump` in Docker/Kubernetes.
- **Rotate periodically**: `safedump clean --older-than 30` via cron.
- **Crash ID in responses**: include report filename in 500 responses so users can reference it.

## Complete working example

```python
# app.py
import safedump
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    safedump.configure(preset="production", output_dir="./crashes")
    safedump.install()
    yield
    safedump.uninstall()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def safedump_exception_handler(request: Request, exc: Exception):
    report_path = safedump.capture_exception(exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "crash_id": report_path.stem if report_path else None,
        },
    )


@app.get("/api/data")
async def get_data():
    return {"data": [1, 2, 3]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
```

## Testing instructions

```python
@app.get("/__debug__/crash")
async def trigger_crash():
    x = None
    return x.upper()
```

```bash
uvicorn app:app --reload
curl http://localhost:8000/__debug__/crash
safedump view
```

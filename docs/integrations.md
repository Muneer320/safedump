# Integrations

Safedump provides optional integrations for developer tools.
Each integration is a standalone module in
`safedump.integrations.*` -- import only what you need.

## pytest

Automatically capture crash reports when tests fail.

```python
# conftest.py
pytest_plugins = ["safedump.integrations.pytest_plugin"]
```

Every test failure now produces a structured crash report alongside
the normal pytest output.

## Click / Typer

Wrap CLI commands to capture crashes on unhandled exceptions.

```python
import click
from safedump.integrations.click_plugin import wrap_click


@click.command()
@wrap_click()
def my_command(): ...
```

The exception is captured and then re-raised, so Click's normal error
handling still works.

### With Typer

```python
import typer
from safedump.integrations.click_plugin import wrap_click

app = typer.Typer()


@app.command()
@wrap_click()
def my_command(): ...
```

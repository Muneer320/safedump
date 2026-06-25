"""Example: Loading crash reports in CI scripts."""

import safedump

# Load and analyze a crash report programmatically
path = "crash-2026-06-25-ZeroDivisionError-a1b2c3.json"
try:
    report = safedump.load_report(path)
    exc_type = report["exception"]["type"]
    exc_msg = report["exception"]["message"]
    frames = report["frames"]

    print(f"Crash: {exc_type}: {exc_msg}")
    print(f"Stack depth: {len(frames)} frames")

    # Check for specific conditions
    if exc_type == "ZeroDivisionError":
        for frame in frames:
            for name, var in frame.get("locals", {}).items():
                if "0" in str(var.get("value", "")):
                    print(f"  Possible culprit: {name} = {var['value']}")

except FileNotFoundError:
    print(f"Report not found: {path}")
except ValueError:
    print(f"Invalid report: {path}")

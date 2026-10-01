"""
Example: basic Safedump usage.

    python docs/examples/basic_usage.py

Writes two crash reports to ./crashes, then shows how to read them back.
"""

import safedump


def divide(total, parts):
    api_token = "ghp_" + "x" * 36  # noqa: F841 -- redacted in the report, never written
    per_part = total / parts  # raises ZeroDivisionError when parts == 0
    return per_part


def main():
    # Configure first, then install the global hooks.
    safedump.configure(output_dir="./crashes", privacy_tier=1)
    safedump.install()

    # Check that reports can be written.
    print("Self-test report:", safedump.test())

    # Manual capture inside an except block, the error is handled.
    try:
        divide(10, 0)
    except ZeroDivisionError:
        path = safedump.capture_exception()
        report = safedump.load_report(path)
        crash = report["frames"][-1]
        print(
            "Captured:", report["exception"]["type"], "at", f"{crash['function']}:{crash['line']}"
        )
        print("Locals:", {name: var["value"] for name, var in crash["locals"].items()})

    safedump.uninstall()
    print("Inspect the reports with: safedump --dir ./crashes list")


if __name__ == "__main__":
    main()

"""Example: Manual crash capture in try/except blocks."""

import safedump

safedump.configure(output_dir="./crashes")


def process_data(items):
    return sum(items) / len(items)


try:
    result = process_data([])
except ZeroDivisionError:
    path = safedump.capture_exception()
    print(f"Crash captured: {path}")
    raise

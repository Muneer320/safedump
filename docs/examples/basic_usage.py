"""
Example: Basic Safedump usage.

This is a placeholder demonstrating the intended API.
Run after Safedump is implemented:
    python docs/examples/basic_usage.py
"""


def main():
    import safedump

    # Install crash hooks — one line
    safedump.install()
    print("Safedump installed. Crash reports will be saved to ~/.safedump/")

    # Configure (optional)
    safedump.configure(
        privacy_tier=1,  # Locals + redaction (default)
        output_dir="./crashes",
    )
    print("Configuration updated.")

    # Self-test
    try:
        safedump.test()
        print("Self-test passed! Safedump is working correctly.")
    except NotImplementedError:
        print("Safedump is not yet implemented. This is a development build.")

    # Manual capture (for try/except blocks)
    try:
        _ = 1 / 0  # This will crash when uncommented in production
    except ZeroDivisionError:
        # path = safedump.capture_exception()
        # print(f"Crash captured: {path}")
        print("Manual capture would happen here (not yet implemented).")
        pass

    # Uninstall when done
    safedump.uninstall()
    print("Safedump uninstalled.")


if __name__ == "__main__":
    main()

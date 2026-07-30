# Frequently Asked Questions

**Does Safedump send data anywhere?**

No. Safedump is completely offline. It never makes network
connections. Crash reports are stored locally on your filesystem.

**Is it safe to share crash reports?**

Yes (after review). By default, Safedump redacts variable names like
`password`, `token`, and `secret`, and detects credential patterns.
The report includes a redaction audit trail. Still, always review
before sharing publicly.

**What's the performance overhead?**

Zero during normal execution. Safedump only runs when an unhandled
exception occurs. Crash capture takes approximately 4ms for a typical
20-frame traceback.

**What Python versions are supported?**

3.9 through 3.13. Tested on all versions in CI on both Linux and
Windows.

**Can I use this in production?**

Yes. Use `configure(preset="production")` (privacy tier 1, no env
capture, no argv). Safedump is designed to fail gracefully -- if the
handler itself crashes, the original traceback is always preserved.

**How do I capture a crash without installing global hooks?**

Use `safedump.watch()` for scoped monitoring, or call
`safedump.capture_exception()` inside `except` blocks.

**Can I customize what gets redacted?**

Yes. Use `RedactionRule` for custom regex patterns, and configure
the privacy tier to control capture detail.

**Does Safedump support Windows?**

Yes. Windows 11 is tested in CI. Crash reports fall back to the
system temp directory (via `tempfile.gettempdir()`) instead of
hardcoded `/tmp`.

**How do I view crash reports from another machine?**

Copy the `.safedump.json` file to your machine and run
`safedump view <path>` or `safedump view --html <path>` to generate
a self-contained HTML file.

**What happens if Safedump itself crashes during capture?**

The original Python traceback is always preserved. A Safedump
internal error message is printed to stderr, followed by the
original traceback. Your application's crash information is never
lost.

**How do compressed reports work?**

When `compress=True` is configured, reports are saved as
`.safedump.json.gz` files. They are transparently decompressed when
read via `load_report()`. All CLI commands handle both formats.

**Does Safedump have a plugin system?**

The `register_serializer()` function allows custom type serialization.
A full plugin system via `importlib.metadata` entry points is planned
for a future release.

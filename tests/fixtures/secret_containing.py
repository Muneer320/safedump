import safedump
safedump.configure(output_dir='CRASH_DIR_PLACEHOLDER')
safedump.install()
password = "my-secret-password-123"
api_key = "sk-abcdefghijklmnopqrstuvwx"
# one of these will be redacted
x = 42
name = "Alice"
raise RuntimeError("testing secrets")
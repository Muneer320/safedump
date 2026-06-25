import safedump
safedump.configure(output_dir='CRASH_DIR_PLACEHOLDER', max_depth=10)
safedump.install()
def recurse(n):
    if n <= 0:
        1 / 0
    return recurse(n - 1)
recurse(100)
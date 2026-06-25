import safedump
safedump.configure(output_dir='CRASH_DIR_PLACEHOLDER')
safedump.install()
# Create lots of local variables
for i in range(150):
    exec(f"var_{i} = {i}")
# This should work but some variables may be truncated
raise ValueError("many locals test")
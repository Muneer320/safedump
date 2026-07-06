import safedump

safedump.configure(output_dir='CRASH_DIR_PLACEHOLDER')
safedump.install()
raise KeyboardInterrupt
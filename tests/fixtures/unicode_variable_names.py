import safedump

safedump.configure(output_dir='CRASH_DIR_PLACEHOLDER')
safedump.install()
café = "espresso"
naïve_π = 3.14159
raise RuntimeError("testing unicode variable names")
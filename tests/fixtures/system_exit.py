# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT


import sys

import safedump

safedump.configure(output_dir='CRASH_DIR_PLACEHOLDER')
safedump.install()
sys.exit(3)
# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT


import safedump
safedump.configure(output_dir='CRASH_DIR_PLACEHOLDER')
safedump.install()
try:
    1 / 0
except ZeroDivisionError:
    raise ValueError("wrapping error") from None
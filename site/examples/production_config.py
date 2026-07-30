"""Example: Production-safe configuration."""

import safedump

safedump.configure(preset="production")
safedump.install()

# Production preset sets:
#   privacy_tier=1 (locals + mandatory redaction)
#   include_env_names=False
#   include_argv=False
#   max_depth=5

# Your production application here

"""Example: Custom redaction rules for domain-specific secrets."""

import safedump

safedump.configure(
    redaction_rules=[
        safedump.RedactionRule(r"PROPRIETARY-\d+", "[REDACTED]"),
        safedump.RedactionRule(r"customer_\w+", "[CUSTOMER]", "names"),
    ],
    privacy_tier=2,
)
safedump.install()

# Any variable named customer_xxx will be redacted
customer_id = "CUST-12345"
api_key = "PROPRIETARY-9876"
raise ValueError("example crash with proprietary data")

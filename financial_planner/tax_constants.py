"""Tax policy constants for calculations."""

# 2026 tax brackets (CAD). Source: user-provided 2026 bracket tables.
ONTARIO_TAX_BRACKETS = (
    (53891, 0.0505),
    (107785, 0.0915),
    (150000, 0.1116),
    (220000, 0.1216),
    (None, 0.1316),
)

CANADA_TAX_BRACKETS = (
    (58523, 0.14),
    (117045, 0.205),
    (181440, 0.26),
    (258482, 0.29),
    (None, 0.33),
)

# Investment tax policy defaults.
CAPITAL_GAINS_INCLUSION_RATE = 0.5
TFSA_ANNUAL_CONTRIBUTION_LIMIT = 7000.0
RRSP_ANNUAL_CONTRIBUTION_LIMIT = 33810.0
RRSP_CONTRIBUTION_RATE = 0.18

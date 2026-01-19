# Tax Calculation

The tax calculator uses 2026 Canada federal and Ontario provincial tax
brackets. The bracket values live in
`financial_planner/tax_constants.py` and were provided in the 2026
bracket tables from the project request. The associated unit tests live in
`financial_planner/tax_calculator_tests.py`.

If bracket values change in future years, update the constants in
`financial_planner/tax_constants.py` and refresh the expected values in
`financial_planner/tax_calculator_tests.py`. The calculator also supports
inflation-adjusted brackets by passing an `inflation_adjustment` multiplier
to the tax helper functions.

Investment tax policy defaults (for example, capital gains inclusion rates
and default contribution limits) are also defined in
`financial_planner/tax_constants.py`.

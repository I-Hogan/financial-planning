# Tax Calculation

The tax calculator uses 2026 Canada federal and Ontario provincial tax
brackets. The bracket values are captured in
`financial_planner/tax_calculator.py` and were provided in the 2026
bracket tables from the project request. The associated unit tests live in
`financial_planner/tax_calculator_tests.py`.

If bracket values change in future years, update the constants in
`financial_planner/tax_calculator.py` and refresh the expected values in
`tex_calculator_tests.py`.

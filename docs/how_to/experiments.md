# Running Experiments

The experiment scripts live in `financial_planner/experiments/` and are meant
for quick scenario exploration outside of the web app.

To run the investment growth experiment:

```bash
python -m financial_planner.experiments.investment_growth
```

Edit `financial_planner/experiments/investment_growth_config.py` to adjust
assumptions. If you want local-only overrides, create or edit
`financial_planner/experiments/investment_growth_config_personal.py`; the
experiment will use the personal config if it exists and fall back to defaults
for any missing values. Use `INFLATION_RATE` to index annual income, spending,
contribution limits, and tax brackets; the output is rendered as a formatted
table in year-0 dollars.
Set `LIQUIDATION_YEARS` to control how many years of withdrawals are used when
estimating the after-tax value of investment balances.

The experiment now builds a timeline (`financial_planner/timeline.py`) with
age buckets between `START_AGE` and `END_AGE`. Annual cash flow settings
(income, spending, contribution policy) are modeled as events resolved at the
start of each year, while initial balances are applied as a start-age event.

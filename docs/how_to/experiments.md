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
experiment will use the personal config if it exists. The output is rendered
as a formatted table.

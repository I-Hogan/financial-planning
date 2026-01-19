"""Tests for the investment growth experiment."""

# pylint: disable=protected-access

import pytest

from financial_planner.experiments import investment_growth


def _parse_table_rows(output: str):
    rows = []
    for line in output.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0].isdigit():
            rows.append(cells)
    return rows


def _set_config(monkeypatch, **overrides):
    for key, value in overrides.items():
        monkeypatch.setattr(investment_growth.config, key, value, raising=False)


def test_inflation_factor_uses_config_rate(monkeypatch):
    """Inflation factor should compound based on the configured rate."""
    _set_config(monkeypatch, INFLATION_RATE=0.05)

    assert investment_growth._inflation_factor(0) == pytest.approx(1.0)
    assert investment_growth._inflation_factor(2) == pytest.approx(1.1025)


def test_deflate_to_year_zero():
    """Deflation should convert nominal amounts to year-zero dollars."""
    assert investment_growth._deflate_to_year_zero(110.0, 1.1) == pytest.approx(100.0)


def test_experiment_outputs_year_zero_dollars(monkeypatch, capsys):
    """Experiment output should deflate values back to year-zero dollars."""
    _set_config(
        monkeypatch,
        YEARS=2,
        INFLATION_RATE=0.1,
        ANNUAL_INCOME=0.0,
        ANNUAL_INVESTMENT_CONTRIBUTION=0.0,
        ANNUAL_SPENDING=0.0,
        INITIAL_FREE_CASH=100.0,
        INITIAL_TFSA_BALANCE=0.0,
        INITIAL_RRSP_BALANCE=0.0,
        INITIAL_UNREGISTERED_BALANCE=0.0,
        INITIAL_UNREGISTERED_COST_BASIS=0.0,
        INITIAL_TFSA_ROOM=0.0,
        INITIAL_RRSP_ROOM=0.0,
        GLOBAL_EQUITY_GROWTH_RATE=0.0,
        GLOBAL_EQUITY_INCOME_RATE=0.0,
        ACCOUNT_ORDER=("tfsa", "rrsp", "unregistered"),
    )

    investment_growth.run_experiment()

    output = capsys.readouterr().out
    rows = _parse_table_rows(output)
    year1 = next(row for row in rows if row[0] == "1")
    year2 = next(row for row in rows if row[0] == "2")

    assert year1[2] == "$100.00"
    assert year2[2] == "$90.91"


def test_net_worth_invariant_without_tax_or_returns(monkeypatch):
    """Net worth should not depend on account order without tax or returns."""
    _set_config(
        monkeypatch,
        YEARS=1,
        INFLATION_RATE=0.0,
        ANNUAL_INCOME=0.0,
        ANNUAL_INVESTMENT_CONTRIBUTION=1000.0,
        ANNUAL_SPENDING=0.0,
        INITIAL_FREE_CASH=1000.0,
        INITIAL_TFSA_BALANCE=0.0,
        INITIAL_RRSP_BALANCE=0.0,
        INITIAL_UNREGISTERED_BALANCE=0.0,
        INITIAL_UNREGISTERED_COST_BASIS=0.0,
        INITIAL_TFSA_ROOM=100_000.0,
        INITIAL_RRSP_ROOM=100_000.0,
        GLOBAL_EQUITY_GROWTH_RATE=0.0,
        GLOBAL_EQUITY_INCOME_RATE=0.0,
    )

    def _simulate(order):
        investments = investment_growth._build_investments()
        free_cash = investment_growth.config.INITIAL_FREE_CASH
        for year in range(1, investment_growth.config.YEARS + 1):
            year_index = year - 1
            inflation_factor = investment_growth._inflation_factor(year_index)
            next_year_factor = investment_growth._inflation_factor(year_index + 1)
            annual_income = investment_growth._round_money(
                investment_growth.config.ANNUAL_INCOME * inflation_factor
            )
            annual_contribution = investment_growth._round_money(
                investment_growth.config.ANNUAL_INVESTMENT_CONTRIBUTION * inflation_factor
            )
            annual_spending = investment_growth._round_money(
                investment_growth.config.ANNUAL_SPENDING * inflation_factor
            )

            free_cash = investment_growth._round_money(free_cash + annual_income)
            old_order = investment_growth.config.ACCOUNT_ORDER
            investment_growth.config.ACCOUNT_ORDER = order
            try:
                free_cash = investment_growth._apply_contributions(
                    investments, free_cash, annual_contribution
                )
            finally:
                investment_growth.config.ACCOUNT_ORDER = old_order
            free_cash = investment_growth._round_money(free_cash - annual_spending)

            result = investments.increment_year(
                annual_income=annual_income,
                inflation_adjustment=inflation_factor,
                next_year_inflation_adjustment=next_year_factor,
            )
            free_cash = investment_growth._round_money(free_cash - result.tax_summary.tax_owed)

        total_investments = investments.total_value(inflation_adjustment=1.0)
        return investment_growth._round_money(free_cash + total_investments)

    tfsa_net_worth = _simulate(("tfsa",))
    unregistered_net_worth = _simulate(("unregistered",))

    assert tfsa_net_worth == pytest.approx(unregistered_net_worth)

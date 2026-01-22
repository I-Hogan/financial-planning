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
        START_AGE=30,
        END_AGE=31,
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
    age1 = next(row for row in rows if row[0] == "30")
    age2 = next(row for row in rows if row[0] == "31")

    assert age1[2] == "$100.00"
    assert age2[2] == "$90.91"


def test_net_worth_invariant_without_tax_or_returns(monkeypatch):
    """Net worth should not depend on account order without tax or returns."""
    _set_config(
        monkeypatch,
        START_AGE=30,
        END_AGE=30,
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
        _set_config(monkeypatch, ACCOUNT_ORDER=order)
        timeline = investment_growth._build_timeline()
        state = investment_growth._build_state()
        summaries = investment_growth._simulate(timeline, state)
        return summaries[-1].net_worth

    tfsa_net_worth = _simulate(("tfsa",))
    unregistered_net_worth = _simulate(("unregistered",))

    assert tfsa_net_worth == pytest.approx(unregistered_net_worth)

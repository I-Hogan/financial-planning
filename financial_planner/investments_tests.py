"""Unit tests for investment account behaviors."""

import pytest

from financial_planner import tax_calculator
from financial_planner.investments import (
    RRSP,
    TFSA,
    FixedIncomeAsset,
    GlobalEquityIndexAsset,
    Investments,
    Unregistered,
)


def _round_money(amount: float) -> float:
    """Round currency values to two decimal places."""
    return round(amount, 2)


def _make_investments():
    """Build a sample Investments instance for tests."""
    asset_type = GlobalEquityIndexAsset(annual_growth_rate=0.1, annual_income_rate=0.05)
    tfsa = TFSA(asset_type=asset_type, initial_contribution_room=6000)
    rrsp = RRSP(asset_type=asset_type, initial_contribution_room=5000)
    unregistered = Unregistered(asset_type=asset_type)
    return Investments(tfsa=tfsa, rrsp=rrsp, unregistered=unregistered)


def test_investments_deposit_respects_order_and_room():
    """Deposits should follow priority ordering and contribution limits."""
    investments = _make_investments()
    remaining = investments.deposit(15000, ["tfsa", "rrsp", "unregistered"])

    assert remaining == 0
    assert investments.tfsa.balance == pytest.approx(6000)
    assert investments.rrsp.balance == pytest.approx(5000)
    assert investments.unregistered.balance == pytest.approx(4000)

    with pytest.raises(ValueError):
        investments.deposit(1000, ["tfsa", "rrsp"])


def test_increment_year_calculates_returns_and_tax():
    """Incrementing a year should update balances and tax inputs."""
    investments = _make_investments()
    investments.deposit(15000, ["tfsa", "rrsp", "unregistered"])

    result = investments.increment_year(annual_income=0.0)

    assert result.account_summaries["tfsa"].returns.growth == pytest.approx(600)
    assert result.account_summaries["tfsa"].returns.income == pytest.approx(300)
    assert result.account_summaries["rrsp"].returns.growth == pytest.approx(500)
    assert result.account_summaries["rrsp"].returns.income == pytest.approx(250)
    assert result.account_summaries["unregistered"].returns.growth == pytest.approx(400)
    assert result.account_summaries["unregistered"].returns.income == pytest.approx(200)

    assert investments.tfsa.balance == pytest.approx(6900)
    assert investments.rrsp.balance == pytest.approx(5750)
    assert investments.unregistered.balance == pytest.approx(4600)
    assert investments.unregistered.cost_basis == pytest.approx(4200)

    assert result.tax_summary.taxable_income == pytest.approx(200)
    assert result.tax_summary.deductions == pytest.approx(5000)
    assert result.tax_summary.net_taxable_income == pytest.approx(0)
    assert result.tax_summary.tax_owed == pytest.approx(0)

    assert investments.tfsa.deposits == pytest.approx(0)
    assert investments.rrsp.deposits == pytest.approx(0)
    assert investments.unregistered.withdrawals == pytest.approx(0)


def test_increment_year_twice_tracks_realized_gains():
    """Multiple years should track gains and resets correctly."""
    investments = _make_investments()
    investments.deposit(15000, ["tfsa", "rrsp", "unregistered"])
    investments.increment_year(annual_income=0.0)

    investments.deposit(3000, ["tfsa", "rrsp", "unregistered"])
    investments.rrsp.withdrawal(1000)
    investments.unregistered.withdrawal(1000)

    result = investments.increment_year(annual_income=0.0)

    assert investments.tfsa.balance == pytest.approx(11385)
    assert investments.rrsp.balance == pytest.approx(5462.5)
    assert investments.unregistered.balance == pytest.approx(4140)
    assert investments.unregistered.cost_basis == pytest.approx(3466.96)

    realized_gain = _round_money(1000 - _round_money(4200 * (1000 / 4600)))
    expected_unregistered_taxable = _round_money(180 + realized_gain * 0.5)
    expected_net_taxable = _round_money(1000 + expected_unregistered_taxable)

    assert result.account_summaries["unregistered"].tax_impact.taxable_income == pytest.approx(
        expected_unregistered_taxable
    )
    assert result.tax_summary.net_taxable_income == pytest.approx(expected_net_taxable)
    assert result.tax_summary.tax_owed == pytest.approx(
        tax_calculator.calculate_ontario_combined_income_tax(expected_net_taxable)
    )


def test_fixed_income_asset_returns_income_only():
    """Fixed income assets should generate income without growth."""
    asset_type = FixedIncomeAsset(annual_return_rate=0.04)
    account = TFSA(balance=1000, asset_type=asset_type)

    returns = account.calculate_returns()

    assert returns.growth == pytest.approx(0.0)
    assert returns.income == pytest.approx(40.0)


def test_unregistered_capital_losses_do_not_reduce_taxable_income():
    """Capital losses should not offset other taxable income."""
    account = Unregistered(balance=1000, cost_basis=2000)

    account.withdrawal(500)
    returns = account.calculate_returns()
    tax_impact = account.calculate_tax(returns)

    assert tax_impact.taxable_income == pytest.approx(0.0)


def test_tfsa_contribution_room_accumulates():
    """TFSA room should grow each year by the annual limit."""
    account = TFSA(initial_contribution_room=0.0)

    assert account.available_room() == pytest.approx(0.0)

    account.increment_year(previous_year_income=0.0)

    assert account.available_room() == pytest.approx(7000.0)


def test_rrsp_contribution_room_uses_previous_income():
    """RRSP room should grow by 18% of prior income up to the max."""
    account = RRSP(initial_contribution_room=0.0)

    account.increment_year(previous_year_income=50_000)

    assert account.available_room() == pytest.approx(9000.0)


def test_investments_deposit_raises_if_room_insufficient():
    """Deposits should fail when room is insufficient across ordered accounts."""
    investments = _make_investments()

    with pytest.raises(ValueError):
        investments.deposit(20_000, ["tfsa", "rrsp"])


def test_increment_year_includes_income_in_taxable_amount():
    """Annual income should be included in the tax summary."""
    investments = Investments(
        tfsa=TFSA(initial_contribution_room=7000),
        rrsp=RRSP(initial_contribution_room=10_000),
        unregistered=Unregistered(),
    )

    investments.deposit(5000, ["rrsp"])

    result = investments.increment_year(annual_income=50_000)

    assert result.tax_summary.taxable_income == pytest.approx(50_000)
    assert result.tax_summary.deductions == pytest.approx(5000)
    assert result.tax_summary.net_taxable_income == pytest.approx(45_000)
    assert result.tax_summary.tax_owed == pytest.approx(
        tax_calculator.calculate_ontario_combined_income_tax(45_000)
    )

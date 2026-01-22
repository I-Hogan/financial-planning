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
from financial_planner.tax_constants import (
    CAPITAL_GAINS_INCLUSION_RATE,
    RRSP_ANNUAL_CONTRIBUTION_LIMIT,
    RRSP_CONTRIBUTION_RATE,
    TFSA_ANNUAL_CONTRIBUTION_LIMIT,
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


def test_investments_withdraw_respects_order_and_balance():
    """Withdrawals should follow priority ordering and balances."""
    investments = _make_investments()
    investments.deposit(15000, ["tfsa", "rrsp", "unregistered"])

    remaining = investments.withdraw(7000, ["rrsp", "tfsa"])

    assert remaining == 0
    assert investments.rrsp.balance == pytest.approx(0)
    assert investments.tfsa.balance == pytest.approx(4000)
    assert investments.unregistered.balance == pytest.approx(4000)


def test_investments_withdraw_raises_when_balance_insufficient():
    """Withdrawals should fail when total balances are insufficient."""
    investments = _make_investments()
    investments.deposit(15000, ["tfsa", "rrsp", "unregistered"])
    starting_balances = (
        investments.tfsa.balance,
        investments.rrsp.balance,
        investments.unregistered.balance,
        investments.unregistered.cost_basis,
    )

    with pytest.raises(ValueError):
        investments.withdraw(20000, ["tfsa", "rrsp", "unregistered"])

    assert investments.tfsa.balance == pytest.approx(starting_balances[0])
    assert investments.rrsp.balance == pytest.approx(starting_balances[1])
    assert investments.unregistered.balance == pytest.approx(starting_balances[2])
    assert investments.unregistered.cost_basis == pytest.approx(starting_balances[3])


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


def test_tfsa_contribution_room_inflation_adjustment():
    """TFSA room should scale with inflation adjustments."""
    account = TFSA(initial_contribution_room=0.0)

    account.increment_year(previous_year_income=0.0, contribution_limit_adjustment=1.05)

    assert account.available_room() == pytest.approx(7350.0)


def test_rrsp_contribution_room_uses_previous_income():
    """RRSP room should grow by 18% of prior income up to the max."""
    account = RRSP(initial_contribution_room=0.0)

    account.increment_year(previous_year_income=50_000)

    assert account.available_room() == pytest.approx(9000.0)


def test_rrsp_contribution_room_inflation_adjustment_caps_limit():
    """RRSP room should respect inflation-adjusted contribution limits."""
    account = RRSP(initial_contribution_room=0.0)

    account.increment_year(previous_year_income=500_000, contribution_limit_adjustment=1.1)

    expected_limit = RRSP_ANNUAL_CONTRIBUTION_LIMIT * 1.1
    assert account.available_room() == pytest.approx(expected_limit)


def test_investments_increment_year_uses_next_year_inflation_for_rooms():
    """Portfolio increment should pass inflation adjustment to account rooms."""
    investments = Investments(
        tfsa=TFSA(initial_contribution_room=0.0),
        rrsp=RRSP(initial_contribution_room=0.0),
        unregistered=Unregistered(),
    )

    investments.increment_year(annual_income=200_000, next_year_inflation_adjustment=1.05)

    expected_tfsa_room = TFSA_ANNUAL_CONTRIBUTION_LIMIT * 1.05
    expected_rrsp_room = min(
        200_000 * RRSP_CONTRIBUTION_RATE, RRSP_ANNUAL_CONTRIBUTION_LIMIT * 1.05
    )
    assert investments.tfsa.available_room() == pytest.approx(expected_tfsa_room)
    assert investments.rrsp.available_room() == pytest.approx(expected_rrsp_room)


def test_increment_year_passes_inflation_adjustment_to_tax(monkeypatch):
    """Incrementing a year should pass inflation adjustment to tax calculations."""
    investments = _make_investments()
    captured = {}

    def _fake_tax(_income, inflation_adjustment=1.0):
        captured["inflation_adjustment"] = inflation_adjustment
        return 0.0

    monkeypatch.setattr(tax_calculator, "calculate_ontario_combined_income_tax", _fake_tax)

    investments.increment_year(annual_income=1000, inflation_adjustment=1.2)

    assert captured["inflation_adjustment"] == pytest.approx(1.2)


def test_total_value_passes_inflation_adjustment_to_tax(monkeypatch):
    """Total value should pass inflation adjustment to tax calculations."""
    investments = Investments(
        tfsa=TFSA(balance=0.0),
        rrsp=RRSP(balance=1000.0),
        unregistered=Unregistered(balance=0.0, cost_basis=0.0),
    )
    captured = {}

    def _fake_tax(_income, inflation_adjustment=1.0):
        captured["inflation_adjustment"] = inflation_adjustment
        return 0.0

    monkeypatch.setattr(tax_calculator, "calculate_ontario_combined_income_tax", _fake_tax)

    investments.total_value(inflation_adjustment=0.95)

    assert captured["inflation_adjustment"] == pytest.approx(0.95)


def test_increment_year_rejects_non_positive_inflation_adjustment():
    """Incrementing a year should reject non-positive inflation adjustments."""
    investments = _make_investments()

    with pytest.raises(ValueError):
        investments.increment_year(annual_income=0.0, inflation_adjustment=0.0)


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


def test_rrsp_deduction_reduces_tax_owed():
    """RRSP deductions should lower tax owed versus taxable accounts."""
    income = 80_000
    contribution = 10_000

    rrsp_investments = Investments(
        tfsa=TFSA(),
        rrsp=RRSP(initial_contribution_room=contribution),
        unregistered=Unregistered(),
    )
    rrsp_investments.deposit(contribution, ["rrsp"])
    rrsp_result = rrsp_investments.increment_year(annual_income=income)

    unregistered_investments = Investments(
        tfsa=TFSA(),
        rrsp=RRSP(),
        unregistered=Unregistered(),
    )
    unregistered_investments.deposit(contribution, ["unregistered"])
    unregistered_result = unregistered_investments.increment_year(annual_income=income)

    assert rrsp_result.tax_summary.tax_owed < unregistered_result.tax_summary.tax_owed


def test_tfsa_outperforms_unregistered_with_taxable_returns():
    """TFSA balances should exceed unregistered after taxes on returns."""
    contribution = 1000.0
    years = 5
    asset_type = GlobalEquityIndexAsset(annual_growth_rate=0.0, annual_income_rate=0.08)

    tfsa_investments = Investments(
        tfsa=TFSA(asset_type=asset_type, initial_contribution_room=100_000),
        rrsp=RRSP(),
        unregistered=Unregistered(),
    )
    tfsa_free_cash = 0.0

    unregistered_investments = Investments(
        tfsa=TFSA(),
        rrsp=RRSP(),
        unregistered=Unregistered(asset_type=asset_type),
    )
    unregistered_free_cash = 0.0

    for _ in range(years):
        tfsa_investments.deposit(contribution, ["tfsa"])
        tfsa_result = tfsa_investments.increment_year(annual_income=0.0)
        tfsa_free_cash = _round_money(tfsa_free_cash - tfsa_result.tax_summary.tax_owed)

        unregistered_investments.deposit(contribution, ["unregistered"])
        unregistered_result = unregistered_investments.increment_year(annual_income=0.0)
        unregistered_free_cash = _round_money(
            unregistered_free_cash - unregistered_result.tax_summary.tax_owed
        )

    tfsa_net_worth = _round_money(tfsa_free_cash + tfsa_investments.total_value())
    unregistered_net_worth = _round_money(
        unregistered_free_cash + unregistered_investments.total_value()
    )

    assert tfsa_net_worth > unregistered_net_worth


def test_total_value_matches_expected_liquidation_tax():
    """Total value should subtract the expected liquidation tax."""
    investments = Investments(
        tfsa=TFSA(balance=1000.0),
        rrsp=RRSP(balance=2000.0),
        unregistered=Unregistered(balance=3000.0, cost_basis=2500.0),
    )

    taxable_unregistered_gain = (3000.0 - 2500.0) * CAPITAL_GAINS_INCLUSION_RATE
    taxable_income = 2000.0 + taxable_unregistered_gain
    expected_tax = tax_calculator.calculate_ontario_combined_income_tax(taxable_income)
    expected_total = _round_money(6000.0 - expected_tax)

    assert investments.total_value(liquidation_years=1) == pytest.approx(expected_total)


def test_total_value_spread_liquidation_reduces_tax():
    """Spreading liquidation over years should reduce total tax."""
    investments = Investments(
        tfsa=TFSA(balance=0.0),
        rrsp=RRSP(balance=1_000_000.0),
        unregistered=Unregistered(balance=0.0, cost_basis=0.0),
    )

    single_year = investments.total_value(liquidation_years=1)
    spread_years = investments.total_value(liquidation_years=10)

    assert spread_years > single_year


def test_total_value_rejects_invalid_liquidation_years():
    """Liquidation years must be positive."""
    investments = Investments()

    with pytest.raises(ValueError):
        investments.total_value(liquidation_years=0)

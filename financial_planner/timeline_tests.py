"""Tests for timeline and event models."""

import pytest

from financial_planner.investments import RRSP, TFSA, Investments, Unregistered
from financial_planner.timeline import (
    DepositPolicy,
    Event,
    SetAnnualIncomeEvent,
    SetAnnualSpendingEvent,
    SetDepositPolicyEvent,
    SetFreeCashEvent,
    SetInvestmentAccountValuesEvent,
    SetRetirementEvent,
    SetWithdrawalPolicyEvent,
    SimulationState,
    Timeline,
    WithdrawalPolicy,
    YearContext,
)


class _RecordingEvent(Event):
    def __init__(self, calls, label):
        self.calls = calls
        self.label = label

    def resolve(self, state, context):
        _ = state
        self.calls.append((self.label, context.year))


def _context(start_year, year, inflation_rate=0.02):
    year_index = year - start_year
    inflation_factor = (1 + inflation_rate) ** year_index
    next_year_factor = (1 + inflation_rate) ** (year_index + 1)
    return YearContext(
        year=year,
        start_year=start_year,
        year_index=year_index,
        inflation_factor=inflation_factor,
        next_year_inflation_factor=next_year_factor,
    )


def test_timeline_requires_valid_year_range():
    """Timeline should reject invalid year ranges."""
    with pytest.raises(ValueError):
        Timeline(start_year=2026, end_year=2025)


def test_timeline_rejects_out_of_range_event():
    """Adding events outside the timeline range should fail."""
    timeline = Timeline(start_year=2026, end_year=2027)

    with pytest.raises(ValueError):
        timeline.add_event(2025, SetFreeCashEvent(amount=0.0))


def test_timeline_add_event_range_requires_valid_bounds():
    """Event ranges should require start year before end year."""
    timeline = Timeline(start_year=2026, end_year=2027)

    with pytest.raises(ValueError):
        timeline.add_event_range(2027, 2026, SetFreeCashEvent(amount=0.0))


def test_timeline_resolves_events_in_order():
    """Timeline buckets should resolve events in insertion order."""
    calls = []
    timeline = Timeline(start_year=2026, end_year=2026)
    timeline.add_event(2026, _RecordingEvent(calls, "first"))
    timeline.add_event(2026, _RecordingEvent(calls, "second"))
    bucket = next(iter(timeline))

    bucket.resolve(SimulationState(investments=Investments()), _context(2026, 2026))

    assert calls == [("first", 2026), ("second", 2026)]


def test_timeline_event_range_applies_to_each_year():
    """Event ranges should apply to every year bucket."""
    calls = []
    timeline = Timeline(start_year=2026, end_year=2028)
    event = _RecordingEvent(calls, "range")
    timeline.add_event_range(2026, 2028, event)

    for bucket in timeline:
        bucket.resolve(SimulationState(investments=Investments()), _context(2026, bucket.year))

    assert calls == [("range", 2026), ("range", 2027), ("range", 2028)]


def test_set_annual_income_event_applies_inflation():
    """Income events should respect inflation adjustments."""
    state = SimulationState(investments=Investments())
    event = SetAnnualIncomeEvent(amount=1000, inflation_adjusted=True)

    event.resolve(state, _context(2026, 2028, inflation_rate=0.1))

    assert state.annual_income == pytest.approx(1210.0)


def test_set_annual_spending_event_ignores_inflation_when_disabled():
    """Spending events should ignore inflation when configured."""
    state = SimulationState(investments=Investments())
    event = SetAnnualSpendingEvent(amount=800, inflation_adjusted=False)

    event.resolve(state, _context(2026, 2028, inflation_rate=0.1))

    assert state.annual_spending == pytest.approx(800.0)


def test_set_deposit_policy_event_updates_state():
    """Deposit policy events should update the simulation state."""
    state = SimulationState(investments=Investments())
    event = SetDepositPolicyEvent(
        annual_contribution=5000,
        account_order=("tfsa", "rrsp"),
        inflation_adjusted=False,
    )

    event.resolve(state, _context(2026, 2026))

    assert state.deposit_policy == DepositPolicy(
        annual_contribution=5000,
        account_order=("tfsa", "rrsp"),
        inflation_adjusted=False,
    )


def test_set_withdrawal_policy_event_updates_state():
    """Withdrawal policy events should update the simulation state."""
    state = SimulationState(investments=Investments())
    event = SetWithdrawalPolicyEvent(
        annual_withdrawal=2000,
        account_order=("rrsp",),
        inflation_adjusted=True,
    )

    event.resolve(state, _context(2026, 2026))

    assert state.withdrawal_policy == WithdrawalPolicy(
        annual_withdrawal=2000,
        account_order=("rrsp",),
        inflation_adjusted=True,
    )


def test_set_retirement_event_marks_state_and_policy():
    """Retirement events should mark retired and set withdrawal policy."""
    state = SimulationState(investments=Investments(), annual_income=2000.0)
    withdrawal_policy = WithdrawalPolicy(
        annual_withdrawal=1500,
        account_order=("tfsa",),
        inflation_adjusted=False,
    )
    event = SetRetirementEvent(withdrawal_policy=withdrawal_policy)

    event.resolve(state, _context(2026, 2026))

    assert state.retired is True
    assert state.annual_income == pytest.approx(0.0)
    assert state.withdrawal_policy == withdrawal_policy


def test_set_free_cash_event_updates_cash():
    """Free cash events should update the cash balance."""
    state = SimulationState(investments=Investments(), free_cash=100.0)

    SetFreeCashEvent(amount=250.0).resolve(state, _context(2026, 2026))

    assert state.free_cash == pytest.approx(250.0)


def test_set_investment_account_values_event_sets_balances_and_rooms():
    """Account value events should reset balances, rooms, and tracking."""
    investments = Investments(
        tfsa=TFSA(balance=10.0, initial_contribution_room=50.0),
        rrsp=RRSP(balance=20.0, initial_contribution_room=60.0),
        unregistered=Unregistered(balance=30.0, cost_basis=25.0),
    )
    investments.unregistered.realized_capital_gains = 15.0
    state = SimulationState(investments=investments)
    event = SetInvestmentAccountValuesEvent(
        tfsa_balance=100.0,
        rrsp_balance=200.0,
        unregistered_balance=300.0,
        tfsa_room=400.0,
        rrsp_room=500.0,
    )

    event.resolve(state, _context(2026, 2026))

    assert investments.tfsa.balance == pytest.approx(100.0)
    assert investments.tfsa.contribution_room == pytest.approx(400.0)
    assert investments.rrsp.balance == pytest.approx(200.0)
    assert investments.rrsp.contribution_room == pytest.approx(500.0)
    assert investments.unregistered.balance == pytest.approx(300.0)
    assert investments.unregistered.cost_basis == pytest.approx(300.0)
    assert investments.unregistered.realized_capital_gains == pytest.approx(0.0)


def test_policy_inflation_helpers_require_positive_factor():
    """Policy helpers should reject invalid inflation factors."""
    with pytest.raises(ValueError):
        DepositPolicy(annual_contribution=100.0, account_order=("tfsa",)).contribution_for_year(0.0)

    with pytest.raises(ValueError):
        WithdrawalPolicy(annual_withdrawal=100.0, account_order=("rrsp",)).withdrawal_for_year(-1.0)

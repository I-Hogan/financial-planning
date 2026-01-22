"""Timeline and event models for financial plan simulations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, Optional

from financial_planner.investments import AccountSelector, Investments, Unregistered


def _round_money(amount: float) -> float:
    """Round currency values to two decimal places."""
    return round(amount, 2)


@dataclass(frozen=True)
class YearContext:
    """Context for a specific simulation year."""

    year: int
    start_year: int
    year_index: int
    inflation_factor: float
    next_year_inflation_factor: float


class Event(ABC):
    """Abstract event resolved at the start of a simulation year."""

    @abstractmethod
    def resolve(self, state: "SimulationState", context: YearContext) -> None:
        """Apply event changes to the simulation state."""


@dataclass
class YearBucket:
    """Container for events tied to a specific year."""

    year: int
    events: list[Event] = field(default_factory=list)

    def add_event(self, event: Event) -> None:
        """Attach an event to the year."""
        self.events.append(event)

    def resolve(self, state: "SimulationState", context: YearContext) -> None:
        """Resolve all events for the year."""
        for event in self.events:
            event.resolve(state, context)


class Timeline:
    """Timeline with a bucket for each year in the simulation range."""

    def __init__(self, start_year: int, end_year: int) -> None:
        if end_year < start_year:
            raise ValueError("End year must be greater than or equal to start year.")
        self.start_year = start_year
        self.end_year = end_year
        self._buckets = {year: YearBucket(year=year) for year in range(start_year, end_year + 1)}

    def add_event(self, year: int, event: Event) -> None:
        """Add an event to the requested year."""
        self._bucket_for_year(year).add_event(event)

    def add_event_range(self, start_year: int, end_year: int, event: Event) -> None:
        """Add the same event to every year in the provided range."""
        if end_year < start_year:
            raise ValueError("End year must be greater than or equal to start year.")
        for year in range(start_year, end_year + 1):
            self.add_event(year, event)

    def _bucket_for_year(self, year: int) -> YearBucket:
        if year not in self._buckets:
            raise ValueError(f"Year {year} is outside the timeline range.")
        return self._buckets[year]

    def __iter__(self) -> Iterable[YearBucket]:
        for year in range(self.start_year, self.end_year + 1):
            yield self._buckets[year]


@dataclass(frozen=True)
class DepositPolicy:
    """Policy for annual contributions into investment accounts."""

    annual_contribution: float
    account_order: tuple[AccountSelector, ...]
    inflation_adjusted: bool = True

    def contribution_for_year(self, inflation_factor: float) -> float:
        """Return the configured contribution for the given inflation factor."""
        if inflation_factor <= 0:
            raise ValueError("Inflation adjustment must be positive.")
        factor = inflation_factor if self.inflation_adjusted else 1.0
        return _round_money(self.annual_contribution * factor)


@dataclass(frozen=True)
class WithdrawalPolicy:
    """Policy for annual withdrawals from investment accounts."""

    annual_withdrawal: float
    account_order: tuple[AccountSelector, ...]
    inflation_adjusted: bool = True

    def withdrawal_for_year(self, inflation_factor: float) -> float:
        """Return the configured withdrawal for the given inflation factor."""
        if inflation_factor <= 0:
            raise ValueError("Inflation adjustment must be positive.")
        factor = inflation_factor if self.inflation_adjusted else 1.0
        return _round_money(self.annual_withdrawal * factor)


@dataclass
class SimulationState:
    """Mutable state updated during simulation."""

    investments: Investments
    free_cash: float = 0.0
    annual_income: float = 0.0
    annual_spending: float = 0.0
    deposit_policy: Optional[DepositPolicy] = None
    withdrawal_policy: Optional[WithdrawalPolicy] = None
    retired: bool = False


@dataclass(frozen=True)
class SetAnnualIncomeEvent(Event):
    """Set the annual income for the current year."""

    amount: float
    inflation_adjusted: bool = True

    def resolve(self, state: SimulationState, context: YearContext) -> None:
        factor = context.inflation_factor if self.inflation_adjusted else 1.0
        state.annual_income = _round_money(self.amount * factor)


@dataclass(frozen=True)
class SetAnnualSpendingEvent(Event):
    """Set the annual spending for the current year."""

    amount: float
    inflation_adjusted: bool = True

    def resolve(self, state: SimulationState, context: YearContext) -> None:
        factor = context.inflation_factor if self.inflation_adjusted else 1.0
        state.annual_spending = _round_money(self.amount * factor)


@dataclass(frozen=True)
class SetDepositPolicyEvent(Event):
    """Set the policy used for annual contributions."""

    annual_contribution: float
    account_order: tuple[AccountSelector, ...]
    inflation_adjusted: bool = True

    def resolve(self, state: SimulationState, context: YearContext) -> None:
        _ = context
        state.deposit_policy = DepositPolicy(
            annual_contribution=self.annual_contribution,
            account_order=tuple(self.account_order),
            inflation_adjusted=self.inflation_adjusted,
        )


@dataclass(frozen=True)
class SetWithdrawalPolicyEvent(Event):
    """Set the policy used for annual withdrawals."""

    annual_withdrawal: float
    account_order: tuple[AccountSelector, ...]
    inflation_adjusted: bool = True

    def resolve(self, state: SimulationState, context: YearContext) -> None:
        _ = context
        state.withdrawal_policy = WithdrawalPolicy(
            annual_withdrawal=self.annual_withdrawal,
            account_order=tuple(self.account_order),
            inflation_adjusted=self.inflation_adjusted,
        )


@dataclass(frozen=True)
class SetRetirementEvent(Event):
    """Mark the simulation state as retired and optionally update withdrawals."""

    withdrawal_policy: Optional[WithdrawalPolicy] = None

    def resolve(self, state: SimulationState, context: YearContext) -> None:
        _ = context
        state.retired = True
        state.annual_income = 0.0
        if self.withdrawal_policy is not None:
            state.withdrawal_policy = self.withdrawal_policy


@dataclass(frozen=True)
class SetFreeCashEvent(Event):
    """Set the amount of free cash available outside investments."""

    amount: float

    def resolve(self, state: SimulationState, context: YearContext) -> None:
        _ = context
        state.free_cash = _round_money(self.amount)


@dataclass(frozen=True)
class SetInvestmentAccountValuesEvent(Event):
    """Set balances and contribution room for investment accounts."""

    tfsa_balance: Optional[float] = None
    rrsp_balance: Optional[float] = None
    unregistered_balance: Optional[float] = None
    unregistered_cost_basis: Optional[float] = None
    tfsa_room: Optional[float] = None
    rrsp_room: Optional[float] = None

    def resolve(self, state: SimulationState, context: YearContext) -> None:
        _ = context
        tfsa = state.investments.tfsa
        rrsp = state.investments.rrsp
        unregistered = state.investments.unregistered

        tfsa_updated = False
        rrsp_updated = False
        unregistered_updated = False

        if self.tfsa_balance is not None:
            tfsa.balance = _round_money(self.tfsa_balance)
            tfsa.year_start_balance = tfsa.balance
            tfsa_updated = True
        if self.tfsa_room is not None:
            tfsa.contribution_room = _round_money(self.tfsa_room)
            tfsa_updated = True
        if tfsa_updated:
            tfsa.deposits = 0.0
            tfsa.withdrawals = 0.0

        if self.rrsp_balance is not None:
            rrsp.balance = _round_money(self.rrsp_balance)
            rrsp.year_start_balance = rrsp.balance
            rrsp_updated = True
        if self.rrsp_room is not None:
            rrsp.contribution_room = _round_money(self.rrsp_room)
            rrsp_updated = True
        if rrsp_updated:
            rrsp.deposits = 0.0
            rrsp.withdrawals = 0.0

        if self.unregistered_balance is not None:
            unregistered.balance = _round_money(self.unregistered_balance)
            unregistered.year_start_balance = unregistered.balance
            unregistered_updated = True
            if self.unregistered_cost_basis is None:
                unregistered.cost_basis = _round_money(self.unregistered_balance)
        if self.unregistered_cost_basis is not None:
            unregistered.cost_basis = _round_money(self.unregistered_cost_basis)
            unregistered_updated = True
        if unregistered_updated:
            if isinstance(unregistered, Unregistered):
                unregistered.realized_capital_gains = 0.0
            unregistered.deposits = 0.0
            unregistered.withdrawals = 0.0

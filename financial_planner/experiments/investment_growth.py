"""Run a simple investment growth experiment."""

from dataclasses import dataclass
from importlib import import_module

from tabulate import tabulate

from financial_planner.investments import (
    RRSP,
    TFSA,
    GlobalEquityIndexAsset,
    Investments,
    Unregistered,
)
from financial_planner.timeline import (
    SetAnnualIncomeEvent,
    SetAnnualSpendingEvent,
    SetDepositPolicyEvent,
    SetFreeCashEvent,
    SetInvestmentAccountValuesEvent,
    SimulationState,
    Timeline,
    YearContext,
)

base_config = import_module("financial_planner.experiments.investment_growth_config")
try:
    config = import_module("financial_planner.experiments.investment_growth_config_personal")
except ImportError:
    config = base_config
else:
    for name in dir(base_config):
        if name.isupper() and not hasattr(config, name):
            setattr(config, name, getattr(base_config, name))


def _round_money(amount: float) -> float:
    """Round currency values to two decimal places."""
    return round(amount, 2)


def _format_money(amount: float) -> str:
    """Format currency with a dollar sign and thousands separators."""
    return f"${amount:,.2f}"


def _inflation_factor(year_index: int) -> float:
    """Return the inflation adjustment factor for a year index (year 0 = 1.0)."""
    if year_index < 0:
        raise ValueError("Year index cannot be negative.")
    return (1 + config.INFLATION_RATE) ** year_index


def _deflate_to_year_zero(amount: float, inflation_factor: float) -> float:
    """Convert a nominal amount into year-zero dollars."""
    return _round_money(amount / inflation_factor)


def _age_range() -> tuple[int, int]:
    """Return the configured start and end ages."""
    start_age = config.START_AGE
    end_age = config.END_AGE
    if end_age < start_age:
        raise ValueError("End age must be greater than or equal to start age.")
    return start_age, end_age


def _build_investments() -> Investments:
    """Construct the Investments model using experiment defaults."""
    asset_type = GlobalEquityIndexAsset(
        annual_growth_rate=config.GLOBAL_EQUITY_GROWTH_RATE,
        annual_income_rate=config.GLOBAL_EQUITY_INCOME_RATE,
    )
    return Investments(
        tfsa=TFSA(
            balance=0.0,
            asset_type=asset_type,
            initial_contribution_room=0.0,
        ),
        rrsp=RRSP(
            balance=0.0,
            asset_type=asset_type,
            initial_contribution_room=0.0,
        ),
        unregistered=Unregistered(
            balance=0.0,
            asset_type=asset_type,
            cost_basis=0.0,
        ),
    )


def _build_timeline() -> Timeline:
    """Build the timeline with configured events."""
    start_age, end_age = _age_range()
    timeline = Timeline(start_year=start_age, end_year=end_age)

    timeline.add_event(
        start_age,
        SetInvestmentAccountValuesEvent(
            tfsa_balance=config.INITIAL_TFSA_BALANCE,
            rrsp_balance=config.INITIAL_RRSP_BALANCE,
            unregistered_balance=config.INITIAL_UNREGISTERED_BALANCE,
            unregistered_cost_basis=config.INITIAL_UNREGISTERED_COST_BASIS,
            tfsa_room=config.INITIAL_TFSA_ROOM,
            rrsp_room=config.INITIAL_RRSP_ROOM,
        ),
    )
    timeline.add_event(start_age, SetFreeCashEvent(amount=config.INITIAL_FREE_CASH))

    income_event = SetAnnualIncomeEvent(
        amount=config.ANNUAL_INCOME,
        inflation_adjusted=True,
    )
    spending_event = SetAnnualSpendingEvent(
        amount=config.ANNUAL_SPENDING,
        inflation_adjusted=True,
    )
    deposit_event = SetDepositPolicyEvent(
        annual_contribution=config.ANNUAL_INVESTMENT_CONTRIBUTION,
        account_order=config.ACCOUNT_ORDER,
        inflation_adjusted=True,
    )
    timeline.add_event_range(start_age, end_age, income_event)
    timeline.add_event_range(start_age, end_age, spending_event)
    timeline.add_event_range(start_age, end_age, deposit_event)

    return timeline


def _build_state() -> SimulationState:
    """Create the initial simulation state."""
    return SimulationState(investments=_build_investments(), free_cash=0.0)


def _apply_contributions(
    investments: Investments,
    free_cash: float,
    annual_contribution: float,
    account_order: tuple,
) -> float:
    """Apply annual contributions and return updated free cash."""
    available_cash = max(0.0, free_cash)
    contribution = min(annual_contribution, available_cash)
    free_cash = _round_money(free_cash - contribution)
    leftover = investments.deposit(contribution, account_order)
    return _round_money(free_cash + leftover)


def _build_year_context(bucket_age: int, start_age: int) -> YearContext:
    """Build the year context for an age bucket."""
    year_index = bucket_age - start_age
    inflation_factor = _inflation_factor(year_index)
    next_year_inflation_factor = _inflation_factor(year_index + 1)
    return YearContext(
        year=bucket_age,
        start_year=start_age,
        year_index=year_index,
        inflation_factor=inflation_factor,
        next_year_inflation_factor=next_year_inflation_factor,
    )


def _apply_cashflow(state: SimulationState, context: YearContext) -> float:
    """Apply annual cash flow and return the nominal income used for taxes."""
    annual_income = _round_money(state.annual_income)
    annual_spending = _round_money(state.annual_spending)
    annual_contribution = 0.0
    if state.deposit_policy is not None:
        annual_contribution = state.deposit_policy.contribution_for_year(context.inflation_factor)

    state.free_cash = _round_money(state.free_cash + annual_income)

    if state.retired and state.withdrawal_policy is not None:
        annual_withdrawal = state.withdrawal_policy.withdrawal_for_year(context.inflation_factor)
        if annual_withdrawal > 0:
            state.investments.withdraw(annual_withdrawal, state.withdrawal_policy.account_order)
            state.free_cash = _round_money(state.free_cash + annual_withdrawal)

    if state.deposit_policy is not None and annual_contribution > 0:
        state.free_cash = _apply_contributions(
            state.investments,
            state.free_cash,
            annual_contribution,
            state.deposit_policy.account_order,
        )

    state.free_cash = _round_money(state.free_cash - annual_spending)
    return annual_income


@dataclass(frozen=True)
class YearSummary:
    """Summarized results for a simulation year."""

    age: int
    inflation_factor: float
    net_worth: float
    free_cash: float
    total_investments: float
    account_balances: dict[str, float]


def _simulate(timeline: Timeline, state: SimulationState) -> list[YearSummary]:
    """Run the simulation and return year summaries."""
    summaries: list[YearSummary] = []
    start_age = timeline.start_year

    for bucket in timeline:
        context = _build_year_context(bucket.year, start_age)
        bucket.resolve(state, context)
        annual_income = _apply_cashflow(state, context)

        result = state.investments.increment_year(
            annual_income=annual_income,
            inflation_adjustment=context.inflation_factor,
            next_year_inflation_adjustment=context.next_year_inflation_factor,
        )
        state.free_cash = _round_money(state.free_cash - result.tax_summary.tax_owed)

        total_investments = state.investments.total_value(
            inflation_adjustment=context.inflation_factor,
            liquidation_years=config.LIQUIDATION_YEARS,
        )
        net_worth = _round_money(state.free_cash + total_investments)
        account_balances = {
            "tfsa": state.investments.tfsa.balance,
            "rrsp": state.investments.rrsp.balance,
            "unregistered": state.investments.unregistered.balance,
        }
        summaries.append(
            YearSummary(
                age=bucket.year,
                inflation_factor=context.inflation_factor,
                net_worth=net_worth,
                free_cash=state.free_cash,
                total_investments=total_investments,
                account_balances=account_balances,
            )
        )

    return summaries


def run_experiment() -> None:
    """Run the experiment and print year-end results."""
    timeline = _build_timeline()
    state = _build_state()
    summaries = _simulate(timeline, state)

    rows = []
    for summary in summaries:
        inflation_factor = summary.inflation_factor
        balances = summary.account_balances
        rows.append(
            [
                summary.age,
                _format_money(_deflate_to_year_zero(summary.net_worth, inflation_factor)),
                _format_money(_deflate_to_year_zero(summary.free_cash, inflation_factor)),
                _format_money(_deflate_to_year_zero(summary.total_investments, inflation_factor)),
                _format_money(_deflate_to_year_zero(balances["tfsa"], inflation_factor)),
                _format_money(_deflate_to_year_zero(balances["rrsp"], inflation_factor)),
                _format_money(_deflate_to_year_zero(balances["unregistered"], inflation_factor)),
            ]
        )

    print(
        tabulate(
            rows,
            headers=[
                "Age",
                "Net Worth",
                "Free Cash",
                "Investments",
                "TFSA",
                "RRSP",
                "Unregistered",
            ],
            tablefmt="github",
        )
    )


if __name__ == "__main__":
    run_experiment()

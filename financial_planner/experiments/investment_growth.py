"""Run a simple investment growth experiment."""

from importlib import import_module

from tabulate import tabulate

from financial_planner.investments import (
    RRSP,
    TFSA,
    GlobalEquityIndexAsset,
    Investments,
    Unregistered,
)

try:
    config = import_module("financial_planner.experiments.investment_growth_config_personal")
except ImportError:
    config = import_module("financial_planner.experiments.investment_growth_config")


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


def _build_investments() -> Investments:
    """Construct the Investments model using experiment defaults."""
    asset_type = GlobalEquityIndexAsset(
        annual_growth_rate=config.GLOBAL_EQUITY_GROWTH_RATE,
        annual_income_rate=config.GLOBAL_EQUITY_INCOME_RATE,
    )
    return Investments(
        tfsa=TFSA(
            balance=config.INITIAL_TFSA_BALANCE,
            asset_type=asset_type,
            initial_contribution_room=config.INITIAL_TFSA_ROOM,
        ),
        rrsp=RRSP(
            balance=config.INITIAL_RRSP_BALANCE,
            asset_type=asset_type,
            initial_contribution_room=config.INITIAL_RRSP_ROOM,
        ),
        unregistered=Unregistered(
            balance=config.INITIAL_UNREGISTERED_BALANCE,
            asset_type=asset_type,
            cost_basis=config.INITIAL_UNREGISTERED_COST_BASIS,
        ),
    )


def _apply_contributions(
    investments: Investments, free_cash: float, annual_contribution: float
) -> float:
    """Apply annual contributions and return updated free cash."""
    available_cash = max(0.0, free_cash)
    contribution = min(annual_contribution, available_cash)
    free_cash = _round_money(free_cash - contribution)
    leftover = investments.deposit(contribution, config.ACCOUNT_ORDER)
    return _round_money(free_cash + leftover)


def run_experiment() -> None:
    """Run the experiment and print year-end results."""
    investments = _build_investments()
    free_cash = config.INITIAL_FREE_CASH
    rows = []

    for year in range(1, config.YEARS + 1):
        year_index = year - 1
        inflation_factor = _inflation_factor(year_index)
        next_year_inflation_factor = _inflation_factor(year_index + 1)
        annual_income = _round_money(config.ANNUAL_INCOME * inflation_factor)
        annual_contribution = _round_money(config.ANNUAL_INVESTMENT_CONTRIBUTION * inflation_factor)
        annual_spending = _round_money(config.ANNUAL_SPENDING * inflation_factor)

        free_cash = _round_money(free_cash + annual_income)
        free_cash = _apply_contributions(investments, free_cash, annual_contribution)
        free_cash = _round_money(free_cash - annual_spending)

        result = investments.increment_year(
            annual_income=annual_income,
            inflation_adjustment=inflation_factor,
            next_year_inflation_adjustment=next_year_inflation_factor,
        )
        free_cash = _round_money(free_cash - result.tax_summary.tax_owed)

        total_investments = investments.total_value(
            inflation_adjustment=inflation_factor,
            liquidation_years=config.LIQUIDATION_YEARS,
        )
        net_worth = _round_money(free_cash + total_investments)
        rows.append(
            [
                year,
                _format_money(_deflate_to_year_zero(net_worth, inflation_factor)),
                _format_money(_deflate_to_year_zero(free_cash, inflation_factor)),
                _format_money(_deflate_to_year_zero(total_investments, inflation_factor)),
                _format_money(_deflate_to_year_zero(investments.tfsa.balance, inflation_factor)),
                _format_money(_deflate_to_year_zero(investments.rrsp.balance, inflation_factor)),
                _format_money(
                    _deflate_to_year_zero(investments.unregistered.balance, inflation_factor)
                ),
            ]
        )

    print(
        tabulate(
            rows,
            headers=[
                "Year",
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

"""A tax calculator."""

from financial_planner.tax_constants import CANADA_TAX_BRACKETS, ONTARIO_TAX_BRACKETS


def _adjust_brackets_for_inflation(brackets, inflation_adjustment):
    """Scale bracket thresholds by an inflation adjustment factor."""
    if inflation_adjustment <= 0:
        raise ValueError("Inflation adjustment must be positive.")
    if inflation_adjustment == 1.0:
        return brackets
    adjusted = []
    for upper_limit, rate in brackets:
        if upper_limit is None:
            adjusted.append((None, rate))
        else:
            adjusted.append((round(upper_limit * inflation_adjustment, 2), rate))
    return tuple(adjusted)


def _calculate_progressive_tax(taxable_income, brackets):
    """Calculate tax owed for progressive tax brackets."""
    if taxable_income < 0:
        raise ValueError("Taxable income cannot be negative.")

    tax = 0.0
    lower_limit = 0.0

    for upper_limit, rate in brackets:
        if upper_limit is None:
            tax += (taxable_income - lower_limit) * rate
            break

        if taxable_income <= upper_limit:
            tax += (taxable_income - lower_limit) * rate
            break

        tax += (upper_limit - lower_limit) * rate
        lower_limit = upper_limit

    return round(tax, 2)


def calculate_ontario_income_tax(taxable_income, inflation_adjustment=1.0):
    """Calculates Ontario provincial income tax based on taxable income."""
    adjusted = _adjust_brackets_for_inflation(ONTARIO_TAX_BRACKETS, inflation_adjustment)
    return _calculate_progressive_tax(taxable_income, adjusted)


def calculate_canada_income_tax(taxable_income, inflation_adjustment=1.0):
    """Calculates Canada federal income tax based on taxable income."""
    adjusted = _adjust_brackets_for_inflation(CANADA_TAX_BRACKETS, inflation_adjustment)
    return _calculate_progressive_tax(taxable_income, adjusted)


def calculate_ontario_combined_income_tax(taxable_income, inflation_adjustment=1.0):
    """Calculate combined federal and provincial income tax for Ontario."""
    return round(
        calculate_canada_income_tax(taxable_income, inflation_adjustment=inflation_adjustment)
        + calculate_ontario_income_tax(taxable_income, inflation_adjustment=inflation_adjustment),
        2,
    )

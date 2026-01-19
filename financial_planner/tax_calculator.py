"""A tax calculator."""

from financial_planner.tax_constants import CANADA_TAX_BRACKETS, ONTARIO_TAX_BRACKETS


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


def calculate_ontario_income_tax(taxable_income):
    """Calculates Ontario provincial income tax based on taxable income."""
    return _calculate_progressive_tax(taxable_income, ONTARIO_TAX_BRACKETS)


def calculate_canada_income_tax(taxable_income):
    """Calculates Canada federal income tax based on taxable income."""
    return _calculate_progressive_tax(taxable_income, CANADA_TAX_BRACKETS)


def calculate_ontario_combined_income_tax(taxable_income):
    """Calculate combined federal and provincial income tax for Ontario."""
    return round(
        calculate_canada_income_tax(taxable_income) + calculate_ontario_income_tax(taxable_income),
        2,
    )

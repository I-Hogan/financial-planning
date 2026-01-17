"""Unit tests for the tax calculator helpers."""

import pytest

from financial_planner import tax_calculator


@pytest.mark.parametrize(
    "income, expected",
    [
        (0, 0.0),
        (50_000, 2525.0),
        (100_000, 6940.47),
        (250_000, 24823.99),
    ],
)
def test_calculate_ontario_income_tax(income, expected):
    """Validate Ontario tax results across representative incomes."""
    assert tax_calculator.calculate_ontario_income_tax(income) == pytest.approx(expected)


@pytest.mark.parametrize(
    "income, expected",
    [
        (0, 0.0),
        (50_000, 7000.0),
        (100_000, 16696.01),
        (250_000, 56815.33),
    ],
)
def test_calculate_canada_income_tax(income, expected):
    """Validate federal tax results across representative incomes."""
    assert tax_calculator.calculate_canada_income_tax(income) == pytest.approx(expected)


def test_combined_tax_matches_sum():
    """Ensure combined tax equals the sum of federal and provincial tax."""
    income = 100_000
    combined = tax_calculator.calculate_ontario_combined_income_tax(income)
    expected = tax_calculator.calculate_canada_income_tax(
        income
    ) + tax_calculator.calculate_ontario_income_tax(income)
    assert combined == pytest.approx(expected)


@pytest.mark.parametrize("income", [-1, -100.50])
def test_negative_income_raises(income):
    """Reject negative taxable income inputs."""
    with pytest.raises(ValueError):
        tax_calculator.calculate_canada_income_tax(income)


def test_ontario_bracket_boundary():
    """Verify Ontario tax at a bracket boundary."""
    assert tax_calculator.calculate_ontario_income_tax(53_891) == pytest.approx(2721.5)


def test_canada_bracket_boundary():
    """Verify federal tax at a bracket boundary."""
    assert tax_calculator.calculate_canada_income_tax(58_523) == pytest.approx(8193.22)

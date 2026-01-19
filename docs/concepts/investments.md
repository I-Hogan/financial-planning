# Investments

The investments module models TFSA, RRSP, and unregistered accounts with a
shared interface. Each account tracks annual deposits, withdrawals, and
returns split into growth and income so tax can be computed accurately.

The `Investments.total_value` helper estimates the after-tax value if all
accounts were liquidated in a single year, applying Ontario tax treatment for
RRSP withdrawals and taxable capital gains on unregistered balances.

Accounts are configured with an asset type to determine how returns are
generated. Fixed income assets return cash income only, while global equity
index assets split returns between growth and income.

Contribution room is tracked per account. TFSA room grows by the annual
contribution limit each year, accumulates, and restores prior-year withdrawals.
RRSP room grows by 18% of the prior year's income (capped at the annual
maximum).

## Annual flow

- Deposits and withdrawals update the account balance during the year.
- Returns are calculated on the year-end balance and reinvested.
- Taxes are computed from the year activity:
  - TFSA: no tax on returns or withdrawals.
  - RRSP: deposits are deductions; withdrawals are taxable income.
  - Unregistered: income returns are taxable; realized capital gains from
    withdrawals are taxed at the inclusion rate (capital losses are not applied
    to offset income).
- `increment_year` resets annual tracking and sets the next year start balance.
- `increment_year` can accept annual income to include it in tax calculations
  and to grow RRSP contribution room for the next year.

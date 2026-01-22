# Timeline and Events

The simulation framework is built around timeline and event models in
`financial_planner/timeline.py`.

## Timeline

- A `Timeline` contains a year bucket for each year in its configured range.
  The investment growth experiment uses ages (`START_AGE` through `END_AGE`)
  as the bucket values.
- Each `YearBucket` stores a list of events resolved at the start of that year.
- `YearContext` supplies the year index plus the current and next-year inflation
  factors for events and simulation logic.

## Events and State

- Events mutate `SimulationState`, which tracks free cash, annual income,
  annual spending, investment balances, and cash flow policies.
- `SetAnnualIncomeEvent` and `SetAnnualSpendingEvent` can apply inflation
  adjustments using the year context.
- `SetDepositPolicyEvent` and `SetWithdrawalPolicyEvent` define annual policies
  for contributions and withdrawals.
- `SetRetirementEvent` marks the state as retired, zeroes annual income, and can
  update withdrawal policy.
- `SetInvestmentAccountValuesEvent` and `SetFreeCashEvent` initialize balances
  and cash at the start of the timeline.

The investment growth experiment builds a timeline and applies these events
before calculating yearly cash flow, investment returns, and taxes.

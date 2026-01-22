# Architecture

High-level overview of the system architecture, key components, data flows, and
significant design decisions.

## Django Project Layout

- `config/`: Project configuration, settings, and URL routing.
- `financial_planner/`: Core application for financial planning features.

## Simulation Core

- `financial_planner/timeline.py`: Timeline and event models resolved at the start of each year.
- Experiments iterate year buckets, apply events to simulation state, and then
  compute annual cash flow plus investment growth and taxes.

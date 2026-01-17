"""App configuration for the financial planner Django app."""

from django.apps import AppConfig


class FinancialPlannerConfig(AppConfig):
    """Configure the financial planner Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "financial_planner"

"""
Service Line Cards Module
=========================

Provides a tiny service to compute the four KPI cards for a selected
Service Line (SL). It intentionally mirrors the structure of the
`manager_revenue_days` analytics service but exposes only the four
aggregates requested by the user:

- ANSR YTD (from `fytd_ansr_sintetico`)
- Horas Cargadas YTD (from `fytd_charged_hours`)
- ANSR MTD (from `mtd_ansr_amt`)
- Horas Cargadas MTD (from `mtd_charged_hours`)

This module returns only those cards and does not implement goals or
additional manager-specific functionality.
"""

from .services import ServiceLineCardsService
from .analytics import ServiceLineAnalyticsService

__all__ = [
    'ServiceLineCardsService',
    'ServiceLineAnalyticsService',
]

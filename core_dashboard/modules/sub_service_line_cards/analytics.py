"""
Sub Service Line Analytics
==========================

Aggregates `RevenueEntry` by `engagement_sub_service_line` (Final_Database column `EngagementSubServiceLine`)
and returns the four KPI values required by the dashboard cards.
"""

import logging
from django.db.models import Sum, Q
from core_dashboard.models import RevenueEntry

logger = logging.getLogger(__name__)


class SubServiceLineAnalyticsService:
    """Calculate aggregates for a given Sub Service Line (SSL).

    Public method:
      - get_ssl_cards(ssl_name, start_date=None, end_date=None)

    Returns a dict with keys:
      - ssl_fytd_ansr_value
      - ssl_fytd_charged_hours
      - ssl_mtd_ansr_value
      - ssl_mtd_charged_hours
    """

    def __init__(self):
        pass

    def get_ssl_cards(self, ssl_name: str, start_date=None, end_date=None):
        """Return the four KPI aggregates for the supplied SSL name.

        If no entries are found for the SSL, returns zeros for all values.
        """
        try:
            if not ssl_name:
                logger.warning("Empty SSL name provided to SubServiceLineAnalyticsService")
                return self._empty_cards()

            # Normalize input and match the engagement_sub_service_line field
            normalized_ssl = ssl_name.strip() if isinstance(ssl_name, str) else ssl_name
            qs = RevenueEntry.objects.filter(engagement_sub_service_line__iexact=normalized_ssl)

            # Apply date filtering if provided
            if start_date and end_date:
                qs = qs.filter(date__range=[start_date, end_date])

            if not qs.exists():
                logger.info(f"No entries found for SSL: {ssl_name}")
                return self._empty_cards()

            aggregates = qs.aggregate(
                fytd_ansr=Sum('fytd_ansr_sintetico'),
                fytd_hours=Sum('fytd_charged_hours'),
                mtd_ansr=Sum('mtd_ansr_amt'),
                mtd_hours=Sum('mtd_charged_hours'),
            )

            return {
                'ssl_fytd_ansr_value': float(aggregates.get('fytd_ansr') or 0.0),
                'ssl_fytd_charged_hours': float(aggregates.get('fytd_hours') or 0.0),
                'ssl_mtd_ansr_value': float(aggregates.get('mtd_ansr') or 0.0),
                'ssl_mtd_charged_hours': float(aggregates.get('mtd_hours') or 0.0),
            }

        except Exception as e:
            logger.error(f"Error computing SSL cards for {ssl_name}: {e}")
            return self._empty_cards()

    def _empty_cards(self):
        return {
            'ssl_fytd_ansr_value': 0.0,
            'ssl_fytd_charged_hours': 0.0,
            'ssl_mtd_ansr_value': 0.0,
            'ssl_mtd_charged_hours': 0.0,
        }

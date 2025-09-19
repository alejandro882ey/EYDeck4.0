"""
Service Line Analytics
======================

Aggregates `RevenueEntry` by `engagement_service_line` and returns the
four KPI values required by the dashboard cards.
"""

import logging
from django.db.models import Sum, Q
from core_dashboard.models import RevenueEntry

logger = logging.getLogger(__name__)


class ServiceLineAnalyticsService:
    """Calculate aggregates for a given Service Line (SL).

    Public method:
      - get_sl_cards(sl_name)

    Returns a dict with keys:
      - sl_fytd_ansr_value
      - sl_fytd_charged_hours
      - sl_mtd_ansr_value
      - sl_mtd_charged_hours
    """

    def __init__(self):
        pass

    def get_sl_cards(self, sl_name: str, start_date=None, end_date=None):
        """Return the four KPI aggregates for the supplied SL name.

        If no entries are found for the SL, returns zeros for all values.
        """
        try:
            if not sl_name:
                logger.warning("Empty SL name provided to ServiceLineAnalyticsService")
                return self._empty_cards()

            # Normalize input and match either the engagement_service_line text or the related Area name
            normalized_sl = sl_name.strip() if isinstance(sl_name, str) else sl_name
            qs = RevenueEntry.objects.filter(
                Q(engagement_service_line__iexact=normalized_sl) | Q(area__name__iexact=normalized_sl)
            )

            # Apply date filtering if provided (so cards reflect the same week/report)
            if start_date and end_date:
                qs = qs.filter(date__range=[start_date, end_date])

            if not qs.exists():
                logger.info(f"No entries found for SL: {sl_name}")
                return self._empty_cards()

            aggregates = qs.aggregate(
                fytd_ansr=Sum('fytd_ansr_sintetico'),
                fytd_hours=Sum('fytd_charged_hours'),
                mtd_ansr=Sum('mtd_ansr_amt'),
                mtd_hours=Sum('mtd_charged_hours'),
            )

            return {
                'sl_fytd_ansr_value': float(aggregates.get('fytd_ansr') or 0.0),
                'sl_fytd_charged_hours': float(aggregates.get('fytd_hours') or 0.0),
                'sl_mtd_ansr_value': float(aggregates.get('mtd_ansr') or 0.0),
                'sl_mtd_charged_hours': float(aggregates.get('mtd_hours') or 0.0),
            }

        except Exception as e:
            logger.error(f"Error computing SL cards for {sl_name}: {e}")
            return self._empty_cards()

    def _empty_cards(self):
        return {
            'sl_fytd_ansr_value': 0.0,
            'sl_fytd_charged_hours': 0.0,
            'sl_mtd_ansr_value': 0.0,
            'sl_mtd_charged_hours': 0.0,
        }

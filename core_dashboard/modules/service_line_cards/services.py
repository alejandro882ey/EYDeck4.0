"""
Service Line Cards Service
==========================

Small wrapper service intended to be used by views to fetch the four
cards for a selected Service Line (SL). This file intentionally keeps
logic minimal and delegates computation to the analytics service.
"""

from .analytics import ServiceLineAnalyticsService
import logging

logger = logging.getLogger(__name__)


class ServiceLineCardsService:
    def __init__(self):
        self.analytics = ServiceLineAnalyticsService()

    def get_cards_for_sl(self, sl_name: str, start_date=None, end_date=None):
        """Return a compact list/dict structure ready to be rendered as cards.

        Structure returned:
          {
              'sl_name': <name>,
              'cards': [
                  {'key': 'ANSR_YTD', 'label': 'ANSR YTD', 'value': <float>},
                  {'key': 'Horas_YTD', 'label': 'Horas Cargadas YTD', 'value': <float>},
                  {'key': 'ANSR_MTD', 'label': 'ANSR MTD', 'value': <float>},
                  {'key': 'Horas_MTD', 'label': 'Horas Cargadas MTD', 'value': <float>},
              ]
          }
        """
        try:
            data = self.analytics.get_sl_cards(sl_name, start_date=start_date, end_date=end_date)

            cards = [
                {'key': 'ANSR_YTD', 'label': 'ANSR YTD', 'value': data['sl_fytd_ansr_value']},
                {'key': 'Horas_YTD', 'label': 'Horas Cargadas YTD', 'value': data['sl_fytd_charged_hours']},
                {'key': 'ANSR_MTD', 'label': 'ANSR MTD', 'value': data['sl_mtd_ansr_value']},
                {'key': 'Horas_MTD', 'label': 'Horas Cargadas MTD', 'value': data['sl_mtd_charged_hours']},
            ]

            return {
                'sl_name': sl_name,
                'cards': cards
            }

        except Exception as e:
            logger.error(f"Error in get_cards_for_sl: {e}")
            # Return empty structure on error
            return {
                'sl_name': sl_name,
                'cards': [
                    {'key': 'ANSR_YTD', 'label': 'ANSR YTD', 'value': 0.0},
                    {'key': 'Horas_YTD', 'label': 'Horas Cargadas YTD', 'value': 0.0},
                    {'key': 'ANSR_MTD', 'label': 'ANSR MTD', 'value': 0.0},
                    {'key': 'Horas_MTD', 'label': 'Horas Cargadas MTD', 'value': 0.0},
                ]
            }

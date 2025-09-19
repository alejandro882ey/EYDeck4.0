"""
Sub Service Line Cards Service
===============================

Wrapper service used by views to fetch four card values for a selected Sub Service Line (SSL).
"""

from .analytics import SubServiceLineAnalyticsService
import logging

logger = logging.getLogger(__name__)


class SubServiceLineCardsService:
    def __init__(self):
        self.analytics = SubServiceLineAnalyticsService()

    def get_cards_for_ssl(self, ssl_name: str, start_date=None, end_date=None):
        try:
            data = self.analytics.get_ssl_cards(ssl_name, start_date=start_date, end_date=end_date)

            cards = [
                {'key': 'ANSR_YTD', 'label': 'ANSR YTD', 'value': data['ssl_fytd_ansr_value']},
                {'key': 'Horas_YTD', 'label': 'Horas Cargadas YTD', 'value': data['ssl_fytd_charged_hours']},
                {'key': 'ANSR_MTD', 'label': 'ANSR MTD', 'value': data['ssl_mtd_ansr_value']},
                {'key': 'Horas_MTD', 'label': 'Horas Cargadas MTD', 'value': data['ssl_mtd_charged_hours']},
            ]

            return {
                'ssl_name': ssl_name,
                'cards': cards
            }

        except Exception as e:
            logger.error(f"Error in get_cards_for_ssl: {e}")
            return {
                'ssl_name': ssl_name,
                'cards': [
                    {'key': 'ANSR_YTD', 'label': 'ANSR YTD', 'value': 0.0},
                    {'key': 'Horas_YTD', 'label': 'Horas Cargadas YTD', 'value': 0.0},
                    {'key': 'ANSR_MTD', 'label': 'ANSR MTD', 'value': 0.0},
                    {'key': 'Horas_MTD', 'label': 'Horas Cargadas MTD', 'value': 0.0},
                ]
            }

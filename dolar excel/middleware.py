"""Django middleware to optionally trigger exchange-rate update on each request.

Configure in Django settings:

DOLAR_EXCEL = {
    "ENABLED": True,
    "EXCEL_PATH": r"C:\\Users\\CK624GF\\OneDrive - EY\\Documents\\2025\\dashboard_django\\dolar excel\\Historial_TCBinance.xlsx",
}

Add 'dolar excel.middleware.DolarExcelMiddleware' to MIDDLEWARE if desired.
"""
from __future__ import annotations

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class DolarExcelMiddleware:
    """Middleware that attempts to run an update check. Designed to be safe and
    non-blocking — failures are logged but don't break requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        cfg = getattr(settings, "DOLAR_EXCEL", {})
        self.enabled = bool(cfg.get("ENABLED", False))
        self.excel_path = cfg.get("EXCEL_PATH")

    def __call__(self, request):
        if self.enabled and self.excel_path:
            try:
                # Lazy import to avoid requiring openpyxl unless enabled
                from .services import EmailRateUpdater

                updater = EmailRateUpdater(self.excel_path)
                # In this design we don't read email automatically here; the
                # update can be triggered by other parts. For safety we do nothing.
                # Placeholder for future implementation.
            except Exception as e:
                logger.exception("DolarExcelMiddleware failed: %s", e)

        response = self.get_response(request)
        return response

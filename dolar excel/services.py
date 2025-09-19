"""Service layer to update Historial_TCBinance.xlsx from parsed email content.

This file intentionally keeps IMAP/credentials optional. For automated runs inside
the web app, configuration must be provided in Django settings (see README).
"""
from __future__ import annotations

import os
from typing import Optional
from openpyxl import load_workbook

from .utils import parse_email_rates


class EmailRateUpdater:
    """Small service to update the Excel file with new rates.

    Usage:
      updater = EmailRateUpdater(excel_path)
      updater.check_and_update_from_email_body(email_body)
    """

    def __init__(self, excel_path: str):
        if not os.path.isabs(excel_path):
            raise ValueError("excel_path must be absolute")
        self.excel_path = excel_path

    def check_and_update_from_email_body(self, body: str) -> Optional[dict]:
        """Parse body and append a new row to the first sheet.

        Returns the appended row dict or None if parsing failed.
        """
        data = parse_email_rates(body)
        if not data:
            return None

        wb = load_workbook(self.excel_path)
        ws = wb.active

        # Decide on columns - infer if headers exist in first row
        # We'll append: datetime (bcv_ts), bcv, paralelo_ts, paralelo
        ws.append([
            data.get("bcv_ts"),
            data.get("bcv"),
            data.get("paralelo_ts"),
            data.get("paralelo"),
        ])
        wb.save(self.excel_path)

        return data

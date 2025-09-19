dolar excel module
===================

This small module provides utilities to parse exchange-rate emails and append rows
to the Excel workbook `Historial_TCBinance.xlsx`.

Quick start
-----------

1. Configure in Django settings (optional) if you want the middleware enabled:

   DOLAR_EXCEL = {
       "ENABLED": True,
       "EXCEL_PATH": r"C:\\full\\path\\to\\Historial_TCBinance.xlsx",
   }

2. Use the service directly from scripts or views:

   from dolar excel.services import EmailRateUpdater
   updater = EmailRateUpdater(r"C:\\full\\path\\to\\Historial_TCBinance.xlsx")
   updater.check_and_update_from_email_body(email_body_text)

Security and email reading
--------------------------
This module does NOT include automatic email reading by default. If you want to fetch
email from an IMAP server, implement a small wrapper that retrieves messages from
`Erick.Lujan@ve.ey.com` sender and passes the message body to
`check_and_update_from_email_body`.

Notes
-----
- The module assumes the email body uses the pattern:
  "BCV: <value> Bs/USD (Fecha: <ISO>)\nParalelo: <value> Bs/USD (Fecha: <ISO>)"
- Tests exist for the parser in `tests.py`.

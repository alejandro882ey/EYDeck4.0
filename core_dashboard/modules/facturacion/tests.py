import io
import pandas as pd
from django.test import TestCase
from .services import FacturacionService

class FacturacionServiceTests(TestCase):
    def test_process_and_totals(self):
        # Build a small DataFrame that mimics the FY26 sheet
        data = {
            'Net Amount Local': [1000.0, 2000.5, 321.63],
            'Accounting Cycle Date': ['2025-07-10', '2025-07-15', '2025-07-18'],
            'Fiscal Year': ['2026', '2026', '2026'],
            'Engagement Country/Region': ['Venezuela', 'Venezuela', 'Venezuela']
        }
        df = pd.DataFrame(data)

        # Write to BytesIO Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='FY26')
        buffer.seek(0)

        service = FacturacionService()
        result = service.process_uploaded_file(buffer, original_filename='Facturacion_test.xlsx')
        self.assertTrue(result.get('success'), msg=result.get('error'))
        # billed_total should be approx sum of Net Amount Local
        expected_sum = sum(data['Net Amount Local'])
        self.assertAlmostEqual(result.get('billed_total'), expected_sum, places=2)

        # Now test get_totals_from_file up to a date
        latest = service.get_latest_file_info()
        self.assertIsNotNone(latest)
        billed_up_to_15 = service.get_totals_from_file(latest['path'], up_to_date=pd.to_datetime('2025-07-15').date())
        # When filtering by week-report date, Accounting Cycle Date represents the report date;
        # therefore we expect only rows with Accounting Cycle Date == up_to_date (the second entry)
        self.assertAlmostEqual(billed_up_to_15, data['Net Amount Local'][1], places=2)

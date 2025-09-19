import io
import pandas as pd
from django.test import TestCase
from .services import FacturacionService


class FacturacionIntegrationTests(TestCase):
    def test_cumulative_billed_for_report_date(self):
        # Build a DataFrame where the report date 2025-07-11 has a total of 559,410.59
        data = {
            'Net Amount Local': [100.0, 200.0, 559410.59, 50.0],
            'Accounting Cycle Date': ['2025-07-10', '2025-07-10', '2025-07-11', '2025-07-12'],
            'Fiscal Year': ['2026', '2026', '2026', '2026'],
            'Engagement Country/Region': ['Venezuela', 'Venezuela', 'Venezuela', 'Venezuela']
        }
        df = pd.DataFrame(data)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Facturacion')
        buffer.seek(0)

        service = FacturacionService()
        result = service.process_uploaded_file(buffer, original_filename='Facturacion_test_integration.xlsx')
        self.assertTrue(result.get('success'), msg=result.get('error'))

        billed_on_2025_07_11 = service.get_cumulative_billed_up_to(pd.to_datetime('2025-07-11').date())
        self.assertAlmostEqual(billed_on_2025_07_11, 559410.59, places=2)
import io
import pandas as pd
from django.test import TestCase, Client
from django.urls import reverse

class FacturacionIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_upload_endpoint_and_status_and_dashboard_macro(self):
        # Build a small DataFrame that mimics the FY26 sheet
        data = {
            'Net Amount Local': [1000.0, 2000.0, 3000.0],
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

        # Upload to the /facturacion/upload/ endpoint
        resp = self.client.post(reverse('facturacion:upload'), {'facturacion_file': buffer}, format='multipart')
        self.assertEqual(resp.status_code, 200)
        resp_json = resp.json()
        self.assertTrue(resp_json.get('success'))

        # Check status endpoint
        status = self.client.get(reverse('facturacion:status'))
        self.assertEqual(status.status_code, 200)
        status_json = status.json()
        self.assertTrue(status_json.get('file_exists'))
        self.assertAlmostEqual(status_json.get('billed_total'), sum(data['Net Amount Local']), places=2)

        # Finally, call dashboard view and ensure macro_billed_total appears in context
        dash = self.client.get(reverse('dashboard'))
        self.assertEqual(dash.status_code, 200)
        # The view renders HTML; we assert the macro value formatted appears
        content = dash.content.decode('utf-8')
        self.assertIn('${:,.0f}'.format(sum(data['Net Amount Local'])), content)

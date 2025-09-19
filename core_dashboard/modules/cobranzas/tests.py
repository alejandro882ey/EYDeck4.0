from django.test import TestCase, Client
from django.conf import settings
import os
import shutil
from .services import CobranzasService


class CobranzasModuleTests(TestCase):
    def setUp(self):
        self.svc = CobranzasService()
        # ensure media folder exists and is empty for tests
        if os.path.exists(self.svc.media_folder):
            # remove test artifacts if any
            for fn in os.listdir(self.svc.media_folder):
                p = os.path.join(self.svc.media_folder, fn)
                try:
                    os.remove(p)
                except Exception:
                    pass
        else:
            os.makedirs(self.svc.media_folder, exist_ok=True)

    def tearDown(self):
        # clean up any files created
        if os.path.exists(self.svc.media_folder):
            for fn in os.listdir(self.svc.media_folder):
                p = os.path.join(self.svc.media_folder, fn)
                try:
                    os.remove(p)
                except Exception:
                    pass

    def _create_dummy_processed(self, name, content='col1\n1'):
        p = os.path.join(self.svc.media_folder, name)
        # create minimal xlsx using pandas
        try:
            import pandas as pd
            df = pd.DataFrame({'col1': [1, 2]})
            df.to_excel(p, index=False)
        except Exception:
            # fallback: create empty file
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write(content)
        return p

    def test_get_available_report_dates_and_preview_data(self):
        # create two dummy processed files with dates in filename
        self._create_dummy_processed('Cobranzas_2025-07-01.xlsx')
        self._create_dummy_processed('Cobranzas_2025-07-15.xlsx')

        reports = self.svc.get_available_report_dates()
        self.assertTrue(isinstance(reports, list))
        self.assertTrue(len(reports) >= 2)
        dates = [r['date'] for r in reports]
        self.assertIn('2025-07-01', dates)
        self.assertIn('2025-07-15', dates)

        # Test preview data endpoint
        client = Client()
        res = client.get('/cobranzas/preview_data/', {'report_date': '2025-07-01'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get('success'))
        self.assertIn('cumulative_up_to', data)
        self.assertIn('usd_mtd', data)

    def test_process_uploaded_file_creates_suffixed_columns(self):
        """Create a small Excel in-memory with BCV rate column followed by an equivalent column and
        ensure process_uploaded_file writes the suffixed columns and maps values correctly."""
        import pandas as pd
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Build DataFrame with BCV exchange column and an adjacent equivalence column
        df = pd.DataFrame({
            'Cliente': ['A', 'B'],
            'Tipo de Cambio BCV': [24.5, 24.6],
            'Monto equivalente en USD de los VES Cobrados': [100.0, 200.0],
            'Monto en Dólares de la Factura': [50.0, 75.0]
        })

        bio = BytesIO()
        df.to_excel(bio, index=False, sheet_name='Cobranzas')
        bio.seek(0)

        uploaded = SimpleUploadedFile('test_cobranzas.xlsx', bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        res = self.svc.process_uploaded_file(uploaded, original_filename='Cobranzas_test.xlsx')
        self.assertTrue(res.get('success'), msg=res)
        out_path = res.get('output_path')
        self.assertTrue(os.path.exists(out_path))

        # Read back processed file and assert suffixed columns
        df_out = pd.read_excel(out_path)
        self.assertIn('Monto equivalente en USD de los VES Cobrados (BCV)', df_out.columns)
        # Check values copied
        vals = pd.to_numeric(df_out['Monto equivalente en USD de los VES Cobrados (BCV)'], errors='coerce').fillna(0).tolist()
        self.assertEqual(sum(vals), 300.0)

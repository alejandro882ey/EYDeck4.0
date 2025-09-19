import os
import pandas as pd
import tempfile
from core_dashboard.modules.cobranzas.services import CobranzasService


def write_test_file(df, path):
    df.to_excel(path, index=False, sheet_name='Cobranzas')


def test_bcv_invoice_rate_conversion(tmp_path):
    # Create a small DataFrame with explicit headers including the canonical ones
    df = pd.DataFrame({
        'Fecha de Cobro': ['2025-07-07', '2025-07-16'],
        'Monto en Bolívares de la Factura': [12140.0, 29512.0],
        'Tipo de Cambio Usado en la Emisión de la Factura BCV': [100.0, 200.0],
        'Monto en Dólares de la Factura': [0.0, 0.0]
    })
    # Ensure Django settings provide MEDIA_ROOT for the service when running outside full Django
    from django.conf import settings
    if not settings.configured:
        settings.configure(MEDIA_ROOT=str(tmp_path))
    svc = CobranzasService()
    # ensure media folder exists and use a temp file inside it
    out_dir = tmp_path
    out_file = os.path.join(out_dir, 'Cobranzas_test.xlsx')
    write_test_file(df, out_file)

    usd_total, ves_equiv_total, ves_bolivares_total = svc.get_breakdown_from_file(out_file)
    # Expected: ves_equiv_total = 12140/100 + 29512/200 = 121.4 + 147.56 = 268.96
    assert abs(ves_equiv_total - 268.96) < 0.01


def test_totals_from_file_prefers_bcv(tmp_path):
    df = pd.DataFrame({
        'Fecha de Cobro': ['2025-07-07'],
        'Monto en Bolívares de la Factura': [12140.0],
        'Tipo de Cambio Usado en la Emisión de la Factura BCV': [100.0],
        'Monto en Dólares de la Factura': [0.0]
    })
    from django.conf import settings
    if not settings.configured:
        settings.configure(MEDIA_ROOT=str(tmp_path))
    svc = CobranzasService()
    out_file = tmp_path / 'Cobranzas_test2.xlsx'
    df.to_excel(out_file, index=False, sheet_name='Cobranzas')
    collected, billed = svc.get_totals_from_file(str(out_file))
    # collected should equal ves converted to USD via BCV = 121.4
    assert abs(collected - 121.4) < 0.01

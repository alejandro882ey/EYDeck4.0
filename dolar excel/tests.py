"""Unit tests for dolar excel utilities."""
from __future__ import annotations

# The package folder contains a space and isn't a valid import name. Import by path.
import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "utils.py"
spec = importlib.util.spec_from_file_location("dolar_excel_utils", str(MODULE_PATH))
utils = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = utils
spec.loader.exec_module(utils)


def test_parse_email_rates_basic():
    text = (
        "BCV: 158.9289 Bs/USD (Fecha: 2025-09-11T21:03:04.940Z)\n"
        "Paralelo: 240.95 Bs/USD (Fecha: 2025-09-11T21:03:08.360Z)"
    )
    data = utils.parse_email_rates(text)
    assert data is not None
    assert abs(data["bcv"] - 158.9289) < 1e-6
    assert abs(data["paralelo"] - 240.95) < 1e-6
    assert data["bcv_ts"].year == 2025


def test_parse_email_rates_missing():
    assert utils.parse_email_rates("") is None
    assert utils.parse_email_rates("no rates here") is None

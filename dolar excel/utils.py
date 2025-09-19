"""Helper utilities for parsing exchange rate emails and updating Excel rows.

Contains:
- parse_email_rates(text): extract BCV and Paralelo rates and ISO timestamps.
- normalize_rate(value_str): parse numeric rate like '158.9289' or '240.95'
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, Dict


EMAIL_RATE_REGEX = re.compile(
    r"BCV:\s*(?P<bcv>[0-9]+(?:\.[0-9]+)?)\s*Bs/USD\s*\(Fecha:\s*(?P<bcv_ts>[^)]+)\)" 
    r"[\s,;]*Paralelo:\s*(?P<paralelo>[0-9]+(?:\.[0-9]+)?)\s*Bs/USD\s*\(Fecha:\s*(?P<par_ts>[^)]+)\)",
    re.IGNORECASE,
)


def normalize_rate(value_str: str) -> float:
    """Convert rate string to float, stripping commas and spaces."""
    s = value_str.replace(",", "").strip()
    return float(s)


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parse an ISO-like timestamp. Falls back to common formats if needed."""
    # Try direct ISO parse
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        # Common fallback formats
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(dt_str, fmt)
            except Exception:
                continue
    raise ValueError(f"Unrecognized datetime format: {dt_str}")


def parse_email_rates(text: str) -> Optional[Dict[str, object]]:
    """Parse the email body text and return a dict with bcv, paralelo and timestamps.

    Example email body:
      BCV: 158.9289 Bs/USD (Fecha: 2025-09-11T21:03:04.940Z)
      Paralelo: 240.95 Bs/USD (Fecha: 2025-09-11T21:03:08.360Z)

    Returns None if pattern not found.
    """
    if not text:
        return None
    m = EMAIL_RATE_REGEX.search(text)
    if not m:
        return None

    bcv = normalize_rate(m.group("bcv"))
    paralelo = normalize_rate(m.group("paralelo"))
    bcv_ts = parse_iso_datetime(m.group("bcv_ts"))
    par_ts = parse_iso_datetime(m.group("par_ts"))

    return {
        "bcv": bcv,
        "paralelo": paralelo,
        "bcv_ts": bcv_ts,
        "paralelo_ts": par_ts,
    }

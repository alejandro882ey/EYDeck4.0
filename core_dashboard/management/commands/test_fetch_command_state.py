"""Tests for the fetch_exchange_emails command small helpers."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import json

cmd_path = Path(__file__).resolve().parent / "fetch_exchange_emails.py"
spec = importlib.util.spec_from_file_location("fetch_cmd", str(cmd_path))
cmd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmd)


def test_state_file_roundtrip(tmp_path):
    # Override the global STATE_FILE to a tmp file
    tmp_state = tmp_path / "state.json"
    cmd.STATE_FILE = str(tmp_state)
    state = cmd.load_state()
    assert isinstance(state, dict)
    state["processed_ids"] = ["a", "b"]
    cmd.save_state(state)
    with open(tmp_state, "r", encoding="utf-8") as fh:
        loaded = json.load(fh)
    assert loaded["processed_ids"] == ["a", "b"]

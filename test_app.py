"""
Basic offline test harness for the StyleVision Product Entry app.
Run with:
    pytest test_app.py
"""

import os
import csv
import datetime
import pandas as pd
from pathlib import Path

# Import functions from your main app (update module name if needed)
# For example, if your main file is named `stylevision_app.py`:
# from stylevision_app import generate_new_pid, dedup_buckets_row
# If everything is in the same folder and main file is `app.py`, use:
from app import generate_new_pid


# -----------------------
# Helper: Mock Data Setup
# -----------------------

def mock_base_row():
    return {
        "theme_color_pattern": "red, blue, cotton",
        "theme_fit": "slim, relaxed, cotton",
        "theme_fabric_care": "cotton, dry clean, hand wash"
    }


# -----------------------
# Test 1: Product ID format
# -----------------------

def test_generate_new_pid_format():
    pid = generate_new_pid()
    assert isinstance(pid, str)
    assert len(pid) == 11, f"Unexpected PID length: {pid}"
    assert pid[2] == "_", f"PID should contain underscore after year: {pid}"

    year_prefix = datetime.datetime.now().strftime("%y")
    assert pid.startswith(year_prefix), f"PID prefix mismatch: {pid}"


# -----------------------
# Test 2: Deduplication Logic
# -----------------------

def test_dedup_buckets_row_logic():
    from app import dedup_buckets_row

    row = mock_base_row()
    result = dedup_buckets_row(row)

    assert isinstance(result, pd.Series)
    assert "cotton" in result["theme_merged_fabric_care"]
    assert "red" in result["theme_merged_color_pattern"]
    assert "slim" in result["theme_merged_fit"]
    assert "cotton" not in result["theme_merged_color_pattern"], "Fabric should not appear in color bucket"


# -----------------------
# Test 3: CSV Writing
# -----------------------

def test_csv_write(tmp_path):
    test_csv = tmp_path / "test_products.csv"

    # Simulate a product entry
    test_data = {
        "p_id": "25_00000001",
        "name": "Test Product",
        "products": "shirt",
        "price": "99.99",
        "brand": "demo",
        "cold_start": 1,
        "rating_bucket": "no_rating",
        "img": "25_00000001.jpg",
        "theme_merged_color_pattern": "red, striped",
        "theme_merged_fit": "regular",
        "theme_merged_fabric_care": "cotton, hand wash",
        "formatted": "Colour: Red<br>Fabric: Cotton",
        "description_generated": "A test product for validation."
    }

    df = pd.DataFrame([test_data])
    df.to_csv(test_csv, mode="a", index=False)

    assert test_csv.exists()
    with open(test_csv, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["name"] == "Test Product"
        assert "formatted" in rows[0]


# -----------------------
# Test 4: Description Generation (Mock)
# -----------------------

def test_generate_description_mock(monkeypatch):
    from app import generate_description

    # Mock Ollama response to avoid API call
    def mock_chat(*args, **kwargs):
        return {"message": {"content": "Mocked description."}}

    monkeypatch.setattr("app.ollama.chat", mock_chat)

    desc = generate_description(
        ["Dress"], "Red", ["Floral"], "DemoBrand",
        ["Cotton"], ["Regular"], ["Button(s)"], ["Hand Wash"], ["Casual"]
    )

    assert "Mocked description" in desc
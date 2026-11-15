"""Mandi price history: official rows stored exactly, duplicates collapsed (no network)."""

from datetime import UTC, datetime

from app.live_data.market_history import crop_key, dedupe, to_rows

NOW = datetime(2026, 11, 14, tzinfo=UTC)


def test_history_and_daily_field_names_both_parse() -> None:
    history = {"State": "Telangana", "District": "Khammam", "Market": "Khammam APMC",
               "Commodity": "Cotton", "Variety": "Cotton (Unginned)", "Grade": "FAQ",
               "Arrival_Date": "12/11/2026", "Min_Price": 7500, "Max_Price": 8800,
               "Modal_Price": 8700}
    daily = {"state": "Telangana", "district": "Khammam", "market": "Khammam APMC",
             "commodity": "Paddy(Common)", "variety": "Other", "grade": "FAQ",
             "arrival_date": "13/11/2026", "min_price": "2200", "max_price": "",
             "modal_price": "2400"}
    no_modal = {**daily, "modal_price": ""}
    rows = to_rows([history, daily, no_modal], "r", NOW)
    assert len(rows) == 2  # a row without a modal price is never stored or filled in
    assert rows[0]["crop_canonical"] == "cotton" and rows[0]["modal_price"] == 8700
    assert rows[1]["crop_canonical"] == "paddy" and rows[1]["max_price"] is None
    assert crop_key("Bhindi(Ladies Finger)") is None or isinstance(crop_key("Bhindi"), str)


def test_repeated_official_rows_are_collapsed() -> None:
    rec = {"State": "Telangana", "District": "Jangaon", "Market": "Jangaon APMC",
           "Commodity": "Maize", "Variety": "Local", "Grade": "Local",
           "Arrival_Date": "13/11/2026", "Modal_Price": 3005}
    rows, repeats = dedupe(to_rows([rec, {**rec, "Modal_Price": 3010}], "r", NOW))
    assert repeats == 1 and len(rows) == 1 and rows[0]["modal_price"] == 3010  # last wins

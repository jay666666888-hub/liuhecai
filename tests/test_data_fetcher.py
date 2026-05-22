import pytest
import sys
sys.path.insert(0, "..")
from predictor.data_fetcher import (
    extract_zodiac_mapping,
    get_special_zodiac,
    get_special_number,
    validate_zodiac_mapping
)

def test_extract_zodiac_mapping():
    records = [
        {
            "expect": "2025001",
            "openCode": "25,18,06,14,29,39,22",
            "zodiac": "龍,豬,豬,兔,鼠,虎,羊"
        }
    ]
    mapping = extract_zodiac_mapping(records)
    assert mapping[25] == "龍"
    assert mapping[22] == "羊"


def test_get_special():
    record = {
        "expect": "2025001",
        "openCode": "25,18,06,14,29,39,22",
        "zodiac": "龍,豬,豬,兔,鼠,虎,羊"
    }
    assert get_special_number(record) == 22
    assert get_special_zodiac(record) == "羊"


def test_validate_mapping():
    records = [
        {
            "openCode": "25,18,06",
            "zodiac": "龍,豬,豬"
        }
    ]
    mapping = {25: "龍", 18: "豬", 6: "豬"}
    assert validate_zodiac_mapping(mapping, records) == 1.0
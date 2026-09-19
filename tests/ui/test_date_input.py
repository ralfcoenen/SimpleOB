from datetime import date

import pytest

from openbilanz.date_input import (
    parse_german_date,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("18.08.2026", date(2026, 8, 18)),
        ("18.08.26", date(2026, 8, 18)),
        ("18082026", date(2026, 8, 18)),
        ("180826", date(2026, 8, 18)),
    ),
)
def test_parse_german_date_accepts_common_formats(
    value: str,
    expected: date,
) -> None:
    assert parse_german_date(value) == expected


def test_parse_german_date_rejects_invalid_date() -> None:
    with pytest.raises(
        ValueError,
        match="Ungültiges Datum",
    ):
        parse_german_date(
            "31022026"
        )

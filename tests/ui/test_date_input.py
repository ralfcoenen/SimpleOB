from datetime import date

import pytest
from PySide6.QtWidgets import QApplication

from simpleob.date_input import (
    GermanDateEdit,
    format_german_date,
    normalize_german_date,
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


def test_two_digit_year_interpretation_remains_in_2000s() -> None:
    assert parse_german_date("01.02.26") == date(2026, 2, 1)
    assert parse_german_date("010226") == date(2026, 2, 1)


def test_german_date_helpers_normalize_short_day_and_month() -> None:
    assert normalize_german_date("1.2.2026") == "01.02.2026"
    assert format_german_date(date(2026, 2, 1)) == "01.02.2026"


def test_german_date_edit_normalizes_on_finish_and_read() -> None:
    app = QApplication.instance() or QApplication([])
    field = GermanDateEdit()
    field.setText("1.2.2026")

    field.editingFinished.emit()

    assert field.text() == "01.02.2026"
    assert field.date_value() == date(2026, 2, 1)
    assert field.text() == "01.02.2026"
    field.close()
    app.processEvents()


def test_german_date_edit_rejects_invalid_calendar_date() -> None:
    app = QApplication.instance() or QApplication([])
    field = GermanDateEdit()
    field.setText("31.02.2026")

    with pytest.raises(ValueError, match="Ungültiges Datum"):
        field.date_value()

    assert field.text() == "31.02.2026"
    field.close()
    app.processEvents()


def test_german_date_edit_distinguishes_optional_empty_value() -> None:
    app = QApplication.instance() or QApplication([])
    optional_field = GermanDateEdit(optional=True)
    required_field = GermanDateEdit()

    assert optional_field.date_value() is None
    with pytest.raises(ValueError, match="darf nicht leer sein"):
        required_field.date_value()

    optional_field.set_date(None)
    assert optional_field.text() == ""
    optional_field.close()
    required_field.close()
    app.processEvents()

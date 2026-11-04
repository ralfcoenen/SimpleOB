from datetime import date
from decimal import Decimal
from uuid import uuid4

from PySide6.QtWidgets import QApplication

from simpleob.domain.kr_settings import KrAnnualTurnoverAddition, KrSettings
from simpleob.ui_qt.kr_settings_dialog import KrSettingsDialog


def test_dialog_saves_calendar_year_amounts_and_preserves_older_years():
    app = QApplication.instance() or QApplication([])
    company_id = uuid4()
    dialog = KrSettingsDialog(
        None,
        settings=KrSettings(
            company_id=company_id,
            activity_start_date=date(2020, 1, 1),
            external_turnovers=(
                KrAnnualTurnoverAddition(2024, Decimal("123.45")),
                KrAnnualTurnoverAddition(2025, Decimal("200.00")),
            ),
        ),
        today=date(2026, 6, 1),
    )
    try:
        assert set(dialog._turnover_entries) == {2024, 2025, 2026}
        dialog._turnover_entries[2024].setText("150,25")
        dialog._turnover_entries[2025].setText("200,00")
        dialog._turnover_entries[2026].setText("300,75")
        dialog._save()

        assert dialog.result is not None
        assert dialog.result.external_turnover_for(2024) == Decimal("150.25")
        assert dialog.result.external_turnover_for(2025) == Decimal("200.00")
        assert dialog.result.external_turnover_for(2026) == Decimal("300.75")
        assert dialog.result.company_id == company_id
    finally:
        dialog.close()
        app.processEvents()

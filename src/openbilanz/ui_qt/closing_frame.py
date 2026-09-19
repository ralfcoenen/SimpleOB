"""PySide6-Darstellung und Bedienung des Jahresabschlusses."""

from collections.abc import Callable
from decimal import Decimal

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.closing_consistency_result import (
    ClosingConsistencyResult,
)
from openbilanz.domain.fiscal_year_status import FiscalYearStatus


class ClosingFrame(QWidget):
    """Stellt Status und Aktionen des Jahresabschlusses dar."""

    def __init__(
        self,
        *,
        on_validate: Callable[[], None],
        on_close: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._on_validate = on_validate
        self._on_close = on_close

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)

        title_label = QLabel("Jahresabschluss")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        self._fiscal_year_status_label = QLabel(
            "Geschäftsjahr: Offen"
        )
        self._fiscal_year_status_label.setStyleSheet(
            "font-size: 14px; font-weight: bold;"
        )
        layout.addWidget(self._fiscal_year_status_label)

        self._result_label = QLabel(
            "Jahresergebnis: noch nicht ermittelt"
        )
        layout.addWidget(self._result_label)

        consistency_title = QLabel("Plausibilitätsprüfung")
        consistency_title.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
        )
        layout.addWidget(consistency_title)

        self._consistency_status_label = QLabel(
            "Noch nicht geprüft."
        )
        layout.addWidget(self._consistency_status_label)

        self._errors = QListWidget()
        layout.addWidget(self._errors, 1)

        buttons_layout = QHBoxLayout()

        self._validate_button = QPushButton(
            "Abschluss prüfen"
        )
        self._validate_button.clicked.connect(
            self._on_validate
        )
        buttons_layout.addWidget(self._validate_button)

        self._close_button = QPushButton(
            "Geschäftsjahr abschließen"
        )
        self._close_button.clicked.connect(
            self._on_close
        )
        self._close_button.setEnabled(False)
        buttons_layout.addWidget(self._close_button)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

    def update_fiscal_year_status(
        self,
        status: FiscalYearStatus,
    ) -> None:
        """Aktualisiert den Status des Geschäftsjahres."""

        if status is FiscalYearStatus.OPEN:
            text = "Geschäftsjahr: Offen"
            self._validate_button.setEnabled(True)
            self._close_button.setEnabled(False)
        else:
            text = "Geschäftsjahr: Abgeschlossen"
            self._validate_button.setEnabled(False)
            self._close_button.setEnabled(False)

        self._fiscal_year_status_label.setText(text)

    def update_net_income(
        self,
        net_income: Decimal,
    ) -> None:
        """Aktualisiert das angezeigte Jahresergebnis."""

        if net_income > Decimal("0.00"):
            description = "Jahresüberschuss"
        elif net_income < Decimal("0.00"):
            description = "Jahresfehlbetrag"
        else:
            description = "Jahresergebnis"

        self._result_label.setText(
            f"{description}: "
            f"{self._format_amount(net_income)} €"
        )

    def update_consistency(
        self,
        result: ClosingConsistencyResult,
    ) -> None:
        """Zeigt das Ergebnis der Abschlussprüfung."""

        self._errors.clear()

        if result.is_consistent:
            self._consistency_status_label.setText(
                "Plausibilitätsprüfung erfolgreich."
            )
            self._close_button.setEnabled(True)
            return

        self._consistency_status_label.setText(
            "Plausibilitätsprüfung fehlgeschlagen."
        )
        self._close_button.setEnabled(False)

        for error in result.errors:
            self._errors.addItem(error)

    def mark_closed(self) -> None:
        """Stellt den Abschlusszustand in der Oberfläche dar."""

        self.update_fiscal_year_status(
            FiscalYearStatus.CLOSED
        )

        self._consistency_status_label.setText(
            "Geschäftsjahr wurde abgeschlossen."
        )

    @staticmethod
    def _format_amount(
        amount: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag deutsch."""

        formatted = f"{amount:,.2f}"

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

"""Buchungserfassung der PySide6-Oberfläche."""

from collections.abc import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.account import Account
from openbilanz.domain.booking import Booking
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.ui_qt.simple_booking_widget import (
    SimpleBookingWidget,
)
from openbilanz.ui_qt.vat_booking_widget import (
    VatBookingWidget,
)


class BookingPage(QWidget):
    """Arbeitsbereich für laufende Buchungen."""

    def __init__(
        self,
        *,
        accounts: tuple[Account, ...],
        vat_accounts: VatAccounts,
        on_booking_created: Callable[[Booking], None],
        enabled: bool,
    ) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Neue Buchung")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        self._mode_box = QComboBox()
        self._mode_box.addItems(
            (
                "Einfache Buchung",
                "Rechnung mit Umsatzsteuer",
            )
        )

        layout.addWidget(self._mode_box)

        self._stack = QStackedWidget()

        self._simple_booking = SimpleBookingWidget(
            accounts=accounts,
            on_booking_created=on_booking_created,
        )

        self._vat_booking = VatBookingWidget(
            accounts=accounts,
            vat_accounts=vat_accounts,
            on_booking_created=on_booking_created,
        )

        self._stack.addWidget(
            self._simple_booking
        )
        self._stack.addWidget(
            self._vat_booking
        )

        layout.addWidget(self._stack)
        layout.addStretch()

        self._mode_box.currentIndexChanged.connect(
            self._stack.setCurrentIndex
        )

        self.set_enabled(enabled)

    def set_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Aktiviert oder sperrt beide Buchungsarten."""

        self._mode_box.setEnabled(enabled)

        self._simple_booking.set_enabled(
            enabled
        )
        self._vat_booking.set_enabled(
            enabled
        )

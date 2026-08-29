"""Buchungserfassung der PySide6-Oberfläche."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

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
from openbilanz.domain.vat_booking_detail import (
    VatBookingDetail,
)
from openbilanz.domain.vat_configuration import (
    VatConfiguration,
)
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue_kind import VatRevenueKind
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
        vat_configuration: VatConfiguration,
        on_booking_created: Callable[[Booking], None],
        on_vat_booking_created: Callable[
            [Booking, tuple[VatBookingDetail, ...]],
            None,
        ],
        on_vat_revenue_created: Callable[
            [
                Booking,
                tuple[VatBookingDetail, ...],
                Decimal,
                VatRevenueKind,
                VatPaymentKind,
                date,
            ],
            None,
        ],
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
            vat_configuration=vat_configuration,
            on_vat_booking_created=(
                on_vat_booking_created
            ),
            on_vat_revenue_created=(
                on_vat_revenue_created
            ),
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

    def set_vat_configuration(
        self,
        configuration: VatConfiguration,
    ) -> None:
        """Aktualisiert die umsatzsteuerliche Behandlung."""

        self._vat_booking.set_vat_configuration(
            configuration
        )

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

    def set_vat_accounts(
        self,
        vat_accounts: VatAccounts,
    ) -> None:
        """Aktualisiert die Umsatzsteuerkonten."""

        self._vat_booking.set_vat_accounts(
            vat_accounts
        )

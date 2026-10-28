"""Dialog für die vollständige Rücknahme einer Guthabenrückerstattung."""

from datetime import date
from uuid import UUID

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
)

from simpleob.amount_input import format_german_amount
from simpleob.date_input import format_german_date, parse_german_date
from simpleob.domain.open_item_credit_refund_reversal import (
    OpenItemCreditRefundReversalCandidate,
)
from simpleob.domain.open_item_offset import OffsetDirection
from simpleob.services.open_item_credit_refund_reversal_service import (
    OpenItemCreditRefundReversalService,
)


class OpenItemCreditRefundReversalDialog(QDialog):
    """Erfasst eine bestätigte vollständige OP-Rücknahme."""

    def __init__(
        self,
        parent,
        *,
        company_id: UUID,
        fiscal_year,
        service: OpenItemCreditRefundReversalService,
    ) -> None:
        super().__init__(parent)
        self._company_id = company_id
        self._fiscal_year = fiscal_year
        self._service = service
        self._candidates = service.list_candidates(
            company_id=company_id,
            fiscal_year=fiscal_year,
        )
        self._candidate_by_id = {
            str(candidate.refund_id): candidate for candidate in self._candidates
        }
        self.setWindowTitle("Guthabenrückerstattung zurücknehmen")
        self.resize(760, 470)
        self.setMinimumWidth(700)

        self._direction_box = QComboBox()
        self._direction_box.addItem("Kundenguthaben", OffsetDirection.CUSTOMER.value)
        self._direction_box.addItem("Lieferantenguthaben", OffsetDirection.SUPPLIER.value)
        self._partner_box = QComboBox()
        self._partner_box.setMinimumContentsLength(30)
        self._refund_box = QComboBox()
        self._refund_box.setMinimumContentsLength(34)
        self._refund_box.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self._amount = QLineEdit()
        self._amount.setReadOnly(True)
        self._amount.setMinimumWidth(280)
        self._refund_booking_date = QLineEdit()
        self._refund_booking_date.setReadOnly(True)
        self._refund_booking_date.setMinimumWidth(280)
        self._existing_reversal = QLabel("Keine Journalgegenbuchung gefunden.")
        self._return_booking_date = QLineEdit(format_german_date(date.today()))
        self._date_error = QLabel()
        self._date_error.setWordWrap(True)
        self._reason = QLineEdit()
        self._reason.setPlaceholderText("Erforderlicher Rücknahmegrund")
        self._reason.setMinimumWidth(420)
        self._scenario = QLabel()
        self._scenario.setWordWrap(True)
        self._scenario.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        self._scenario.setMinimumWidth(420)

        form = QFormLayout()
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.addRow("Guthabenart", self._direction_box)
        form.addRow("Geschäftspartner", self._partner_box)
        form.addRow("Guthabenrückerstattung", self._refund_box)
        form.addRow("Rückerstattungsbetrag", self._amount)
        form.addRow("Ursprüngliches Buchungsdatum", self._refund_booking_date)
        form.addRow("Journalgegenbuchung", self._existing_reversal)
        form.addRow("Rücknahme-Buchungsdatum", self._return_booking_date)
        form.addRow("", self._date_error)
        form.addRow("Rücknahmegrund (erforderlich)", self._reason)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._reverse)
        buttons.rejected.connect(self.reject)
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Vorgehen"))
        layout.addWidget(self._scenario)
        layout.addWidget(buttons)

        self._direction_box.currentIndexChanged.connect(self._refresh_partners)
        self._partner_box.currentIndexChanged.connect(self._refresh_refunds)
        self._refund_box.currentIndexChanged.connect(self._refresh_selection)
        self._reason.textChanged.connect(self._update_submit_state)
        self._return_booking_date.textChanged.connect(self._update_submit_state)
        self._refresh_partners()

    def _refresh_partners(self, *_args: object) -> None:
        direction = OffsetDirection(self._direction_box.currentData())
        matching = [
            candidate
            for candidate in self._candidates
            if candidate.direction is direction
        ]
        partner_names: dict[str, tuple[UUID, str]] = {}
        for candidate in matching:
            partner_names.setdefault(
                str(candidate.partner_id),
                (candidate.partner_id, candidate.partner_name),
            )
        self._partner_box.blockSignals(True)
        self._partner_box.clear()
        for partner_id, name in partner_names.values():
            self._partner_box.addItem(name, str(partner_id))
        self._partner_box.blockSignals(False)
        self._refresh_refunds()

    def _refresh_refunds(self, *_args: object) -> None:
        self._refund_box.blockSignals(True)
        self._refund_box.clear()
        partner_id = self._partner_box.currentData()
        direction = OffsetDirection(self._direction_box.currentData())
        if partner_id is not None:
            for candidate in self._candidates:
                if (
                    candidate.direction is direction
                    and str(candidate.partner_id) == str(partner_id)
                ):
                    self._refund_box.addItem(
                        self._candidate_label(candidate),
                        str(candidate.refund_id),
                    )
        self._refund_box.blockSignals(False)
        self._refresh_selection()

    @staticmethod
    def _candidate_label(candidate: OpenItemCreditRefundReversalCandidate) -> str:
        return (
            f"{format_german_date(candidate.booking_date)} · "
            f"{format_german_amount(candidate.amount)} €"
        )

    def _selected_candidate(self) -> OpenItemCreditRefundReversalCandidate | None:
        refund_id = self._refund_box.currentData()
        if refund_id is None:
            return None
        return self._candidate_by_id.get(str(refund_id))

    def _refresh_selection(self, *_args: object) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            self._amount.clear()
            self._refund_booking_date.clear()
            self._existing_reversal.setText("Keine Journalgegenbuchung gefunden.")
            self._scenario.clear()
            self._return_booking_date.setReadOnly(False)
            self._update_submit_state()
            return

        self._amount.setText(f"{format_german_amount(candidate.amount)} EUR")
        self._refund_booking_date.setText(format_german_date(candidate.booking_date))
        if candidate.journal_reversal_count == 0:
            self._existing_reversal.setText("Keine vorhanden.")
            self._return_booking_date.setReadOnly(False)
            try:
                proposed_date = parse_german_date(self._return_booking_date.text())
            except ValueError:
                proposed_date = date.today()
            if proposed_date < candidate.booking_date:
                self._return_booking_date.setText(
                    format_german_date(candidate.booking_date)
                )
            self._scenario.setText(
                "Es wird eine Hauptbuchgegenbuchung zur ursprünglichen "
                "Rückerstattung und ein OP-Rücknahmeereignis erzeugt."
            )
        elif candidate.journal_reversal_count == 1:
            self._existing_reversal.setText(
                "Bereits im Journal storniert · "
                f"{format_german_date(candidate.journal_reversal_booking_date)}"
            )
            self._return_booking_date.setText(
                format_german_date(candidate.journal_reversal_booking_date)
            )
            self._return_booking_date.setReadOnly(True)
            self._scenario.setText(
                "Die Rückerstattung wurde bereits im Journal storniert. "
                "Es wird ausschließlich die fehlende OP-Rücknahme ergänzt; "
                "es entsteht keine weitere Hauptbuchgegenbuchung."
            )
        else:
            self._existing_reversal.setText(
                f"Ungültig: {candidate.journal_reversal_count} Gegenbuchungen gefunden."
            )
            self._return_booking_date.setReadOnly(True)
            self._scenario.setText(
                "Die vorhandenen Buchungsreferenzen sind mehrdeutig. "
                "Die Rücknahme kann nicht aus diesem Dialog ausgeführt werden."
            )
        self._update_submit_state()

    def _update_submit_state(self, *_args: object) -> None:
        candidate = self._selected_candidate()
        date_error = ""
        try:
            effective_date = parse_german_date(self._return_booking_date.text())
            valid_date = True
        except ValueError:
            valid_date = False
            effective_date = None
            date_error = "Bitte ein gültiges Rücknahmebuchungsdatum eingeben."
        if candidate is not None and candidate.journal_reversal_count == 1:
            reversal_date = candidate.journal_reversal_booking_date
            if reversal_date is None:
                valid_date = False
                date_error = "Das Buchungsdatum der vorhandenen Journalgegenbuchung fehlt."
            elif reversal_date < candidate.booking_date:
                valid_date = False
                date_error = (
                    "Das Datum der vorhandenen Journalgegenbuchung darf nicht vor "
                    "dem Buchungsdatum der ursprünglichen Rückerstattung liegen."
                )
            elif effective_date != reversal_date:
                valid_date = False
                date_error = (
                    "Das Rücknahmebuchungsdatum muss dem Datum der vorhandenen "
                    "Journalgegenbuchung entsprechen."
                )
        elif (
            candidate is not None
            and effective_date is not None
            and effective_date < candidate.booking_date
        ):
            valid_date = False
            date_error = (
                "Das Rücknahmebuchungsdatum darf nicht vor dem Buchungsdatum der "
                f"ursprünglichen Rückerstattung ({format_german_date(candidate.booking_date)}) liegen."
            )
        self._date_error.setText(date_error)
        self._ok_button.setEnabled(
            candidate is not None
            and candidate.journal_reversal_count in (0, 1)
            and bool(self._reason.text().strip())
            and valid_date
        )

    def _reverse(self) -> None:
        try:
            candidate = self._selected_candidate()
            if candidate is None:
                raise ValueError("Bitte eine vorhandene Rückerstattung auswählen.")
            if candidate.journal_reversal_count not in (0, 1):
                raise ValueError("Die Journalgegenbuchung ist nicht eindeutig.")
            reason = self._reason.text().strip()
            if not reason:
                raise ValueError("Ein Rücknahmegrund ist erforderlich.")
            self._update_submit_state()
            if not self._ok_button.isEnabled():
                raise ValueError(
                    self._date_error.text()
                    or "Das Rücknahmebuchungsdatum ist nicht zulässig."
                )
            booking_date = parse_german_date(self._return_booking_date.text())
            scenario = (
                "Die Rücknahme erzeugt eine Hauptbuchgegenbuchung und ein OP-Rücknahmeereignis."
                if candidate.journal_reversal_count == 0
                else "Die Journalgegenbuchung ist bereits vorhanden. Es wird nur die OP-Rücknahme ergänzt."
            )
            confirmation = QMessageBox.question(
                self,
                "Rücknahme bestätigen",
                f"{scenario}\n\n"
                f"Geschäftspartner: {candidate.partner_name}\n"
                f"Rückerstattung: {format_german_amount(candidate.amount)} EUR\n"
                f"Ursprüngliche Buchung: {format_german_date(candidate.booking_date)}\n"
                f"Rücknahmebuchung: {format_german_date(booking_date)}\n"
                f"Grund: {reason}\n\n"
                "Die ursprüngliche Rückerstattung bleibt unverändert erhalten.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmation != QMessageBox.StandardButton.Yes:
                return
            self._service.reverse_refund(
                company_id=self._company_id,
                fiscal_year=self._fiscal_year,
                refund_id=candidate.refund_id,
                reason=reason,
                booking_date=booking_date,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Rücknahme nicht gespeichert", str(exc))
            return
        self.accept()

"""Dialog für eine manuelle Korrektur einer Zahlungszuordnung."""

from datetime import date
from uuid import UUID

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from simpleob.amount_input import parse_german_amount
from simpleob.date_input import parse_german_date
from simpleob.services.payment_allocation_correction_service import (
    PaymentAllocationCorrectionService,
)


class PaymentAllocationCorrectionDialog(QDialog):
    def __init__(self, parent, *, company_id: UUID, fiscal_year, service: PaymentAllocationCorrectionService) -> None:
        super().__init__(parent)
        self._company_id, self._fiscal_year, self._service = company_id, fiscal_year, service
        self.setWindowTitle("Zahlungszuordnung korrigieren")
        self.resize(680, 300)
        form = QFormLayout()
        self._source = QComboBox()
        self._target = QComboBox()
        self._amount = QLineEdit()
        today = date.today().strftime("%d.%m.%Y")
        self._correction_date = QLineEdit(today)
        self._booking_date = QLineEdit(today)
        self._reason = QLineEdit()
        form.addRow("Ursprüngliche Zuordnung", self._source)
        form.addRow("Zielrechnung", self._target)
        form.addRow("Korrekturbetrag", self._amount)
        form.addRow("Korrekturdatum", self._correction_date)
        form.addRow("Buchungsdatum", self._booking_date)
        form.addRow("Begründung (erforderlich)", self._reason)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._correct)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        for allocation in service.list_correctable_allocations(company_id):
            self._source.addItem(
                f"{allocation.direction.value} · {allocation.source_document_number} · "
                f"Zahlung {allocation.payment_date:%d.%m.%Y} · ID {str(allocation.payment_id)[:8]} · "
                f"korrigierbar {allocation.correctable_amount:.2f} EUR",
                str(allocation.original_event_id),
            )
        self._source.currentIndexChanged.connect(self._refresh_targets)
        self._refresh_targets()

    def _refresh_targets(self, *_args) -> None:
        self._target.clear()
        event_id = self._source.currentData()
        if event_id is None:
            return
        source = next((item for item in self._service.list_correctable_allocations(self._company_id)
                       if str(item.original_event_id) == str(event_id)), None)
        if source is None:
            return
        for invoice in self._service.list_open_targets(
            company_id=self._company_id, partner_id=source.partner_id, direction=source.direction
        ):
            if invoice.open_item_id != source.source_open_item_id:
                self._target.addItem(
                    f"{invoice.document_number} · offen {invoice.open_amount:.2f} EUR",
                    str(invoice.open_item_id),
                )

    def _correct(self) -> None:
        try:
            event_id, target_id = self._source.currentData(), self._target.currentData()
            if event_id is None or target_id is None:
                raise ValueError("Bitte eine Zuordnung und eine Zielrechnung auswählen.")
            amount = parse_german_amount(self._amount.text())
            reason = self._reason.text().strip()
            if not reason:
                raise ValueError("Eine Begründung ist erforderlich.")
            confirmation = QMessageBox.question(
                self, "Korrektur bestätigen",
                f"{amount:.2f} EUR auf die ausgewählte Zielrechnung übertragen?\n\n"
                "Die ursprüngliche Zahlung bleibt unverändert. Es entsteht keine Bank- oder Kassenbewegung.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmation != QMessageBox.StandardButton.Yes:
                return
            self._service.correct(
                company_id=self._company_id, fiscal_year=self._fiscal_year,
                original_event_id=UUID(str(event_id)), target_open_item_id=UUID(str(target_id)),
                amount=amount, correction_date=parse_german_date(self._correction_date.text()),
                booking_date=parse_german_date(self._booking_date.text()), reason=reason, confirmed=True,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Korrektur nicht gespeichert", str(exc))
            return
        self.accept()

"""Persistenz und Zulassungsprüfung für Guthabenrückerstattungen."""

from sqlalchemy.orm import Session

from simpleob.database.models import (
    Buchung,
    Geschaeftspartner,
    Mandant,
    Wirtschaftsjahr,
)
from simpleob.database.models import (
    GuthabenOPRueckerstattung as GuthabenOPRueckerstattungModel,
)
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.open_item_credit_refund import OpenItemCreditRefund
from simpleob.domain.open_item_offset import OffsetDirection


class OpenItemCreditRefundRepository:
    """Speichert eine unveränderliche Rückerstattung je Guthabenbewegung."""

    def __init__(
        self,
        session: Session,
        *,
        offset_repository: OpenItemOffsetRepository | None = None,
    ) -> None:
        self._session = session
        self._offset_repository = offset_repository or OpenItemOffsetRepository(session)

    def add(
        self,
        *,
        refund: OpenItemCreditRefund,
        fiscal_year: FiscalYear,
        commit: bool = True,
    ) -> None:
        if not isinstance(refund, OpenItemCreditRefund):
            raise TypeError("refund must be an OpenItemCreditRefund")
        self._offset_repository.reserve_credit_mutation()

        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(refund.company_id))
            .one_or_none()
        )
        if company is None:
            raise ValueError("Der Mandant wurde nicht gefunden.")
        year = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id == company.id,
                Wirtschaftsjahr.start_date == fiscal_year.start_date,
                Wirtschaftsjahr.end_date == fiscal_year.end_date,
            )
            .one_or_none()
        )
        if year is None:
            raise ValueError("Das Geschäftsjahr gehört nicht zum Mandanten.")
        if year.status != FiscalYearStatus.OPEN.value:
            raise ValueError("Das Geschäftsjahr ist nicht offen.")
        if self._session.query(GuthabenOPRueckerstattungModel.id).filter(
            GuthabenOPRueckerstattungModel.refund_id == str(refund.refund_id)
        ).one_or_none():
            raise ValueError("Die Rückerstattungs-ID ist bereits vorhanden.")
        if self._session.query(GuthabenOPRueckerstattungModel.id).filter(
            GuthabenOPRueckerstattungModel.booking_id == str(refund.booking_id)
        ).one_or_none():
            raise ValueError("Für diese Hauptbuchbuchung existiert bereits eine Rückerstattung.")

        credit = self._offset_repository.get_credit(
            company_id=refund.company_id,
            partner_id=refund.partner_id,
            open_item_id=refund.open_item_id,
            direction=refund.direction,
            for_update=True,
        )
        if credit is None:
            raise ValueError("Der Guthaben-OP ist nicht vorhanden.")
        if refund.amount > credit.available_amount:
            raise ValueError("Der Rückerstattungsbetrag übersteigt das verfügbare Guthaben.")
        if credit.origin_booking_date is None:
            raise ValueError("Das Buchungsdatum der Guthabenentstehung ist nicht feststellbar.")

        booking = (
            self._session.query(Buchung)
            .filter(
                Buchung.booking_id == str(refund.booking_id),
                Buchung.wirtschaftsjahr_id == year.id,
            )
            .one_or_none()
        )
        if booking is None:
            raise ValueError("Die Rückerstattungsbuchung fehlt oder gehört zu einem anderen Geschäftsjahr.")
        if booking.booking_date < credit.origin_booking_date:
            raise ValueError(
                "Das Buchungsdatum der Rückerstattung darf nicht vor dem "
                f"Entstehungsdatum des Guthabens ({credit.origin_booking_date:%d.%m.%Y}) liegen."
            )
        if booking.booking_date < fiscal_year.start_date or booking.booking_date > fiscal_year.end_date:
            raise ValueError("Das Buchungsdatum liegt außerhalb des Geschäftsjahrs.")

        partner_role = (
            Geschaeftspartner.is_customer
            if refund.direction is OffsetDirection.CUSTOMER
            else Geschaeftspartner.is_supplier
        )
        if not self._session.query(Geschaeftspartner.id).filter(
            Geschaeftspartner.mandant_id == company.id,
            Geschaeftspartner.partner_id == str(refund.partner_id),
            partner_role.is_(True),
        ).one_or_none():
            raise ValueError("Der Geschäftspartner gehört nicht zum Mandanten oder hat nicht die passende Rolle.")

        control_side = (
            EntrySide.DEBIT
            if refund.direction is OffsetDirection.CUSTOMER
            else EntrySide.CREDIT
        )
        matching_control_lines = [
            line
            for line in booking.zeilen
            if line.account_number == credit.account_number
            and line.side == control_side.value
        ]
        other_lines = [line for line in booking.zeilen if line not in matching_control_lines]
        cash_side = (
            EntrySide.CREDIT
            if refund.direction is OffsetDirection.CUSTOMER
            else EntrySide.DEBIT
        )
        if (
            len(booking.zeilen) != 2
            or len(matching_control_lines) != 1
            or matching_control_lines[0].amount != refund.amount
            or len(other_lines) != 1
            or other_lines[0].side != cash_side.value
            or other_lines[0].amount != refund.amount
        ):
            raise ValueError("Die Hauptbuchbuchung entspricht nicht der Rückerstattung des Guthaben-OPs.")

        self._session.add(
            GuthabenOPRueckerstattungModel(
                refund_id=str(refund.refund_id),
                mandant_id=company.id,
                partner_id=str(refund.partner_id),
                open_item_id=str(refund.open_item_id),
                direction=refund.direction.value,
                amount=refund.amount,
                refund_date=refund.refund_date,
                booking_id=str(refund.booking_id),
                recorded_at=refund.recorded_at,
            )
        )
        self._session.flush()
        if commit:
            self._session.commit()

"""Atomare Persistenz für die Rücknahme einer Guthabenrückerstattung."""

from collections import Counter
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.models import (
    Buchung,
    Buchungszeile,
    Geschaeftspartner,
    GuthabenOPRueckerstattung,
    GuthabenOPRueckerstattungsruecknahme,
    Konto,
    Mandant,
    Wirtschaftsjahr,
)
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
from simpleob.domain.booking import Booking as BookingDomain
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.open_item_credit_refund_reversal import (
    OpenItemCreditRefundReversal,
    OpenItemCreditRefundReversalCandidate,
)
from simpleob.domain.open_item_offset import OffsetDirection


class OpenItemCreditRefundReversalRepository:
    """Validiert Rücknahmen und speichert sie mit der maßgeblichen Gegenbuchung."""

    def __init__(
        self,
        *,
        session: Session,
        booking_repository: BookingRepository,
        offset_repository: OpenItemOffsetRepository,
    ) -> None:
        self._session = session
        self._booking_repository = booking_repository
        self._offset_repository = offset_repository

    def list_candidates(
        self, *, company_id: UUID, fiscal_year: FiscalYear
    ) -> tuple[OpenItemCreditRefundReversalCandidate, ...]:
        """Listet nicht zurückgenommene Erstattungen des ausgewählten Jahres."""
        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )
        if company is None:
            return ()
        rows = (
            self._session.query(GuthabenOPRueckerstattung, Geschaeftspartner, Buchung)
            .join(
                Geschaeftspartner,
                (Geschaeftspartner.mandant_id == GuthabenOPRueckerstattung.mandant_id)
                & (Geschaeftspartner.partner_id == GuthabenOPRueckerstattung.partner_id),
            )
            .join(Buchung, GuthabenOPRueckerstattung.booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(
                GuthabenOPRueckerstattung.mandant_id == company.id,
                Wirtschaftsjahr.mandant_id == company.id,
                Wirtschaftsjahr.start_date == fiscal_year.start_date,
                Wirtschaftsjahr.end_date == fiscal_year.end_date,
                ~GuthabenOPRueckerstattung.refund_id.in_(
                    self._session.query(
                        GuthabenOPRueckerstattungsruecknahme.refund_id
                    )
                ),
            )
            .order_by(Geschaeftspartner.name, Buchung.booking_date, GuthabenOPRueckerstattung.recorded_at)
            .all()
        )
        candidates = []
        for refund, partner, booking in rows:
            reversals = (
                self._session.query(Buchung)
                .filter(Buchung.reversal_of_booking_id == booking.booking_id)
                .order_by(Buchung.booking_date, Buchung.booking_id)
                .all()
            )
            existing = reversals[0] if len(reversals) == 1 else None
            candidates.append(
                OpenItemCreditRefundReversalCandidate(
                    refund_id=UUID(refund.refund_id),
                    partner_id=UUID(refund.partner_id),
                    partner_name=partner.name,
                    direction=OffsetDirection(refund.direction),
                    amount=refund.amount,
                    refund_date=refund.refund_date,
                    booking_date=booking.booking_date,
                    original_booking_id=UUID(booking.booking_id),
                    original_voucher_no=booking.voucher_no,
                    journal_reversal_count=len(reversals),
                    journal_reversal_booking_id=(
                        UUID(existing.booking_id) if existing is not None else None
                    ),
                    journal_reversal_booking_date=(
                        existing.booking_date if existing is not None else None
                    ),
                )
            )
        return tuple(candidates)

    def reverse_refund(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        refund_id: UUID,
        reason: str,
        booking_date: date | None,
    ) -> OpenItemCreditRefundReversal:
        """Nimmt eine Rückerstattung vollständig zurück.

        Der spezialisierte Schreibpfad ist die einzige Freigabe für eine
        Gegenbuchung der durch das allgemeine Journal geschützten Rückerstattung.
        """
        try:
            if not isinstance(company_id, UUID) or not isinstance(refund_id, UUID):
                raise TypeError("Mandant und Rückerstattung müssen UUIDs sein.")
            if not isinstance(fiscal_year, FiscalYear):
                raise TypeError("fiscal_year must be a FiscalYear")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("Der Rücknahmegrund darf nicht leer sein.")
            if booking_date is not None and not isinstance(booking_date, date):
                raise TypeError("Das Buchungsdatum muss ein Datum sein.")

            # SQLite benötigt die Schreibreservierung vor jedem OP-Lesezugriff.
            self._offset_repository.reserve_credit_mutation()
            company = (
                self._session.query(Mandant)
                .filter(Mandant.company_id == str(company_id))
                .one_or_none()
            )
            if company is None:
                raise ValueError("Der geöffnete Mandant wurde nicht gefunden.")

            # Die erste Lesung ermittelt nur den zu sperrenden Guthaben-OP.
            refund_ref = (
                self._session.query(GuthabenOPRueckerstattung)
                .filter(GuthabenOPRueckerstattung.refund_id == str(refund_id))
                .one_or_none()
            )
            if refund_ref is None:
                raise ValueError("Die Guthabenrückerstattung wurde nicht gefunden.")
            if refund_ref.mandant_id != company.id:
                raise ValueError("Die Guthabenrückerstattung gehört zu einem anderen Mandanten.")

            direction = OffsetDirection(refund_ref.direction)
            credit = self._offset_repository.get_credit(
                company_id=company_id,
                partner_id=UUID(refund_ref.partner_id),
                open_item_id=UUID(refund_ref.open_item_id),
                direction=direction,
                for_update=True,
            )
            if credit is None:
                raise ValueError("Der Guthaben-OP der Rückerstattung fehlt.")

            # Gleiche Sperrreihenfolge wie bei Guthabenverrechnungen und
            # Rückerstattungen: Guthaben-OP, danach Geschäftsjahr.
            original_year = self._booking_repository.require_open_fiscal_year(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking_date=fiscal_year.start_date,
                for_update=True,
            )

            refund = (
                self._session.query(GuthabenOPRueckerstattung)
                .filter(GuthabenOPRueckerstattung.refund_id == str(refund_id))
                .with_for_update()
                .populate_existing()
                .one_or_none()
            )
            if refund is None or refund.mandant_id != company.id:
                raise ValueError("Die Guthabenrückerstattung gehört nicht zum geöffneten Mandanten.")
            if refund.partner_id != str(credit.partner_id) or refund.open_item_id != str(credit.open_item_id):
                raise ValueError("Die Rückerstattung und der Guthaben-OP sind nicht konsistent.")
            if self._session.query(
                GuthabenOPRueckerstattungsruecknahme.id
            ).filter(
                GuthabenOPRueckerstattungsruecknahme.refund_id == str(refund_id)
            ).one_or_none():
                raise ValueError("Diese Guthabenrückerstattung wurde bereits zurückgenommen.")

            source = (
                self._session.query(Buchung, Wirtschaftsjahr)
                .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
                .filter(Buchung.booking_id == refund.booking_id)
                .with_for_update(of=Buchung)
                .one_or_none()
            )
            if source is None:
                raise ValueError("Die ursprüngliche Rückerstattungsbuchung fehlt.")
            original_booking, source_year = source
            if source_year.mandant_id != company.id or refund.mandant_id != company.id:
                raise ValueError("Rückerstattung und Buchung müssen zum geöffneten Mandanten gehören.")
            if source_year.id != original_year.id:
                raise ValueError("Die Rücknahme muss im ursprünglichen Geschäftsjahr erfolgen.")
            if original_booking.booking_type != BookingType.REGULAR.value:
                raise ValueError("Die ursprüngliche Rückerstattung ist keine reguläre Buchung.")
            if credit.origin_booking_date is None or original_booking.booking_date < credit.origin_booking_date:
                raise ValueError("Das Buchungsdatum der ursprünglichen Rückerstattung ist ungültig.")

            partner_role = (
                Geschaeftspartner.is_customer
                if direction is OffsetDirection.CUSTOMER
                else Geschaeftspartner.is_supplier
            )
            partner = (
                self._session.query(Geschaeftspartner)
                .filter(
                    Geschaeftspartner.mandant_id == company.id,
                    Geschaeftspartner.partner_id == refund.partner_id,
                    partner_role.is_(True),
                )
                .one_or_none()
            )
            if partner is None:
                raise ValueError("Der Geschäftspartner gehört nicht zum Mandanten oder hat nicht die passende Rolle.")

            self._validate_refund_booking(
                booking=original_booking,
                refund=refund,
                credit_account=credit.account_number,
                direction=direction,
                mandant_id=company.id,
            )

            existing_reversals = (
                self._session.query(Buchung)
                .filter(Buchung.reversal_of_booking_id == refund.booking_id)
                .with_for_update()
                .all()
            )
            if len(existing_reversals) > 1:
                raise ValueError("Zur Rückerstattung existieren mehrere Journalgegenbuchungen.")

            if existing_reversals:
                reversal_booking = existing_reversals[0]
                reversal_year = (
                    self._session.query(Wirtschaftsjahr)
                    .filter(Wirtschaftsjahr.id == reversal_booking.wirtschaftsjahr_id)
                    .one_or_none()
                )
                if (
                    reversal_booking.booking_type != BookingType.REVERSAL.value
                    or reversal_booking.reversal_of_booking_id != refund.booking_id
                    or reversal_year is None
                    or reversal_year.mandant_id != company.id
                    or reversal_year.id != source_year.id
                    or reversal_booking.booking_date < original_booking.booking_date
                    or not fiscal_year.contains(reversal_booking.booking_date)
                ):
                    raise ValueError("Die vorhandene Journalgegenbuchung ist für diese Rücknahme nicht zulässig.")
                self._ensure_exact_inverse(original_booking, reversal_booking)
                if booking_date is not None and booking_date != reversal_booking.booking_date:
                    raise ValueError("Das angegebene Buchungsdatum weicht von der vorhandenen Gegenbuchung ab.")
                if self._session.query(
                    GuthabenOPRueckerstattungsruecknahme.id
                ).filter(
                    GuthabenOPRueckerstattungsruecknahme.reversal_booking_id
                    == reversal_booking.booking_id
                ).one_or_none():
                    raise ValueError("Die vorhandene Gegenbuchung wird bereits für eine andere Rücknahme verwendet.")
                effective_booking_date = reversal_booking.booking_date
                created_booking = False
            else:
                if booking_date is None:
                    raise ValueError("Für die neue Rücknahme muss ein Buchungsdatum angegeben werden.")
                self._booking_repository.require_open_fiscal_year(
                    company_id=company_id,
                    fiscal_year=fiscal_year,
                    booking_date=booking_date,
                    for_update=True,
                )
                if booking_date < original_booking.booking_date:
                    raise ValueError("Das Rücknahmebuchungsdatum darf nicht vor der Rückerstattung liegen.")
                reversal_domain = BookingDomain(
                    booking_date=booking_date,
                    description=f"Rücknahme Guthabenrückerstattung: {reason.strip()}",
                    booking_type=BookingType.REVERSAL,
                    reversal_of_booking_id=UUID(original_booking.booking_id),
                    lines=tuple(
                        BookingLine(
                            account_number=line.account_number,
                            side=(
                                EntrySide.CREDIT
                                if line.side == EntrySide.DEBIT.value
                                else EntrySide.DEBIT
                            ),
                            amount=line.amount,
                        )
                        for line in original_booking.zeilen
                    ),
                )
                reversal_booking = Buchung(
                    booking_id=str(reversal_domain.booking_id),
                    wirtschaftsjahr_id=original_year.id,
                    booking_date=reversal_domain.booking_date,
                    voucher_no=None,
                    description=reversal_domain.description,
                    booking_type=BookingType.REVERSAL.value,
                    reversal_of_booking_id=original_booking.booking_id,
                    zeilen=[
                        Buchungszeile(
                            position=position,
                            account_number=line.account_number,
                            side=line.side.value,
                            amount=line.amount,
                        )
                        for position, line in enumerate(reversal_domain.lines)
                    ],
                )
                self._session.add(reversal_booking)
                self._session.flush()
                self._ensure_exact_inverse(original_booking, reversal_booking)
                effective_booking_date = booking_date
                created_booking = True

            recorded_at = datetime.now(timezone.utc)
            return_record = GuthabenOPRueckerstattungsruecknahme(
                reversal_id=str(uuid4()),
                refund_id=refund.refund_id,
                reversal_booking_id=reversal_booking.booking_id,
                recorded_at=recorded_at,
                reason=reason.strip(),
            )
            self._session.add(return_record)
            self._session.flush()
            self._booking_repository.commit()
            return OpenItemCreditRefundReversal(
                company_id=company_id,
                partner_id=UUID(refund.partner_id),
                open_item_id=UUID(refund.open_item_id),
                refund_id=refund_id,
                direction=direction,
                reversal_booking_id=UUID(reversal_booking.booking_id),
                booking_date=effective_booking_date,
                amount=refund.amount,
                reason=reason,
                created_booking=created_booking,
                reversal_id=UUID(return_record.reversal_id),
                recorded_at=recorded_at,
            )
        except Exception:
            self._booking_repository.rollback()
            raise

    def _validate_refund_booking(
        self,
        *,
        booking: Buchung,
        refund: GuthabenOPRueckerstattung,
        credit_account: str,
        direction: OffsetDirection,
        mandant_id: int,
    ) -> None:
        control_side = (
            EntrySide.DEBIT.value
            if direction is OffsetDirection.CUSTOMER
            else EntrySide.CREDIT.value
        )
        cash_side = (
            EntrySide.CREDIT.value
            if direction is OffsetDirection.CUSTOMER
            else EntrySide.DEBIT.value
        )
        control_lines = [
            line for line in booking.zeilen
            if line.account_number == credit_account and line.side == control_side
        ]
        cash_lines = [
            line for line in booking.zeilen
            if line.account_number != credit_account and line.side == cash_side
        ]
        if (
            len(booking.zeilen) != 2
            or len(control_lines) != 1
            or len(cash_lines) != 1
            or control_lines[0].amount != refund.amount
            or cash_lines[0].amount != refund.amount
        ):
            raise ValueError("Die ursprüngliche Buchung entspricht nicht der gespeicherten Guthabenrückerstattung.")
        account_numbers = {line.account_number for line in booking.zeilen}
        if len(account_numbers) != 2 or self._session.query(Konto.id).filter(
            Konto.mandant_id == mandant_id,
            Konto.account_number.in_(account_numbers),
        ).count() != 2:
            raise ValueError("Ein Konto der Rückerstattungsbuchung gehört nicht zum Mandanten.")

    @staticmethod
    def _ensure_exact_inverse(original: Buchung, reversal: Buchung) -> None:
        def signature(booking: Buchung, *, invert: bool) -> Counter:
            result = Counter()
            for line in booking.zeilen:
                side = line.side
                if invert:
                    side = (
                        EntrySide.CREDIT.value
                        if side == EntrySide.DEBIT.value
                        else EntrySide.DEBIT.value
                    )
                result[(line.account_number, side, line.amount)] += 1
            return result

        if signature(original, invert=True) != signature(reversal, invert=False):
            raise ValueError("Die vorhandene Journalgegenbuchung spiegelt die Rückerstattung nicht exakt.")

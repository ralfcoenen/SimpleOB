"""Lesende Stichtagsberechnung für Sammelkonto-Abstimmungen."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from simpleob.database.models import (
    Ausgangsrechnung,
    Buchung,
    Buchungszeile,
    Eingangsrechnung,
    ForderungsOP,
    GuthabenOP,
    GuthabenOPEreignis,
    Gutschrift,
    Kontenrolle,
    Konto,
    Mandant,
    OPGuthabenverrechnung,
    RechnungsOPVerrechnungsereignis,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlung,
    Zahlungszuordnungskorrektur,
    Zahlungszuordnungskorrekturereignis,
)
from simpleob.domain.open_item_reconciliation import (
    OpenItemReconciliationReport,
    OpenItemReconciliationRow,
    UnexplainedControlMovement,
    UnresolvedCorrectionTiming,
)

_ROLES = (
    ("CUSTOMER_RECEIVABLES", "Kundenforderungen", "ASSET", "DEBIT"),
    ("SUPPLIER_PAYABLES", "Lieferantenverbindlichkeiten", "LIABILITY", "CREDIT"),
    ("CUSTOMER_CREDIT_BALANCES", "Kundenguthaben", "LIABILITY", "CREDIT"),
    ("SUPPLIER_CREDIT_BALANCES", "Lieferantenguthaben", "ASSET", "DEBIT"),
)
_ZERO = Decimal("0.00")


class OpenItemReconciliationRepository:
    """Berechnet OP- und Hauptbuchsalden ausschließlich lesend."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def reconcile(self, *, company_id: UUID, as_of_date: date) -> OpenItemReconciliationReport:
        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")
        if not isinstance(as_of_date, date):
            raise TypeError("as_of_date must be a date")
        company = self._session.query(Mandant).filter_by(company_id=str(company_id)).one_or_none()
        if company is None:
            raise ValueError("Der Mandant wurde nicht gefunden.")

        configured = {
            row.role: row.account_number
            for row in self._session.query(Kontenrolle).filter(
                Kontenrolle.mandant_id == company.id,
                Kontenrolle.role.in_([item[0] for item in _ROLES]),
            ).all()
        }
        role_accounts: dict[str, set[str]] = {role[0]: set() for role in _ROLES}
        unresolved_roles: set[str] = set()
        for role, account_number in configured.items():
            role_accounts[role].add(account_number)

        # Per-OP state stores its semantic role, the actual account on the
        # originating booking, and its balance as of the requested date.
        item_state: dict[str, dict] = {}
        known_booking_ids: set[str] = set()
        receivable_rows = (
            self._session.query(ForderungsOP, Ausgangsrechnung, Buchung)
            .join(Ausgangsrechnung, ForderungsOP.invoice_id == Ausgangsrechnung.invoice_id)
            .join(Buchung, Ausgangsrechnung.booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(Ausgangsrechnung.mandant_id == company.id, Wirtschaftsjahr.mandant_id == company.id)
            .all()
        )
        payable_rows = (
            self._session.query(VerbindlichkeitsOP, Eingangsrechnung, Buchung)
            .join(Eingangsrechnung, VerbindlichkeitsOP.invoice_id == Eingangsrechnung.invoice_id)
            .join(Buchung, Eingangsrechnung.booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(Eingangsrechnung.mandant_id == company.id, Wirtschaftsjahr.mandant_id == company.id)
            .all()
        )
        credit_rows = (
            self._session.query(GuthabenOP, Gutschrift, Buchung)
            .join(Gutschrift, GuthabenOP.credit_note_id == Gutschrift.credit_note_id)
            .join(Buchung, Gutschrift.booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(Gutschrift.mandant_id == company.id, Wirtschaftsjahr.mandant_id == company.id)
            .all()
        )
        for op, document, booking in receivable_rows + payable_rows:
            role, side, account_type = (
                ("CUSTOMER_RECEIVABLES", "DEBIT", "ASSET")
                if isinstance(op, ForderungsOP)
                else ("SUPPLIER_PAYABLES", "CREDIT", "LIABILITY")
            )
            account_number = self._source_account(
                company.id, booking.booking_id, side, account_type, op.amount
            )
            if account_number:
                role_accounts[role].add(account_number)
            else:
                unresolved_roles.add(role)
            known_booking_ids.add(booking.booking_id)
            item_state[op.open_item_id] = {
                "role": role, "account": account_number,
                "balance": op.amount if booking.booking_date <= as_of_date else _ZERO,
            }
        for op, document, booking in credit_rows:
            if document.credit_note_kind == "CUSTOMER":
                role, side, account_type = "CUSTOMER_CREDIT_BALANCES", "CREDIT", "LIABILITY"
            else:
                role, side, account_type = "SUPPLIER_CREDIT_BALANCES", "DEBIT", "ASSET"
            account_number = self._source_account(
                company.id, booking.booking_id, side, account_type, op.amount
            )
            if account_number:
                role_accounts[role].add(account_number)
            else:
                unresolved_roles.add(role)
            known_booking_ids.add(booking.booking_id)
            item_state[op.open_item_id] = {
                "role": role, "account": account_number,
                "balance": op.amount if booking.booking_date <= as_of_date else _ZERO,
            }

        # Payment and settlement events are dated by their associated ledger
        # booking, not by their operational/effective date.
        for event, payment, booking in (
            self._session.query(RechnungsOPZahlungsereignis, Zahlung, Buchung)
            .join(Zahlung, RechnungsOPZahlungsereignis.payment_id == Zahlung.payment_id)
            .join(Buchung, Zahlung.booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(Zahlung.mandant_id == company.id, Wirtschaftsjahr.mandant_id == company.id)
            .all()
        ):
            known_booking_ids.add(booking.booking_id)
            if booking.booking_date <= as_of_date:
                open_item_id = event.receivable_open_item_id or event.payable_open_item_id
                if open_item_id in item_state and item_state[open_item_id]["balance"] is not None:
                    item_state[open_item_id]["balance"] -= event.amount
        for event, settlement, booking in (
            self._session.query(RechnungsOPVerrechnungsereignis, OPGuthabenverrechnung, Buchung)
            .join(OPGuthabenverrechnung, RechnungsOPVerrechnungsereignis.settlement_id == OPGuthabenverrechnung.settlement_id)
            .join(Buchung, OPGuthabenverrechnung.booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(OPGuthabenverrechnung.mandant_id == company.id, Wirtschaftsjahr.mandant_id == company.id)
            .all()
        ):
            known_booking_ids.add(booking.booking_id)
            if booking.booking_date <= as_of_date:
                open_item_id = event.receivable_open_item_id or event.payable_open_item_id
                if open_item_id in item_state:
                    item_state[open_item_id]["balance"] -= event.amount
        for event, settlement, booking in (
            self._session.query(GuthabenOPEreignis, OPGuthabenverrechnung, Buchung)
            .join(OPGuthabenverrechnung, GuthabenOPEreignis.settlement_id == OPGuthabenverrechnung.settlement_id)
            .join(Buchung, OPGuthabenverrechnung.booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(OPGuthabenverrechnung.mandant_id == company.id, Wirtschaftsjahr.mandant_id == company.id)
            .all()
        ):
            if booking.booking_date <= as_of_date and event.open_item_id in item_state:
                item_state[event.open_item_id]["balance"] += event.amount_delta
        for event, correction in (
            self._session.query(Zahlungszuordnungskorrekturereignis, Zahlungszuordnungskorrektur)
            .join(Zahlungszuordnungskorrektur, Zahlungszuordnungskorrekturereignis.correction_id == Zahlungszuordnungskorrektur.correction_id)
            .filter(Zahlungszuordnungskorrektur.mandant_id == company.id)
            .all()
        ):
            correction_booking = None
            if correction.booking_id:
                correction_booking = self._session.query(Buchung).filter_by(booking_id=correction.booking_id).one_or_none()
                if correction_booking is not None:
                    known_booking_ids.add(correction_booking.booking_id)
            open_item_id = event.receivable_open_item_id or event.payable_open_item_id
            balance_adjustment = _correction_balance_adjustment(
                amount_delta=event.amount_delta,
                booking_date=correction.booking_date,
                as_of_date=as_of_date,
            )
            if balance_adjustment and open_item_id in item_state:
                # Event delta is the opposite of its effect on receivable/payable balance.
                item_state[open_item_id]["balance"] += balance_adjustment

        # Current-year opening bookings already carry prior balance-sheet
        # balances forward; do not add earlier fiscal-year balances twice.
        balance_year = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id == company.id,
                Wirtschaftsjahr.start_date <= as_of_date,
            )
            .order_by(Wirtschaftsjahr.start_date.desc())
            .first()
        )
        ledger_by_account: dict[str, Decimal] = defaultdict(lambda: _ZERO)
        line_query = (
            self._session.query(Buchungszeile, Buchung, Konto)
            .join(Buchung, Buchungszeile.buchung_id == Buchung.id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .join(Konto, (Konto.mandant_id == company.id) & (Konto.account_number == Buchungszeile.account_number))
            .filter(Wirtschaftsjahr.mandant_id == company.id, Buchung.booking_date <= as_of_date)
        )
        if balance_year is not None:
            line_query = line_query.filter(Wirtschaftsjahr.id == balance_year.id)
        line_rows = line_query.all()
        unknown_by_account: dict[str, list[UnexplainedControlMovement]] = defaultdict(list)
        unresolved_by_account: dict[str, list[UnresolvedCorrectionTiming]] = defaultdict(list)
        unresolved_by_role: dict[str, list[UnresolvedCorrectionTiming]] = defaultdict(list)
        role_by_account = {acc: role for role, accounts in role_accounts.items() for acc in accounts}
        for line, booking, account in line_rows:
            role = role_by_account.get(line.account_number)
            if role is None:
                continue
            normal_side = next(item[3] for item in _ROLES if item[0] == role)
            signed = line.amount if line.side == normal_side else -line.amount
            ledger_by_account[line.account_number] += signed
            if booking.booking_id not in known_booking_ids:
                unknown_by_account[line.account_number].append(
                    UnexplainedControlMovement(
                        booking_id=booking.booking_id,
                        booking_date=booking.booking_date,
                        voucher_no=booking.voucher_no,
                        description=booking.description,
                        side=line.side,
                        amount=line.amount,
                    )
                )

        op_by_account: dict[str, Decimal] = defaultdict(lambda: _ZERO)
        for state in item_state.values():
            if state["account"] and state["balance"] is not None:
                op_by_account[state["account"]] += state["balance"]

        for correction in (
            self._session.query(Zahlungszuordnungskorrektur)
            .filter(
                Zahlungszuordnungskorrektur.mandant_id == company.id,
                Zahlungszuordnungskorrektur.booking_date.is_(None),
            )
            .all()
        ):
            source_id = (
                correction.source_receivable_open_item_id
                or correction.source_payable_open_item_id
            )
            target_id = (
                correction.target_receivable_open_item_id
                or correction.target_payable_open_item_id
            )
            role = (
                "CUSTOMER_RECEIVABLES"
                if correction.direction == "CUSTOMER_RECEIPT"
                else "SUPPLIER_PAYABLES"
            )
            detail = UnresolvedCorrectionTiming(
                correction_id=correction.correction_id,
                correction_date=correction.correction_date,
                reason=correction.reason,
                amount=correction.amount,
                source_open_item_id=source_id,
                target_open_item_id=target_id,
            )
            unresolved_by_role[role].append(detail)
            affected_accounts = set()
            for item_id in (source_id, target_id):
                state = item_state.get(item_id)
                if state and state["account"]:
                    affected_accounts.add(state["account"])
            for account_number in affected_accounts:
                unresolved_by_account[account_number].append(detail)

        rows = []
        for role, label, account_type, _normal_side in _ROLES:
            accounts = sorted(role_accounts[role])
            if not accounts:
                rows.append(OpenItemReconciliationRow(
                    role=role, role_label=label, account_number=None,
                    account_name="", ledger_balance=_ZERO, open_item_balance=_ZERO,
                    difference=_ZERO,
                    status=(
                        "ZEITLICH_UNGEKLAERT" if unresolved_by_role.get(role)
                        else "OP_KONTO_UNERMITTELBAR" if role in unresolved_roles
                        else "NICHT_KONFIGURIERT"
                    ),
                    unresolved_correction_timings=tuple(unresolved_by_role.get(role, ())),
                ))
                continue
            for account_number in accounts:
                account = self._session.query(Konto).filter_by(
                    mandant_id=company.id, account_number=account_number
                ).one_or_none()
                ledger = ledger_by_account[account_number]
                op_balance = op_by_account[account_number]
                difference = ledger - op_balance
                unexplained = tuple(unknown_by_account[account_number])
                unresolved = tuple(
                    unresolved_by_account[account_number]
                    or unresolved_by_role.get(role, ())
                )
                if account is None or account.account_type != account_type:
                    status = "KONTOFEHLER"
                elif unresolved:
                    status = "ZEITLICH_UNGEKLAERT"
                elif role in unresolved_roles:
                    status = "OP_KONTO_UNERMITTELBAR"
                elif unexplained:
                    status = "UNGEKLAERTE_BEWEGUNG"
                elif configured.get(role) != account_number:
                    status = "KONTO_NICHT_MEHR_ZUGEORDNET"
                elif difference == _ZERO:
                    status = "ABGESTIMMT"
                else:
                    status = "ABWEICHUNG"
                rows.append(OpenItemReconciliationRow(
                    role=role, role_label=label, account_number=account_number,
                    account_name=account.name if account else "",
                    ledger_balance=ledger, open_item_balance=op_balance,
                    difference=difference, status=status,
                    unexplained_movements=unexplained,
                    unresolved_correction_timings=unresolved,
                ))
        return OpenItemReconciliationReport(company_id, as_of_date, tuple(rows))

    def _source_account(self, mandant_id: int, booking_id: str, side: str,
                        account_type: str, amount: Decimal) -> str | None:
        account_amounts = (
            self._session.query(Buchungszeile.account_number, func.sum(Buchungszeile.amount))
            .join(Buchung, Buchungszeile.buchung_id == Buchung.id)
            .join(Konto, (Konto.mandant_id == mandant_id) & (Konto.account_number == Buchungszeile.account_number))
            .filter(Buchung.booking_id == booking_id, Buchungszeile.side == side,
                    Konto.account_type == account_type)
            .group_by(Buchungszeile.account_number)
            .all()
        )
        matches = [account for account, total in account_amounts if total == amount]
        return matches[0] if len(matches) == 1 else None


def _correction_balance_adjustment(
    *, amount_delta: Decimal, booking_date: date | None, as_of_date: date
) -> Decimal:
    """Liefert die Bestandsänderung, falls das Korrekturbuchungsdatum erreicht ist."""
    if booking_date is None or booking_date > as_of_date:
        return _ZERO
    return -amount_delta

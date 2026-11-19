"""Read models für Auswertungen der Personenkonten."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from simpleob.domain.person_account_role import PersonAccountRole


@dataclass(frozen=True, slots=True)
class PersonAccountBalanceRow:
    account_number: str
    partner_id: UUID
    partner_name: str
    role: PersonAccountRole
    opening_balance: Decimal
    debit_turnover: Decimal
    credit_turnover: Decimal
    ending_balance: Decimal
    ending_debit_balance: Decimal
    ending_credit_balance: Decimal


@dataclass(frozen=True, slots=True)
class PersonAccountSummary:
    start_date: date
    end_date: date
    rows: tuple[PersonAccountBalanceRow, ...]
    opening_debit_total: Decimal
    opening_credit_total: Decimal
    debit_turnover_total: Decimal
    credit_turnover_total: Decimal
    ending_debit_total: Decimal
    ending_credit_total: Decimal


@dataclass(frozen=True, slots=True)
class PersonAccountStatementLine:
    booking_date: date
    voucher_no: str
    description: str
    debit: Decimal
    credit: Decimal
    running_balance: Decimal
    booking_id: UUID
    is_opening: bool


@dataclass(frozen=True, slots=True)
class PersonAccountStatement:
    fiscal_year_start: date
    fiscal_year_end: date
    start_date: date
    end_date: date
    account_number: str
    account_name: str
    partner_id: UUID
    partner_name: str
    role: PersonAccountRole
    opening_balance: Decimal
    carried_forward_balance: Decimal
    lines: tuple[PersonAccountStatementLine, ...]
    ending_balance: Decimal

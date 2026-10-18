"""Domänenmodell des portablen SimpleOB-Mandantentransfers."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

CLIENT_TRANSFER_FORMAT_NAME = "SimpleOB Client Transfer"
CLIENT_TRANSFER_FORMAT_VERSION = 1


def _validate_required_text(
    value: str,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} must not be blank"
        )

    return normalized


def _validate_optional_text(
    value: str | None,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string or None"
        )

    normalized = value.strip()

    return normalized or None


def _validate_account_number(
    value: str,
    *,
    field_name: str,
) -> str:
    normalized = _validate_required_text(
        value,
        field_name=field_name,
    )

    if not normalized.isdigit():
        raise ValueError(
            f"{field_name} must contain digits only"
        )

    return normalized


def _validate_account_numbers(
    values: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(
            f"{field_name} must be a tuple"
        )

    normalized = tuple(
        _validate_account_number(
            value,
            field_name=field_name,
        )
        for value in values
    )

    if len(set(normalized)) != len(normalized):
        raise ValueError(
            f"{field_name} must not contain duplicates"
        )

    return normalized


@dataclass(frozen=True, slots=True)
class ClientTransferFormat:
    """Identifiziert das verwendete Transferformat."""

    name: str = CLIENT_TRANSFER_FORMAT_NAME
    version: int = CLIENT_TRANSFER_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.name != CLIENT_TRANSFER_FORMAT_NAME:
            raise ValueError(
                "Unbekanntes Mandantentransferformat."
            )

        if self.version != CLIENT_TRANSFER_FORMAT_VERSION:
            raise ValueError(
                "Nicht unterstützte Version des "
                "Mandantentransferformats."
            )


@dataclass(frozen=True, slots=True)
class ClientTransferApplication:
    """Beschreibt die erzeugende SimpleOB-Version."""

    name: str
    version: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            _validate_required_text(
                self.name,
                field_name="name",
            ),
        )
        object.__setattr__(
            self,
            "version",
            _validate_required_text(
                self.version,
                field_name="version",
            ),
        )


@dataclass(frozen=True, slots=True)
class ClientTransferMasterData:
    """Portable Unternehmensstammdaten."""

    name: str
    legal_form: str = ""
    tax_number: str = ""
    tax_office: str = ""
    tax_id: str = ""
    tax_economic_id: str = ""
    bf4: str = ""
    street: str = ""
    house_number: str = ""
    postal_code: str = ""
    city: str = ""
    country: str = ""
    federal_state: str = ""
    business: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            _validate_required_text(
                self.name,
                field_name="name",
            ),
        )

        for field_name in (
            "legal_form",
            "tax_number",
            "tax_office",
            "tax_id",
            "tax_economic_id",
            "bf4",
            "street",
            "house_number",
            "postal_code",
            "city",
            "country",
            "federal_state",
            "business",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, str):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            normalized = value.strip()

            object.__setattr__(
                self,
                field_name,
                normalized,
            )


@dataclass(frozen=True, slots=True)
class ClientTransferAccount:
    """Ein portables Mandantenkonto."""

    account_number: str
    name: str
    account_type: str
    is_active: bool
    debit_position_code: str | None = None
    credit_position_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "account_number",
            _validate_account_number(
                self.account_number,
                field_name="account_number",
            ),
        )
        object.__setattr__(
            self,
            "name",
            _validate_required_text(
                self.name,
                field_name="name",
            ),
        )
        object.__setattr__(
            self,
            "account_type",
            _validate_required_text(
                self.account_type,
                field_name="account_type",
            ),
        )

        if not isinstance(self.is_active, bool):
            raise TypeError(
                "is_active must be a bool"
            )

        object.__setattr__(
            self,
            "debit_position_code",
            _validate_optional_text(
                self.debit_position_code,
                field_name="debit_position_code",
            ),
        )
        object.__setattr__(
            self,
            "credit_position_code",
            _validate_optional_text(
                self.credit_position_code,
                field_name="credit_position_code",
            ),
        )


@dataclass(frozen=True, slots=True)
class ClientTransferControlAccounts:
    """Portable technische Kontenkonfiguration."""

    opening_balance_account: str
    income_summary_account: str
    profit_account: str
    loss_account: str
    profit_loss_carryforward_account: str
    statutory_reserve_account: str
    other_revenue_reserves_account: str
    distribution_liability_account: str
    depreciation_expense_account: str
    fixed_asset_disposal_gain_account: str
    fixed_asset_disposal_loss_account: str

    def __post_init__(self) -> None:
        for field_name in (
            "opening_balance_account",
            "income_summary_account",
            "profit_account",
            "loss_account",
            "profit_loss_carryforward_account",
            "statutory_reserve_account",
            "other_revenue_reserves_account",
            "distribution_liability_account",
            "depreciation_expense_account",
            "fixed_asset_disposal_gain_account",
            "fixed_asset_disposal_loss_account",
        ):
            object.__setattr__(
                self,
                field_name,
                _validate_account_number(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )


@dataclass(frozen=True, slots=True)
class ClientTransferVatAccounts:
    """Portable Umsatzsteuerkontenkonfiguration."""

    input_tax_7: str
    input_tax_19: str
    output_tax_7: str
    output_tax_19: str

    def __post_init__(self) -> None:
        for field_name in (
            "input_tax_7",
            "input_tax_19",
            "output_tax_7",
            "output_tax_19",
        ):
            object.__setattr__(
                self,
                field_name,
                _validate_account_number(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )


@dataclass(frozen=True, slots=True)
class ClientTransferAccountRoles:
    """Portable fachliche Kontenrollen."""

    cash_accounts: tuple[str, ...] = ()
    bank_accounts: tuple[str, ...] = ()
    general_rate_sales_accounts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        cash_accounts = _validate_account_numbers(
            self.cash_accounts,
            field_name="cash_accounts",
        )
        bank_accounts = _validate_account_numbers(
            self.bank_accounts,
            field_name="bank_accounts",
        )
        general_rate_sales_accounts = (
            _validate_account_numbers(
                self.general_rate_sales_accounts,
                field_name="general_rate_sales_accounts",
            )
        )

        role_sets = (
            set(cash_accounts),
            set(bank_accounts),
            set(general_rate_sales_accounts),
        )

        for index, account_numbers in enumerate(
            role_sets
        ):
            for other_account_numbers in role_sets[
                index + 1:
            ]:
                if (
                    account_numbers
                    & other_account_numbers
                ):
                    raise ValueError(
                        "Ein Konto darf nicht mehreren "
                        "fachlichen Rollen zugeordnet sein."
                    )

        object.__setattr__(
            self,
            "cash_accounts",
            cash_accounts,
        )
        object.__setattr__(
            self,
            "bank_accounts",
            bank_accounts,
        )
        object.__setattr__(
            self,
            "general_rate_sales_accounts",
            general_rate_sales_accounts,
        )


@dataclass(frozen=True, slots=True)
class ClientTransferTaxonomyMapping:
    """Portable Taxonomiezuordnung eines Kontos."""

    taxonomy_version: str
    account_number: str
    concept_name: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "taxonomy_version",
            _validate_required_text(
                self.taxonomy_version,
                field_name="taxonomy_version",
            ),
        )
        object.__setattr__(
            self,
            "account_number",
            _validate_account_number(
                self.account_number,
                field_name="account_number",
            ),
        )
        object.__setattr__(
            self,
            "concept_name",
            _validate_required_text(
                self.concept_name,
                field_name="concept_name",
            ),
        )


@dataclass(frozen=True, slots=True)
class ClientTransferFiscalYearReference:
    """Portable Referenz auf ein Geschäftsjahr."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if not isinstance(self.start_date, date):
            raise TypeError(
                "start_date must be a date"
            )

        if not isinstance(self.end_date, date):
            raise TypeError(
                "end_date must be a date"
            )

        if self.start_date > self.end_date:
            raise ValueError(
                "start_date must not be after end_date"
            )


@dataclass(frozen=True, slots=True)
class ClientTransferBookingLineReference:
    """Portable Referenz auf eine Buchungszeile."""

    booking_id: UUID
    position: int

    def __post_init__(self) -> None:
        if not isinstance(self.booking_id, UUID):
            raise TypeError(
                "booking_id must be a UUID"
            )

        if (
            not isinstance(self.position, int)
            or isinstance(self.position, bool)
        ):
            raise TypeError(
                "position must be an int"
            )

        if self.position < 0:
            raise ValueError(
                "position must not be negative"
            )


@dataclass(frozen=True, slots=True)
class ClientTransferBookingLine:
    """Portable Buchungszeile einschließlich ihrer Position."""

    position: int
    account_number: str
    side: str
    amount: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.position, int)
            or isinstance(self.position, bool)
        ):
            raise TypeError(
                "position must be an int"
            )

        if self.position < 0:
            raise ValueError(
                "position must not be negative"
            )

        object.__setattr__(
            self,
            "account_number",
            _validate_account_number(
                self.account_number,
                field_name="account_number",
            ),
        )

        side = _validate_required_text(
            self.side,
            field_name="side",
        )

        if side not in {"DEBIT", "CREDIT"}:
            raise ValueError(
                "side must be DEBIT or CREDIT"
            )

        object.__setattr__(
            self,
            "side",
            side,
        )

        amount = _validate_required_text(
            self.amount,
            field_name="amount",
        )

        object.__setattr__(
            self,
            "amount",
            amount,
        )


@dataclass(frozen=True, slots=True)
class ClientTransferBooking:
    """Portable Buchung eines Geschäftsjahres."""

    booking_id: UUID
    booking_date: date
    booking_type: str
    lines: tuple[ClientTransferBookingLine, ...]
    voucher_no: str | None = None
    description: str | None = None
    reversal_of_booking_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.booking_id, UUID):
            raise TypeError(
                "booking_id must be a UUID"
            )

        if not isinstance(self.booking_date, date):
            raise TypeError(
                "booking_date must be a date"
            )

        booking_type = _validate_required_text(
            self.booking_type,
            field_name="booking_type",
        )

        if booking_type not in {
            "REGULAR",
            "OPENING",
            "CLOSING",
            "REVERSAL",
        }:
            raise ValueError(
                "unknown booking_type"
            )

        object.__setattr__(
            self,
            "booking_type",
            booking_type,
        )

        if not isinstance(self.lines, tuple):
            raise TypeError(
                "lines must be a tuple"
            )

        if not all(
            isinstance(
                line,
                ClientTransferBookingLine,
            )
            for line in self.lines
        ):
            raise TypeError(
                "lines must contain only "
                "ClientTransferBookingLine objects"
            )

        positions = tuple(
            line.position
            for line in self.lines
        )

        if len(set(positions)) != len(positions):
            raise ValueError(
                "booking line positions must be unique"
            )

        if positions != tuple(range(len(self.lines))):
            raise ValueError(
                "booking line positions must be "
                "continuous and start at zero"
            )

        object.__setattr__(
            self,
            "voucher_no",
            _validate_optional_text(
                self.voucher_no,
                field_name="voucher_no",
            ),
        )
        object.__setattr__(
            self,
            "description",
            _validate_optional_text(
                self.description,
                field_name="description",
            ),
        )

        if (
            self.reversal_of_booking_id is not None
            and not isinstance(
                self.reversal_of_booking_id,
                UUID,
            )
        ):
            raise TypeError(
                "reversal_of_booking_id must be "
                "a UUID or None"
            )

        if (
            booking_type == "REVERSAL"
            and self.reversal_of_booking_id is None
        ):
            raise ValueError(
                "REVERSAL booking requires "
                "reversal_of_booking_id"
            )

        if (
            booking_type != "REVERSAL"
            and self.reversal_of_booking_id is not None
        ):
            raise ValueError(
                "only REVERSAL booking may reference "
                "reversal_of_booking_id"
            )


@dataclass(frozen=True, slots=True)
class ClientTransferFiscalYear:
    """Portables Geschäftsjahr einschließlich Buchungen."""

    start_date: date
    end_date: date
    status: str
    opening_source: (
        ClientTransferFiscalYearReference | None
    )
    bookings: tuple[ClientTransferBooking, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.start_date, date):
            raise TypeError(
                "start_date must be a date"
            )

        if not isinstance(self.end_date, date):
            raise TypeError(
                "end_date must be a date"
            )

        if self.start_date > self.end_date:
            raise ValueError(
                "start_date must not be after end_date"
            )

        status = _validate_required_text(
            self.status,
            field_name="status",
        )

        if status not in {"OPEN", "CLOSED"}:
            raise ValueError(
                "status must be OPEN or CLOSED"
            )

        object.__setattr__(
            self,
            "status",
            status,
        )

        if (
            self.opening_source is not None
            and not isinstance(
                self.opening_source,
                ClientTransferFiscalYearReference,
            )
        ):
            raise TypeError(
                "opening_source must be a "
                "ClientTransferFiscalYearReference or None"
            )

        if not isinstance(self.bookings, tuple):
            raise TypeError(
                "bookings must be a tuple"
            )

        if not all(
            isinstance(
                booking,
                ClientTransferBooking,
            )
            for booking in self.bookings
        ):
            raise TypeError(
                "bookings must contain only "
                "ClientTransferBooking objects"
            )

        booking_ids = tuple(
            booking.booking_id
            for booking in self.bookings
        )

        if len(set(booking_ids)) != len(booking_ids):
            raise ValueError(
                "bookings must not contain duplicate "
                "booking IDs"
            )

        for booking in self.bookings:
            if not (
                self.start_date
                <= booking.booking_date
                <= self.end_date
            ):
                raise ValueError(
                    "booking date must be within "
                    "the fiscal year"
                )


@dataclass(frozen=True, slots=True)
class ClientTransferProfitAppropriationAnnualData:
    """Portable jahresbezogene Ergebnisverwendung."""

    fiscal_year: ClientTransferFiscalYearReference
    statutory_reserve_addition: str
    other_revenue_reserves_addition: str
    statutory_reserve_release: str
    other_revenue_reserves_release: str
    distribution: str
    profit_loss_carryforward: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.fiscal_year,
            ClientTransferFiscalYearReference,
        ):
            raise TypeError(
                "fiscal_year must be a "
                "ClientTransferFiscalYearReference"
            )

        for field_name in (
            "statutory_reserve_addition",
            "other_revenue_reserves_addition",
            "statutory_reserve_release",
            "other_revenue_reserves_release",
            "distribution",
            "profit_loss_carryforward",
        ):
            object.__setattr__(
                self,
                field_name,
                _validate_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )


@dataclass(frozen=True, slots=True)
class ClientTransferProfitAppropriationPosting:
    """Portable bestätigte Ergebnisverwendungsbuchung."""

    posting_id: UUID
    source_fiscal_year: ClientTransferFiscalYearReference
    posting_date: date
    amount: str
    booking_line: ClientTransferBookingLineReference
    posting_type: str

    def __post_init__(self) -> None:
        if not isinstance(self.posting_id, UUID):
            raise TypeError(
                "posting_id must be a UUID"
            )

        if not isinstance(
            self.source_fiscal_year,
            ClientTransferFiscalYearReference,
        ):
            raise TypeError(
                "source_fiscal_year must be a "
                "ClientTransferFiscalYearReference"
            )

        if not isinstance(self.posting_date, date):
            raise TypeError(
                "posting_date must be a date"
            )

        object.__setattr__(
            self,
            "amount",
            _validate_required_text(
                self.amount,
                field_name="amount",
            ),
        )

        if not isinstance(
            self.booking_line,
            ClientTransferBookingLineReference,
        ):
            raise TypeError(
                "booking_line must be a "
                "ClientTransferBookingLineReference"
            )

        posting_type = _validate_required_text(
            self.posting_type,
            field_name="posting_type",
        )

        if posting_type not in {
            "STATUTORY_RESERVE_ADDITION",
            "OTHER_REVENUE_RESERVES_ADDITION",
            "STATUTORY_RESERVE_RELEASE",
            "OTHER_REVENUE_RESERVES_RELEASE",
            "DISTRIBUTION",
        }:
            raise ValueError(
                "unknown posting_type"
            )

        object.__setattr__(
            self,
            "posting_type",
            posting_type,
        )


@dataclass(frozen=True, slots=True)
class ClientTransferEquityContribution:
    """Portable Kennzeichnung einer BVV-Einlage."""

    booking_line: ClientTransferBookingLineReference

    def __post_init__(self) -> None:
        if not isinstance(
            self.booking_line,
            ClientTransferBookingLineReference,
        ):
            raise TypeError(
                "booking_line must be a "
                "ClientTransferBookingLineReference"
            )


@dataclass(frozen=True, slots=True)
class ClientTransferShareholder:
    """Portabler Gesellschafter."""

    shareholder_id: UUID
    shareholder_number: str
    name: str
    legal_status: str
    share_numerator: str
    share_denominator: str
    first_name: str = ""
    tax_number: str = ""
    tax_number_federal_state: str = ""
    tax_id: str = ""
    wid: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.shareholder_id, UUID):
            raise TypeError(
                "shareholder_id must be a UUID"
            )

        for field_name in (
            "shareholder_number",
            "name",
            "legal_status",
            "share_numerator",
            "share_denominator",
        ):
            object.__setattr__(
                self,
                field_name,
                _validate_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

        for field_name in (
            "first_name",
            "tax_number",
            "tax_number_federal_state",
            "tax_id",
            "wid",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, str):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            object.__setattr__(
                self,
                field_name,
                value.strip(),
            )

        if not self.share_numerator.isdigit():
            raise ValueError(
                "share_numerator must contain digits only"
            )

        if not self.share_denominator.isdigit():
            raise ValueError(
                "share_denominator must contain digits only"
            )

        if int(self.share_denominator) <= 0:
            raise ValueError(
                "share_denominator must be greater than zero"
            )


@dataclass(frozen=True, slots=True)
class ClientTransferTaxDepreciationAdjustment:
    """Portable steuerliche AfA-Abweichung."""

    depreciation_id: UUID
    tax_amount: str

    def __post_init__(self) -> None:
        if not isinstance(self.depreciation_id, UUID):
            raise TypeError(
                "depreciation_id must be a UUID"
            )

        object.__setattr__(
            self,
            "tax_amount",
            _validate_required_text(
                self.tax_amount,
                field_name="tax_amount",
            ),
        )


@dataclass(frozen=True, slots=True)
class ClientTransferFixedAssetDepreciation:
    """Portable bestätigte Anlagenabschreibung."""

    depreciation_id: UUID
    fiscal_year_end: date
    depreciation_date: date
    amount: str
    booking_line: ClientTransferBookingLineReference
    kind: str
    source: str
    tax_adjustment: (
        ClientTransferTaxDepreciationAdjustment | None
    ) = None

    def __post_init__(self) -> None:
        if not isinstance(self.depreciation_id, UUID):
            raise TypeError(
                "depreciation_id must be a UUID"
            )

        if not isinstance(self.fiscal_year_end, date):
            raise TypeError(
                "fiscal_year_end must be a date"
            )

        if not isinstance(self.depreciation_date, date):
            raise TypeError(
                "depreciation_date must be a date"
            )

        object.__setattr__(
            self,
            "amount",
            _validate_required_text(
                self.amount,
                field_name="amount",
            ),
        )

        if not isinstance(
            self.booking_line,
            ClientTransferBookingLineReference,
        ):
            raise TypeError(
                "booking_line must be a "
                "ClientTransferBookingLineReference"
            )

        kind = _validate_required_text(
            self.kind,
            field_name="kind",
        )

        if kind not in {
            "LINEAR",
            "DEGRESSIVE",
            "SPECIAL",
            "OTHER",
        }:
            raise ValueError(
                "unknown depreciation kind"
            )

        object.__setattr__(
            self,
            "kind",
            kind,
        )

        source = _validate_required_text(
            self.source,
            field_name="source",
        )

        if source not in {
            "CALCULATED",
            "IMPORTED",
        }:
            raise ValueError(
                "unknown depreciation source"
            )

        object.__setattr__(
            self,
            "source",
            source,
        )

        if (
            source == "CALCULATED"
            and kind != "LINEAR"
        ):
            raise ValueError(
                "calculated depreciation must be linear"
            )

        if (
            self.tax_adjustment is not None
            and not isinstance(
                self.tax_adjustment,
                ClientTransferTaxDepreciationAdjustment,
            )
        ):
            raise TypeError(
                "tax_adjustment must be a "
                "ClientTransferTaxDepreciationAdjustment "
                "or None"
            )

        if (
            self.tax_adjustment is not None
            and self.tax_adjustment.depreciation_id
            != self.depreciation_id
        ):
            raise ValueError(
                "tax adjustment must reference "
                "this depreciation"
            )


@dataclass(frozen=True, slots=True)
class ClientTransferFixedAssetMovement:
    """Portable Anlagenbewegung."""

    movement_id: UUID
    fiscal_year_end: date
    movement_date: date
    amount: str
    booking_line: ClientTransferBookingLineReference
    movement_type: str
    reversed_movement_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.movement_id, UUID):
            raise TypeError(
                "movement_id must be a UUID"
            )

        if not isinstance(self.fiscal_year_end, date):
            raise TypeError(
                "fiscal_year_end must be a date"
            )

        if not isinstance(self.movement_date, date):
            raise TypeError(
                "movement_date must be a date"
            )

        object.__setattr__(
            self,
            "amount",
            _validate_required_text(
                self.amount,
                field_name="amount",
            ),
        )

        if not isinstance(
            self.booking_line,
            ClientTransferBookingLineReference,
        ):
            raise TypeError(
                "booking_line must be a "
                "ClientTransferBookingLineReference"
            )

        movement_type = _validate_required_text(
            self.movement_type,
            field_name="movement_type",
        )

        if movement_type not in {
            "ACQUISITION",
            "DISPOSAL",
            "LOSS",
            "REVERSAL",
        }:
            raise ValueError(
                "unknown movement_type"
            )

        object.__setattr__(
            self,
            "movement_type",
            movement_type,
        )

        if (
            self.reversed_movement_id is not None
            and not isinstance(
                self.reversed_movement_id,
                UUID,
            )
        ):
            raise TypeError(
                "reversed_movement_id must be "
                "a UUID or None"
            )

        if (
            movement_type == "REVERSAL"
            and self.reversed_movement_id is None
        ):
            raise ValueError(
                "REVERSAL movement requires "
                "reversed_movement_id"
            )

        if (
            movement_type != "REVERSAL"
            and self.reversed_movement_id is not None
        ):
            raise ValueError(
                "only REVERSAL movement may reference "
                "reversed_movement_id"
            )


@dataclass(frozen=True, slots=True)
class ClientTransferFixedAsset:
    """Portables Anlagegut einschließlich Historie."""

    fixed_asset_id: UUID
    asset_code: str
    description: str
    position_code: str
    asset_account_number: str
    depreciation_expense_account_number: str
    acquisition_date: date
    acquisition_cost: str
    depreciation_start_date: date
    useful_life_months: int
    status: str
    disposal_date: date | None = None
    movements: tuple[
        ClientTransferFixedAssetMovement,
        ...,
    ] = ()
    depreciations: tuple[
        ClientTransferFixedAssetDepreciation,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.fixed_asset_id, UUID):
            raise TypeError(
                "fixed_asset_id must be a UUID"
            )

        for field_name in (
            "asset_code",
            "description",
            "position_code",
        ):
            object.__setattr__(
                self,
                field_name,
                _validate_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

        object.__setattr__(
            self,
            "asset_account_number",
            _validate_account_number(
                self.asset_account_number,
                field_name="asset_account_number",
            ),
        )
        object.__setattr__(
            self,
            "depreciation_expense_account_number",
            _validate_account_number(
                self.depreciation_expense_account_number,
                field_name=(
                    "depreciation_expense_account_number"
                ),
            ),
        )

        if not isinstance(self.acquisition_date, date):
            raise TypeError(
                "acquisition_date must be a date"
            )

        object.__setattr__(
            self,
            "acquisition_cost",
            _validate_required_text(
                self.acquisition_cost,
                field_name="acquisition_cost",
            ),
        )

        if not isinstance(
            self.depreciation_start_date,
            date,
        ):
            raise TypeError(
                "depreciation_start_date must be a date"
            )

        if (
            self.depreciation_start_date
            < self.acquisition_date
        ):
            raise ValueError(
                "depreciation_start_date must not be "
                "before acquisition_date"
            )

        if (
            not isinstance(self.useful_life_months, int)
            or isinstance(self.useful_life_months, bool)
        ):
            raise TypeError(
                "useful_life_months must be an int"
            )

        if self.useful_life_months <= 0:
            raise ValueError(
                "useful_life_months must be greater "
                "than zero"
            )

        status = _validate_required_text(
            self.status,
            field_name="status",
        )

        if status not in {"ACTIVE", "DISPOSED"}:
            raise ValueError(
                "status must be ACTIVE or DISPOSED"
            )

        object.__setattr__(
            self,
            "status",
            status,
        )

        if (
            self.disposal_date is not None
            and not isinstance(self.disposal_date, date)
        ):
            raise TypeError(
                "disposal_date must be a date or None"
            )

        if (
            self.disposal_date is not None
            and self.disposal_date
            < self.acquisition_date
        ):
            raise ValueError(
                "disposal_date must not be before "
                "acquisition_date"
            )

        if (
            status == "ACTIVE"
            and self.disposal_date is not None
        ):
            raise ValueError(
                "active fixed asset must not have "
                "a disposal_date"
            )

        if (
            status == "DISPOSED"
            and self.disposal_date is None
        ):
            raise ValueError(
                "disposed fixed asset requires "
                "a disposal_date"
            )

        if not isinstance(self.movements, tuple):
            raise TypeError(
                "movements must be a tuple"
            )

        if not all(
            isinstance(
                movement,
                ClientTransferFixedAssetMovement,
            )
            for movement in self.movements
        ):
            raise TypeError(
                "movements must contain only "
                "ClientTransferFixedAssetMovement objects"
            )

        movement_ids = tuple(
            movement.movement_id
            for movement in self.movements
        )

        if len(set(movement_ids)) != len(movement_ids):
            raise ValueError(
                "movements must not contain duplicate IDs"
            )

        if not isinstance(self.depreciations, tuple):
            raise TypeError(
                "depreciations must be a tuple"
            )

        if not all(
            isinstance(
                depreciation,
                ClientTransferFixedAssetDepreciation,
            )
            for depreciation in self.depreciations
        ):
            raise TypeError(
                "depreciations must contain only "
                "ClientTransferFixedAssetDepreciation "
                "objects"
            )

        depreciation_ids = tuple(
            depreciation.depreciation_id
            for depreciation in self.depreciations
        )

        if (
            len(set(depreciation_ids))
            != len(depreciation_ids)
        ):
            raise ValueError(
                "depreciations must not contain "
                "duplicate IDs"
            )


@dataclass(frozen=True, slots=True)
class ClientTransferClient:
    """Portable Daten eines SimpleOB-Mandanten."""

    company_id: UUID
    master_data: ClientTransferMasterData
    accounts: tuple[ClientTransferAccount, ...]
    control_accounts: ClientTransferControlAccounts | None
    vat_accounts: ClientTransferVatAccounts | None
    account_roles: ClientTransferAccountRoles
    taxonomy_mappings: tuple[
        ClientTransferTaxonomyMapping,
        ...,
    ] = ()
    shareholders: tuple[
        ClientTransferShareholder,
        ...,
    ] = ()
    fixed_assets: tuple[
        ClientTransferFixedAsset,
        ...,
    ] = ()
    profit_appropriation_annual_data: tuple[
        ClientTransferProfitAppropriationAnnualData,
        ...,
    ] = ()
    profit_appropriation_postings: tuple[
        ClientTransferProfitAppropriationPosting,
        ...,
    ] = ()
    equity_contributions: tuple[
        ClientTransferEquityContribution,
        ...,
    ] = ()
    fiscal_years: tuple[
        ClientTransferFiscalYear,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(
            self.master_data,
            ClientTransferMasterData,
        ):
            raise TypeError(
                "master_data must be a "
                "ClientTransferMasterData"
            )

        if not isinstance(self.accounts, tuple):
            raise TypeError(
                "accounts must be a tuple"
            )

        if not all(
            isinstance(
                account,
                ClientTransferAccount,
            )
            for account in self.accounts
        ):
            raise TypeError(
                "accounts must contain only "
                "ClientTransferAccount objects"
            )

        account_numbers = tuple(
            account.account_number
            for account in self.accounts
        )

        if (
            len(set(account_numbers))
            != len(account_numbers)
        ):
            raise ValueError(
                "accounts must not contain duplicate "
                "account numbers"
            )

        if (
            self.control_accounts is not None
            and not isinstance(
                self.control_accounts,
                ClientTransferControlAccounts,
            )
        ):
            raise TypeError(
                "control_accounts must be a "
                "ClientTransferControlAccounts or None"
            )

        if (
            self.vat_accounts is not None
            and not isinstance(
                self.vat_accounts,
                ClientTransferVatAccounts,
            )
        ):
            raise TypeError(
                "vat_accounts must be a "
                "ClientTransferVatAccounts or None"
            )

        if not isinstance(
            self.account_roles,
            ClientTransferAccountRoles,
        ):
            raise TypeError(
                "account_roles must be a "
                "ClientTransferAccountRoles"
            )

        if not isinstance(
            self.taxonomy_mappings,
            tuple,
        ):
            raise TypeError(
                "taxonomy_mappings must be a tuple"
            )

        if not all(
            isinstance(
                mapping,
                ClientTransferTaxonomyMapping,
            )
            for mapping in self.taxonomy_mappings
        ):
            raise TypeError(
                "taxonomy_mappings must contain only "
                "ClientTransferTaxonomyMapping objects"
            )

        if not isinstance(
            self.fiscal_years,
            tuple,
        ):
            raise TypeError(
                "fiscal_years must be a tuple"
            )



        if not all(
            isinstance(
                fiscal_year,
                ClientTransferFiscalYear,
            )
            for fiscal_year in self.fiscal_years
        ):
            raise TypeError(
                "fiscal_years must contain only "
                "ClientTransferFiscalYear objects"
            )

        fiscal_year_keys = tuple(
            (
                fiscal_year.start_date,
                fiscal_year.end_date,
            )
            for fiscal_year in self.fiscal_years
        )

        if (
            len(set(fiscal_year_keys))
            != len(fiscal_year_keys)
        ):
            raise ValueError(
                "fiscal_years must not contain "
                "duplicates"
            )
        if not isinstance(self.shareholders, tuple):
            raise TypeError(
                "shareholders must be a tuple"
            )

        if not all(
            isinstance(
                shareholder,
                ClientTransferShareholder,
            )
            for shareholder in self.shareholders
        ):
            raise TypeError(
                "shareholders must contain only "
                "ClientTransferShareholder objects"
            )

        shareholder_ids = tuple(
            shareholder.shareholder_id
            for shareholder in self.shareholders
        )

        if (
            len(set(shareholder_ids))
            != len(shareholder_ids)
        ):
            raise ValueError(
                "shareholders must not contain "
                "duplicate IDs"
            )

        shareholder_numbers = tuple(
            shareholder.shareholder_number
            for shareholder in self.shareholders
        )

        if (
            len(set(shareholder_numbers))
            != len(shareholder_numbers)
        ):
            raise ValueError(
                "shareholders must not contain "
                "duplicate shareholder numbers"
            )

        if not isinstance(self.fixed_assets, tuple):
            raise TypeError(
                "fixed_assets must be a tuple"
            )

        if not isinstance(
            self.profit_appropriation_annual_data,
            tuple,
        ):
            raise TypeError(
                "profit_appropriation_annual_data "
                "must be a tuple"
            )

        if not all(
            isinstance(
                data,
                ClientTransferProfitAppropriationAnnualData,
            )
            for data in self.profit_appropriation_annual_data
        ):
            raise TypeError(
                "profit_appropriation_annual_data must "
                "contain only "
                "ClientTransferProfitAppropriationAnnualData "
                "objects"
            )

        annual_data_years = tuple(
            data.fiscal_year
            for data
            in self.profit_appropriation_annual_data
        )

        if (
            len(set(annual_data_years))
            != len(annual_data_years)
        ):
            raise ValueError(
                "profit_appropriation_annual_data must "
                "not contain duplicate fiscal years"
            )

        if not isinstance(
            self.profit_appropriation_postings,
            tuple,
        ):
            raise TypeError(
                "profit_appropriation_postings "
                "must be a tuple"
            )

        if not all(
            isinstance(
                posting,
                ClientTransferProfitAppropriationPosting,
            )
            for posting in self.profit_appropriation_postings
        ):
            raise TypeError(
                "profit_appropriation_postings must "
                "contain only "
                "ClientTransferProfitAppropriationPosting "
                "objects"
            )

        posting_ids = tuple(
            posting.posting_id
            for posting
            in self.profit_appropriation_postings
        )

        if len(set(posting_ids)) != len(posting_ids):
            raise ValueError(
                "profit_appropriation_postings must "
                "not contain duplicate IDs"
            )

        if not isinstance(
            self.equity_contributions,
            tuple,
        ):
            raise TypeError(
                "equity_contributions must be a tuple"
            )

        if not all(
            isinstance(
                contribution,
                ClientTransferEquityContribution,
            )
            for contribution in self.equity_contributions
        ):
            raise TypeError(
                "equity_contributions must contain only "
                "ClientTransferEquityContribution objects"
            )

        contribution_lines = tuple(
            contribution.booking_line
            for contribution in self.equity_contributions
        )

        if (
            len(set(contribution_lines))
            != len(contribution_lines)
        ):
            raise ValueError(
                "equity_contributions must not contain "
                "duplicate booking lines"
            )

        if not all(
            isinstance(
                fixed_asset,
                ClientTransferFixedAsset,
            )
            for fixed_asset in self.fixed_assets
        ):
            raise TypeError(
                "fixed_assets must contain only "
                "ClientTransferFixedAsset objects"
            )

        fixed_asset_ids = tuple(
            fixed_asset.fixed_asset_id
            for fixed_asset in self.fixed_assets
        )

        if (
            len(set(fixed_asset_ids))
            != len(fixed_asset_ids)
        ):
            raise ValueError(
                "fixed_assets must not contain "
                "duplicate IDs"
            )

        asset_codes = tuple(
            fixed_asset.asset_code
            for fixed_asset in self.fixed_assets
        )

        if len(set(asset_codes)) != len(asset_codes):
            raise ValueError(
                "fixed_assets must not contain "
                "duplicate asset codes"
            )


@dataclass(frozen=True, slots=True)
class ClientTransfer:
    """Portabler Mandantentransfer."""

    format: ClientTransferFormat
    application: ClientTransferApplication
    exported_at: datetime
    client: ClientTransferClient

    def __post_init__(self) -> None:
        if not isinstance(
            self.format,
            ClientTransferFormat,
        ):
            raise TypeError(
                "format must be a ClientTransferFormat"
            )

        if not isinstance(
            self.application,
            ClientTransferApplication,
        ):
            raise TypeError(
                "application must be a "
                "ClientTransferApplication"
            )

        if not isinstance(self.exported_at, datetime):
            raise TypeError(
                "exported_at must be a datetime"
            )

        if self.exported_at.tzinfo is None:
            raise ValueError(
                "exported_at must include timezone information"
            )

        if not isinstance(
            self.client,
            ClientTransferClient,
        ):
            raise TypeError(
                "client must be a ClientTransferClient"
            )

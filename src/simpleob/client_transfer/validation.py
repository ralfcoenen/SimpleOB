"""Dokumentweite Referenzprüfung für Mandantentransfers."""

from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from simpleob.client_transfer.model import (
    ClientTransfer,
    ClientTransferBookingLineReference,
    ClientTransferClient,
    ClientTransferFiscalYearReference,
)

FiscalYearKey = tuple[date, date]
BookingLineKey = tuple[UUID, int]


def validate_client_transfer_references(
    transfer: ClientTransfer,
) -> None:
    """Prüft dokumentweite Referenzen eines Mandantentransfers."""

    if not isinstance(transfer, ClientTransfer):
        raise TypeError(
            "transfer must be a ClientTransfer"
        )

    client = transfer.client

    account_numbers = {
        account.account_number
        for account in client.accounts
    }

    fiscal_year_keys = {
        _fiscal_year_key(
            fiscal_year.start_date,
            fiscal_year.end_date,
        )
        for fiscal_year in client.fiscal_years
    }

    bookings_by_id = {}
    booking_lines: set[BookingLineKey] = set()

    for fiscal_year in client.fiscal_years:
        for booking in fiscal_year.bookings:
            if booking.booking_id in bookings_by_id:
                raise ValueError(
                    "booking_id must be unique across "
                    "the complete transfer"
                )

            bookings_by_id[booking.booking_id] = booking

            for line in booking.lines:
                booking_lines.add(
                    (
                        booking.booking_id,
                        line.position,
                    )
                )

                _require_account(
                    line.account_number,
                    account_numbers,
                    reference_name="booking line",
                )

    _validate_account_references(
        client=client,
        account_numbers=account_numbers,
    )

    for fiscal_year in client.fiscal_years:
        if fiscal_year.opening_source is not None:
            _require_fiscal_year(
                fiscal_year.opening_source,
                fiscal_year_keys,
                reference_name="opening_source",
            )

        for booking in fiscal_year.bookings:
            if (
                booking.reversal_of_booking_id is not None
                and booking.reversal_of_booking_id
                not in bookings_by_id
            ):
                raise ValueError(
                    "reversal booking references "
                    "unknown booking"
                )

    for fixed_asset in client.fixed_assets:
        _require_account(
            fixed_asset.asset_account_number,
            account_numbers,
            reference_name="fixed asset asset account",
        )
        _require_account(
            fixed_asset.depreciation_expense_account_number,
            account_numbers,
            reference_name=(
                "fixed asset depreciation expense account"
            ),
        )

        movement_ids = {
            movement.movement_id
            for movement in fixed_asset.movements
        }

        for movement in fixed_asset.movements:
            _require_fiscal_year_end(
                movement.fiscal_year_end,
                fiscal_year_keys,
                reference_name="fixed asset movement",
            )
            _require_booking_line(
                movement.booking_line,
                booking_lines,
                reference_name="fixed asset movement",
            )

            if (
                movement.reversed_movement_id is not None
                and movement.reversed_movement_id
                not in movement_ids
            ):
                raise ValueError(
                    "fixed asset reversal movement "
                    "references unknown movement"
                )

        for depreciation in fixed_asset.depreciations:
            _require_fiscal_year_end(
                depreciation.fiscal_year_end,
                fiscal_year_keys,
                reference_name="fixed asset depreciation",
            )
            _require_booking_line(
                depreciation.booking_line,
                booking_lines,
                reference_name="fixed asset depreciation",
            )

    for data in client.profit_appropriation_annual_data:
        _require_fiscal_year(
            data.fiscal_year,
            fiscal_year_keys,
            reference_name=(
                "profit appropriation annual data"
            ),
        )

    for posting in client.profit_appropriation_postings:
        _require_fiscal_year(
            posting.source_fiscal_year,
            fiscal_year_keys,
            reference_name="profit appropriation posting",
        )
        _require_booking_line(
            posting.booking_line,
            booking_lines,
            reference_name="profit appropriation posting",
        )

    for contribution in client.equity_contributions:
        _require_booking_line(
            contribution.booking_line,
            booking_lines,
            reference_name="equity contribution",
        )
    _validate_document_consistency(transfer)


def _validate_account_references(
    *,
    client: ClientTransferClient,
    account_numbers: set[str],
) -> None:
    control_accounts = client.control_accounts

    if control_accounts is not None:
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
            _require_account(
                getattr(control_accounts, field_name),
                account_numbers,
                reference_name=(
                    f"control account {field_name}"
                ),
            )

    vat_accounts = client.vat_accounts

    if vat_accounts is not None:
        for field_name in (
            "input_tax_7",
            "input_tax_19",
            "output_tax_7",
            "output_tax_19",
        ):
            _require_account(
                getattr(vat_accounts, field_name),
                account_numbers,
                reference_name=f"VAT account {field_name}",
            )

    for account_number in (
        *client.account_roles.cash_accounts,
        *client.account_roles.bank_accounts,
        *client.account_roles.general_rate_sales_accounts,
    ):
        _require_account(
            account_number,
            account_numbers,
            reference_name="account role",
        )

    for mapping in client.taxonomy_mappings:
        _require_account(
            mapping.account_number,
            account_numbers,
            reference_name="taxonomy mapping",
        )


def _require_account(
    account_number: str,
    account_numbers: set[str],
    *,
    reference_name: str,
) -> None:
    if account_number not in account_numbers:
        raise ValueError(
            f"{reference_name} references unknown "
            f"account {account_number}"
        )


def _require_fiscal_year(
    reference: ClientTransferFiscalYearReference,
    fiscal_year_keys: set[FiscalYearKey],
    *,
    reference_name: str,
) -> None:
    key = _fiscal_year_key(
        reference.start_date,
        reference.end_date,
    )

    if key not in fiscal_year_keys:
        raise ValueError(
            f"{reference_name} references unknown "
            "fiscal year"
        )


def _require_fiscal_year_end(
    fiscal_year_end: date,
    fiscal_year_keys: set[FiscalYearKey],
    *,
    reference_name: str,
) -> None:
    if not any(
        end_date == fiscal_year_end
        for _, end_date in fiscal_year_keys
    ):
        raise ValueError(
            f"{reference_name} references unknown "
            "fiscal year"
        )


def _require_booking_line(
    reference: ClientTransferBookingLineReference,
    booking_lines: set[BookingLineKey],
    *,
    reference_name: str,
) -> None:
    key = (
        reference.booking_id,
        reference.position,
    )

    if key not in booking_lines:
        raise ValueError(
            f"{reference_name} references unknown "
            "booking line"
        )


def _fiscal_year_key(
    start_date: date,
    end_date: date,
) -> FiscalYearKey:
    return start_date, end_date


def _validate_document_consistency(
    transfer: ClientTransfer,
) -> None:
    client = transfer.client

    fiscal_year_by_booking_id = {}
    booking_by_id = {}
    booking_line_by_key = {}

    for fiscal_year in client.fiscal_years:
        for booking in fiscal_year.bookings:
            fiscal_year_by_booking_id[
                booking.booking_id
            ] = fiscal_year
            booking_by_id[booking.booking_id] = booking

            for line in booking.lines:
                booking_line_by_key[
                    (
                        booking.booking_id,
                        line.position,
                    )
                ] = line

                _parse_decimal(
                    line.amount,
                    field_name="booking line amount",
                )

    _validate_booking_reversals(
        client=client,
        fiscal_year_by_booking_id=(
            fiscal_year_by_booking_id
        ),
        booking_by_id=booking_by_id,
    )

    _validate_fixed_asset_consistency(
        client=client,
        fiscal_year_by_booking_id=(
            fiscal_year_by_booking_id
        ),
        booking_line_by_key=booking_line_by_key,
    )

    _validate_profit_appropriation_consistency(
        client=client,
        booking_by_id=booking_by_id,
        booking_line_by_key=booking_line_by_key,
    )


def _validate_booking_reversals(
    *,
    client: ClientTransferClient,
    fiscal_year_by_booking_id: dict[UUID, object],
    booking_by_id: dict[UUID, object],
) -> None:
    reversed_booking_ids: set[UUID] = set()

    for fiscal_year in client.fiscal_years:
        for booking in fiscal_year.bookings:
            original_id = booking.reversal_of_booking_id

            if original_id is None:
                continue

            original = booking_by_id[original_id]

            if original.booking_type != "REGULAR":
                raise ValueError(
                    "reversal booking must reference "
                    "a REGULAR booking"
                )

            if (
                fiscal_year_by_booking_id[original_id]
                is not fiscal_year
            ):
                raise ValueError(
                    "reversal booking and original booking "
                    "must belong to the same fiscal year"
                )

            if original_id in reversed_booking_ids:
                raise ValueError(
                    "booking must not be reversed more "
                    "than once"
                )

            reversed_booking_ids.add(original_id)


def _validate_fixed_asset_consistency(
    *,
    client: ClientTransferClient,
    fiscal_year_by_booking_id: dict[UUID, object],
    booking_line_by_key: dict[BookingLineKey, object],
) -> None:
    movement_lines: set[BookingLineKey] = set()
    depreciation_lines: set[BookingLineKey] = set()

    for fixed_asset in client.fixed_assets:
        movement_by_id = {
            movement.movement_id: movement
            for movement in fixed_asset.movements
        }
        reversed_movement_ids: set[UUID] = set()

        for movement in fixed_asset.movements:
            line_key = (
                movement.booking_line.booking_id,
                movement.booking_line.position,
            )

            fiscal_year = fiscal_year_by_booking_id[
                movement.booking_line.booking_id
            ]

            if (
                fiscal_year.end_date
                != movement.fiscal_year_end
            ):
                raise ValueError(
                    "fixed asset movement and booking "
                    "must belong to the same fiscal year"
                )

            if line_key in movement_lines:
                raise ValueError(
                    "booking line must not be assigned "
                    "to more than one fixed asset movement"
                )

            movement_lines.add(line_key)

            booking_line = booking_line_by_key[line_key]

            movement_amount = _parse_decimal(
                movement.amount,
                field_name="fixed asset movement amount",
            )
            booking_line_amount = _parse_decimal(
                booking_line.amount,
                field_name="booking line amount",
            )

            amount_may_differ = (
                movement.movement_type == "DISPOSAL"
            )

            if movement.movement_type == "REVERSAL":
                original = movement_by_id[
                    movement.reversed_movement_id
                ]

                if (
                    movement.reversed_movement_id
                    in reversed_movement_ids
                ):
                    raise ValueError(
                        "fixed asset movement must not "
                        "be reversed more than once"
                    )

                reversed_movement_ids.add(
                    movement.reversed_movement_id
                )

                if original.movement_type == "DISPOSAL":
                    amount_may_differ = True

            if (
                not amount_may_differ
                and booking_line_amount != movement_amount
            ):
                raise ValueError(
                    "booking line amount does not match "
                    "fixed asset movement amount"
                )

        for depreciation in fixed_asset.depreciations:
            line_key = (
                depreciation.booking_line.booking_id,
                depreciation.booking_line.position,
            )

            fiscal_year = fiscal_year_by_booking_id[
                depreciation.booking_line.booking_id
            ]

            if (
                fiscal_year.end_date
                != depreciation.fiscal_year_end
            ):
                raise ValueError(
                    "fixed asset depreciation and booking "
                    "must belong to the same fiscal year"
                )

            if line_key in depreciation_lines:
                raise ValueError(
                    "booking line must not be assigned "
                    "to more than one fixed asset depreciation"
                )

            depreciation_lines.add(line_key)

            booking_line = booking_line_by_key[line_key]

            depreciation_amount = _parse_decimal(
                depreciation.amount,
                field_name=(
                    "fixed asset depreciation amount"
                ),
            )
            booking_line_amount = _parse_decimal(
                booking_line.amount,
                field_name="booking line amount",
            )

            if booking_line_amount != depreciation_amount:
                raise ValueError(
                    "booking line amount does not match "
                    "fixed asset depreciation amount"
                )

            if depreciation.tax_adjustment is not None:
                _parse_decimal(
                    depreciation.tax_adjustment.tax_amount,
                    field_name=(
                        "tax depreciation adjustment amount"
                    ),
                )


def _validate_profit_appropriation_consistency(
    *,
    client: ClientTransferClient,
    booking_by_id: dict[UUID, object],
    booking_line_by_key: dict[BookingLineKey, object],
) -> None:
    posting_lines: set[BookingLineKey] = set()

    for data in client.profit_appropriation_annual_data:
        for field_name in (
            "statutory_reserve_addition",
            "other_revenue_reserves_addition",
            "statutory_reserve_release",
            "other_revenue_reserves_release",
            "distribution",
            "profit_loss_carryforward",
        ):
            _parse_decimal(
                getattr(data, field_name),
                field_name=(
                    f"profit appropriation {field_name}"
                ),
            )

    for posting in client.profit_appropriation_postings:
        line_key = (
            posting.booking_line.booking_id,
            posting.booking_line.position,
        )

        booking = booking_by_id[
            posting.booking_line.booking_id
        ]

        if booking.booking_date != posting.posting_date:
            raise ValueError(
                "profit appropriation posting date does "
                "not match booking date"
            )

        if line_key in posting_lines:
            raise ValueError(
                "booking line must not be assigned to "
                "more than one profit appropriation posting"
            )

        posting_lines.add(line_key)

        booking_line = booking_line_by_key[line_key]

        posting_amount = _parse_decimal(
            posting.amount,
            field_name="profit appropriation posting amount",
        )
        booking_line_amount = _parse_decimal(
            booking_line.amount,
            field_name="booking line amount",
        )

        if booking_line_amount != posting_amount:
            raise ValueError(
                "booking line amount does not match "
                "profit appropriation posting amount"
            )


def _parse_decimal(
    value: str,
    *,
    field_name: str,
) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(
            f"{field_name} must be a valid decimal"
        ) from exc

    if not result.is_finite():
        raise ValueError(
            f"{field_name} must be a finite decimal"
        )

    return result

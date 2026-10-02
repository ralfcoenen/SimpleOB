"""JSON-Serialisierung des portablen SimpleOB-Mandantentransfers."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from openbilanz.client_transfer.model import (
    ClientTransfer,
    ClientTransferAccount,
    ClientTransferAccountRoles,
    ClientTransferApplication,
    ClientTransferBooking,
    ClientTransferBookingLine,
    ClientTransferBookingLineReference,
    ClientTransferClient,
    ClientTransferControlAccounts,
    ClientTransferEquityContribution,
    ClientTransferFiscalYear,
    ClientTransferFiscalYearReference,
    ClientTransferFixedAsset,
    ClientTransferFixedAssetDepreciation,
    ClientTransferFixedAssetMovement,
    ClientTransferFormat,
    ClientTransferMasterData,
    ClientTransferProfitAppropriationAnnualData,
    ClientTransferProfitAppropriationPosting,
    ClientTransferShareholder,
    ClientTransferTaxDepreciationAdjustment,
    ClientTransferTaxonomyMapping,
    ClientTransferVatAccounts,
)
from openbilanz.client_transfer.validation import (
    validate_client_transfer_references,
)


JsonObject = dict[str, Any]


def client_transfer_to_dict(
    transfer: ClientTransfer,
) -> JsonObject:
    """Wandelt einen Mandantentransfer in JSON-kompatible Daten um."""
    if not isinstance(transfer, ClientTransfer):
        raise TypeError(
            "transfer must be a ClientTransfer"
        )

    return _to_json_value(asdict(transfer))


def client_transfer_to_json(
    transfer: ClientTransfer,
) -> str:
    """Serialisiert einen Mandantentransfer als lesbares JSON."""
    return json.dumps(
        client_transfer_to_dict(transfer),
        ensure_ascii=False,
        indent=2,
    )


def client_transfer_from_json(
    text: str,
) -> ClientTransfer:
    """Deserialisiert und validiert einen Mandantentransfer."""
    if not isinstance(text, str):
        raise TypeError(
            "text must be a string"
        )

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "invalid client transfer JSON"
        ) from exc

    return client_transfer_from_dict(data)


def client_transfer_from_dict(
    data: object,
) -> ClientTransfer:
    """Erzeugt und validiert einen Mandantentransfer aus JSON-Daten."""
    root = _require_object(
        data,
        field_name="client transfer",
    )

    transfer = ClientTransfer(
        format=_format_from_dict(
            _require_object(
                root.get("format"),
                field_name="format",
            )
        ),
        application=_application_from_dict(
            _require_object(
                root.get("application"),
                field_name="application",
            )
        ),
        exported_at=_parse_datetime(
            root.get("exported_at"),
            field_name="exported_at",
        ),
        client=_client_from_dict(
            _require_object(
                root.get("client"),
                field_name="client",
            )
        ),
    )

    validate_client_transfer_references(transfer)

    return transfer


def _format_from_dict(
    data: JsonObject,
) -> ClientTransferFormat:
    return ClientTransferFormat(
        name=_require_string(
            data.get("name"),
            field_name="format.name",
        ),
        version=_require_int(
            data.get("version"),
            field_name="format.version",
        ),
    )


def _application_from_dict(
    data: JsonObject,
) -> ClientTransferApplication:
    return ClientTransferApplication(
        name=_require_string(
            data.get("name"),
            field_name="application.name",
        ),
        version=_require_string(
            data.get("version"),
            field_name="application.version",
        ),
    )


def _master_data_from_dict(
    data: JsonObject,
) -> ClientTransferMasterData:
    return ClientTransferMasterData(
        name=_require_string(
            data.get("name"),
            field_name="master_data.name",
        ),
        legal_form=_optional_string_with_default(
            data,
            "legal_form",
        ),
        tax_number=_optional_string_with_default(
            data,
            "tax_number",
        ),
        tax_office=_optional_string_with_default(
            data,
            "tax_office",
        ),
        tax_id=_optional_string_with_default(
            data,
            "tax_id",
        ),
        tax_economic_id=_optional_string_with_default(
            data,
            "tax_economic_id",
        ),
        bf4=_optional_string_with_default(
            data,
            "bf4",
        ),
        street=_optional_string_with_default(
            data,
            "street",
        ),
        house_number=_optional_string_with_default(
            data,
            "house_number",
        ),
        postal_code=_optional_string_with_default(
            data,
            "postal_code",
        ),
        city=_optional_string_with_default(
            data,
            "city",
        ),
        country=_optional_string_with_default(
            data,
            "country",
        ),
        federal_state=_optional_string_with_default(
            data,
            "federal_state",
        ),
        business=_optional_string_with_default(
            data,
            "business",
        ),
    )


def _account_from_dict(
    data: JsonObject,
) -> ClientTransferAccount:
    return ClientTransferAccount(
        account_number=_require_string(
            data.get("account_number"),
            field_name="account.account_number",
        ),
        name=_require_string(
            data.get("name"),
            field_name="account.name",
        ),
        account_type=_require_string(
            data.get("account_type"),
            field_name="account.account_type",
        ),
        is_active=_require_bool(
            data.get("is_active"),
            field_name="account.is_active",
        ),
        debit_position_code=_optional_string(
            data.get("debit_position_code"),
            field_name="account.debit_position_code",
        ),
        credit_position_code=_optional_string(
            data.get("credit_position_code"),
            field_name="account.credit_position_code",
        ),
    )


def _control_accounts_from_dict(
    data: JsonObject,
) -> ClientTransferControlAccounts:
    field_names = (
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
    )

    values = {
        field_name: _require_string(
            data.get(field_name),
            field_name=(
                f"control_accounts.{field_name}"
            ),
        )
        for field_name in field_names
    }

    return ClientTransferControlAccounts(**values)


def _vat_accounts_from_dict(
    data: JsonObject,
) -> ClientTransferVatAccounts:
    return ClientTransferVatAccounts(
        input_tax_7=_require_string(
            data.get("input_tax_7"),
            field_name="vat_accounts.input_tax_7",
        ),
        input_tax_19=_require_string(
            data.get("input_tax_19"),
            field_name="vat_accounts.input_tax_19",
        ),
        output_tax_7=_require_string(
            data.get("output_tax_7"),
            field_name="vat_accounts.output_tax_7",
        ),
        output_tax_19=_require_string(
            data.get("output_tax_19"),
            field_name="vat_accounts.output_tax_19",
        ),
    )


def _account_roles_from_dict(
    data: JsonObject,
) -> ClientTransferAccountRoles:
    return ClientTransferAccountRoles(
        cash_accounts=_string_tuple(
            data.get("cash_accounts", []),
            field_name="account_roles.cash_accounts",
        ),
        bank_accounts=_string_tuple(
            data.get("bank_accounts", []),
            field_name="account_roles.bank_accounts",
        ),
        general_rate_sales_accounts=_string_tuple(
            data.get(
                "general_rate_sales_accounts",
                [],
            ),
            field_name=(
                "account_roles.general_rate_sales_accounts"
            ),
        ),
    )


def _taxonomy_mapping_from_dict(
    data: JsonObject,
) -> ClientTransferTaxonomyMapping:
    return ClientTransferTaxonomyMapping(
        taxonomy_version=_require_string(
            data.get("taxonomy_version"),
            field_name="taxonomy_mapping.taxonomy_version",
        ),
        account_number=_require_string(
            data.get("account_number"),
            field_name="taxonomy_mapping.account_number",
        ),
        concept_name=_require_string(
            data.get("concept_name"),
            field_name="taxonomy_mapping.concept_name",
        ),
    )


def _fiscal_year_reference_from_dict(
    data: JsonObject,
) -> ClientTransferFiscalYearReference:
    return ClientTransferFiscalYearReference(
        start_date=_parse_date(
            data.get("start_date"),
            field_name="fiscal_year_reference.start_date",
        ),
        end_date=_parse_date(
            data.get("end_date"),
            field_name="fiscal_year_reference.end_date",
        ),
    )


def _booking_line_reference_from_dict(
    data: JsonObject,
) -> ClientTransferBookingLineReference:
    return ClientTransferBookingLineReference(
        booking_id=_parse_uuid(
            data.get("booking_id"),
            field_name="booking_line_reference.booking_id",
        ),
        position=_require_int(
            data.get("position"),
            field_name="booking_line_reference.position",
        ),
    )


def _booking_line_from_dict(
    data: JsonObject,
) -> ClientTransferBookingLine:
    return ClientTransferBookingLine(
        position=_require_int(
            data.get("position"),
            field_name="booking_line.position",
        ),
        account_number=_require_string(
            data.get("account_number"),
            field_name="booking_line.account_number",
        ),
        side=_require_string(
            data.get("side"),
            field_name="booking_line.side",
        ),
        amount=_require_string(
            data.get("amount"),
            field_name="booking_line.amount",
        ),
    )


def _booking_from_dict(
    data: JsonObject,
) -> ClientTransferBooking:
    reversal_value = data.get(
        "reversal_of_booking_id"
    )

    return ClientTransferBooking(
        booking_id=_parse_uuid(
            data.get("booking_id"),
            field_name="booking.booking_id",
        ),
        booking_date=_parse_date(
            data.get("booking_date"),
            field_name="booking.booking_date",
        ),
        booking_type=_require_string(
            data.get("booking_type"),
            field_name="booking.booking_type",
        ),
        lines=tuple(
            _booking_line_from_dict(
                _require_object(
                    item,
                    field_name="booking.lines item",
                )
            )
            for item in _require_list(
                data.get("lines"),
                field_name="booking.lines",
            )
        ),
        voucher_no=_optional_string(
            data.get("voucher_no"),
            field_name="booking.voucher_no",
        ),
        description=_optional_string(
            data.get("description"),
            field_name="booking.description",
        ),
        reversal_of_booking_id=(
            None
            if reversal_value is None
            else _parse_uuid(
                reversal_value,
                field_name=(
                    "booking.reversal_of_booking_id"
                ),
            )
        ),
    )


def _fiscal_year_from_dict(
    data: JsonObject,
) -> ClientTransferFiscalYear:
    opening_source_value = data.get("opening_source")

    return ClientTransferFiscalYear(
        start_date=_parse_date(
            data.get("start_date"),
            field_name="fiscal_year.start_date",
        ),
        end_date=_parse_date(
            data.get("end_date"),
            field_name="fiscal_year.end_date",
        ),
        status=_require_string(
            data.get("status"),
            field_name="fiscal_year.status",
        ),
        opening_source=(
            None
            if opening_source_value is None
            else _fiscal_year_reference_from_dict(
                _require_object(
                    opening_source_value,
                    field_name=(
                        "fiscal_year.opening_source"
                    ),
                )
            )
        ),
        bookings=tuple(
            _booking_from_dict(
                _require_object(
                    item,
                    field_name="fiscal_year.bookings item",
                )
            )
            for item in _require_list(
                data.get("bookings", []),
                field_name="fiscal_year.bookings",
            )
        ),
    )


def _shareholder_from_dict(
    data: JsonObject,
) -> ClientTransferShareholder:
    return ClientTransferShareholder(
        shareholder_id=_parse_uuid(
            data.get("shareholder_id"),
            field_name="shareholder.shareholder_id",
        ),
        shareholder_number=_require_string(
            data.get("shareholder_number"),
            field_name="shareholder.shareholder_number",
        ),
        name=_require_string(
            data.get("name"),
            field_name="shareholder.name",
        ),
        legal_status=_require_string(
            data.get("legal_status"),
            field_name="shareholder.legal_status",
        ),
        share_numerator=_require_string(
            data.get("share_numerator"),
            field_name="shareholder.share_numerator",
        ),
        share_denominator=_require_string(
            data.get("share_denominator"),
            field_name="shareholder.share_denominator",
        ),
        first_name=_optional_string_with_default(
            data,
            "first_name",
        ),
        tax_number=_optional_string_with_default(
            data,
            "tax_number",
        ),
        tax_number_federal_state=(
            _optional_string_with_default(
                data,
                "tax_number_federal_state",
            )
        ),
        tax_id=_optional_string_with_default(
            data,
            "tax_id",
        ),
        wid=_optional_string_with_default(
            data,
            "wid",
        ),
    )


def _tax_adjustment_from_dict(
    data: JsonObject,
) -> ClientTransferTaxDepreciationAdjustment:
    return ClientTransferTaxDepreciationAdjustment(
        depreciation_id=_parse_uuid(
            data.get("depreciation_id"),
            field_name=(
                "tax_adjustment.depreciation_id"
            ),
        ),
        tax_amount=_require_string(
            data.get("tax_amount"),
            field_name="tax_adjustment.tax_amount",
        ),
    )


def _fixed_asset_depreciation_from_dict(
    data: JsonObject,
) -> ClientTransferFixedAssetDepreciation:
    tax_adjustment_value = data.get("tax_adjustment")

    return ClientTransferFixedAssetDepreciation(
        depreciation_id=_parse_uuid(
            data.get("depreciation_id"),
            field_name="depreciation.depreciation_id",
        ),
        fiscal_year_end=_parse_date(
            data.get("fiscal_year_end"),
            field_name="depreciation.fiscal_year_end",
        ),
        depreciation_date=_parse_date(
            data.get("depreciation_date"),
            field_name="depreciation.depreciation_date",
        ),
        amount=_require_string(
            data.get("amount"),
            field_name="depreciation.amount",
        ),
        booking_line=_booking_line_reference_from_dict(
            _require_object(
                data.get("booking_line"),
                field_name="depreciation.booking_line",
            )
        ),
        kind=_require_string(
            data.get("kind"),
            field_name="depreciation.kind",
        ),
        source=_require_string(
            data.get("source"),
            field_name="depreciation.source",
        ),
        tax_adjustment=(
            None
            if tax_adjustment_value is None
            else _tax_adjustment_from_dict(
                _require_object(
                    tax_adjustment_value,
                    field_name=(
                        "depreciation.tax_adjustment"
                    ),
                )
            )
        ),
    )


def _fixed_asset_movement_from_dict(
    data: JsonObject,
) -> ClientTransferFixedAssetMovement:
    reversed_value = data.get("reversed_movement_id")

    return ClientTransferFixedAssetMovement(
        movement_id=_parse_uuid(
            data.get("movement_id"),
            field_name="movement.movement_id",
        ),
        fiscal_year_end=_parse_date(
            data.get("fiscal_year_end"),
            field_name="movement.fiscal_year_end",
        ),
        movement_date=_parse_date(
            data.get("movement_date"),
            field_name="movement.movement_date",
        ),
        amount=_require_string(
            data.get("amount"),
            field_name="movement.amount",
        ),
        booking_line=_booking_line_reference_from_dict(
            _require_object(
                data.get("booking_line"),
                field_name="movement.booking_line",
            )
        ),
        movement_type=_require_string(
            data.get("movement_type"),
            field_name="movement.movement_type",
        ),
        reversed_movement_id=(
            None
            if reversed_value is None
            else _parse_uuid(
                reversed_value,
                field_name=(
                    "movement.reversed_movement_id"
                ),
            )
        ),
    )


def _fixed_asset_from_dict(
    data: JsonObject,
) -> ClientTransferFixedAsset:
    disposal_date_value = data.get("disposal_date")

    return ClientTransferFixedAsset(
        fixed_asset_id=_parse_uuid(
            data.get("fixed_asset_id"),
            field_name="fixed_asset.fixed_asset_id",
        ),
        asset_code=_require_string(
            data.get("asset_code"),
            field_name="fixed_asset.asset_code",
        ),
        description=_require_string(
            data.get("description"),
            field_name="fixed_asset.description",
        ),
        position_code=_require_string(
            data.get("position_code"),
            field_name="fixed_asset.position_code",
        ),
        asset_account_number=_require_string(
            data.get("asset_account_number"),
            field_name=(
                "fixed_asset.asset_account_number"
            ),
        ),
        depreciation_expense_account_number=(
            _require_string(
                data.get(
                    "depreciation_expense_account_number"
                ),
                field_name=(
                    "fixed_asset."
                    "depreciation_expense_account_number"
                ),
            )
        ),
        acquisition_date=_parse_date(
            data.get("acquisition_date"),
            field_name="fixed_asset.acquisition_date",
        ),
        acquisition_cost=_require_string(
            data.get("acquisition_cost"),
            field_name="fixed_asset.acquisition_cost",
        ),
        depreciation_start_date=_parse_date(
            data.get("depreciation_start_date"),
            field_name=(
                "fixed_asset.depreciation_start_date"
            ),
        ),
        useful_life_months=_require_int(
            data.get("useful_life_months"),
            field_name="fixed_asset.useful_life_months",
        ),
        status=_require_string(
            data.get("status"),
            field_name="fixed_asset.status",
        ),
        disposal_date=(
            None
            if disposal_date_value is None
            else _parse_date(
                disposal_date_value,
                field_name="fixed_asset.disposal_date",
            )
        ),
        movements=tuple(
            _fixed_asset_movement_from_dict(
                _require_object(
                    item,
                    field_name="fixed_asset.movements item",
                )
            )
            for item in _require_list(
                data.get("movements", []),
                field_name="fixed_asset.movements",
            )
        ),
        depreciations=tuple(
            _fixed_asset_depreciation_from_dict(
                _require_object(
                    item,
                    field_name=(
                        "fixed_asset.depreciations item"
                    ),
                )
            )
            for item in _require_list(
                data.get("depreciations", []),
                field_name="fixed_asset.depreciations",
            )
        ),
    )


def _profit_appropriation_annual_data_from_dict(
    data: JsonObject,
) -> ClientTransferProfitAppropriationAnnualData:
    return ClientTransferProfitAppropriationAnnualData(
        fiscal_year=_fiscal_year_reference_from_dict(
            _require_object(
                data.get("fiscal_year"),
                field_name=(
                    "profit_appropriation_annual_data."
                    "fiscal_year"
                ),
            )
        ),
        statutory_reserve_addition=_require_string(
            data.get("statutory_reserve_addition"),
            field_name="statutory_reserve_addition",
        ),
        other_revenue_reserves_addition=_require_string(
            data.get("other_revenue_reserves_addition"),
            field_name="other_revenue_reserves_addition",
        ),
        statutory_reserve_release=_require_string(
            data.get("statutory_reserve_release"),
            field_name="statutory_reserve_release",
        ),
        other_revenue_reserves_release=_require_string(
            data.get("other_revenue_reserves_release"),
            field_name="other_revenue_reserves_release",
        ),
        distribution=_require_string(
            data.get("distribution"),
            field_name="distribution",
        ),
        profit_loss_carryforward=_require_string(
            data.get("profit_loss_carryforward"),
            field_name="profit_loss_carryforward",
        ),
    )


def _profit_appropriation_posting_from_dict(
    data: JsonObject,
) -> ClientTransferProfitAppropriationPosting:
    return ClientTransferProfitAppropriationPosting(
        posting_id=_parse_uuid(
            data.get("posting_id"),
            field_name=(
                "profit_appropriation_posting.posting_id"
            ),
        ),
        source_fiscal_year=(
            _fiscal_year_reference_from_dict(
                _require_object(
                    data.get("source_fiscal_year"),
                    field_name=(
                        "profit_appropriation_posting."
                        "source_fiscal_year"
                    ),
                )
            )
        ),
        posting_date=_parse_date(
            data.get("posting_date"),
            field_name=(
                "profit_appropriation_posting.posting_date"
            ),
        ),
        amount=_require_string(
            data.get("amount"),
            field_name=(
                "profit_appropriation_posting.amount"
            ),
        ),
        booking_line=_booking_line_reference_from_dict(
            _require_object(
                data.get("booking_line"),
                field_name=(
                    "profit_appropriation_posting."
                    "booking_line"
                ),
            )
        ),
        posting_type=_require_string(
            data.get("posting_type"),
            field_name=(
                "profit_appropriation_posting.posting_type"
            ),
        ),
    )


def _equity_contribution_from_dict(
    data: JsonObject,
) -> ClientTransferEquityContribution:
    return ClientTransferEquityContribution(
        booking_line=_booking_line_reference_from_dict(
            _require_object(
                data.get("booking_line"),
                field_name=(
                    "equity_contribution.booking_line"
                ),
            )
        )
    )


def _client_from_dict(
    data: JsonObject,
) -> ClientTransferClient:
    control_value = data.get("control_accounts")
    vat_value = data.get("vat_accounts")

    return ClientTransferClient(
        company_id=_parse_uuid(
            data.get("company_id"),
            field_name="client.company_id",
        ),
        master_data=_master_data_from_dict(
            _require_object(
                data.get("master_data"),
                field_name="client.master_data",
            )
        ),
        accounts=tuple(
            _account_from_dict(
                _require_object(
                    item,
                    field_name="client.accounts item",
                )
            )
            for item in _require_list(
                data.get("accounts"),
                field_name="client.accounts",
            )
        ),
        control_accounts=(
            None
            if control_value is None
            else _control_accounts_from_dict(
                _require_object(
                    control_value,
                    field_name="client.control_accounts",
                )
            )
        ),
        vat_accounts=(
            None
            if vat_value is None
            else _vat_accounts_from_dict(
                _require_object(
                    vat_value,
                    field_name="client.vat_accounts",
                )
            )
        ),
        account_roles=_account_roles_from_dict(
            _require_object(
                data.get("account_roles"),
                field_name="client.account_roles",
            )
        ),
        taxonomy_mappings=tuple(
            _taxonomy_mapping_from_dict(
                _require_object(
                    item,
                    field_name=(
                        "client.taxonomy_mappings item"
                    ),
                )
            )
            for item in _require_list(
                data.get("taxonomy_mappings", []),
                field_name="client.taxonomy_mappings",
            )
        ),
        shareholders=tuple(
            _shareholder_from_dict(
                _require_object(
                    item,
                    field_name="client.shareholders item",
                )
            )
            for item in _require_list(
                data.get("shareholders", []),
                field_name="client.shareholders",
            )
        ),
        fixed_assets=tuple(
            _fixed_asset_from_dict(
                _require_object(
                    item,
                    field_name="client.fixed_assets item",
                )
            )
            for item in _require_list(
                data.get("fixed_assets", []),
                field_name="client.fixed_assets",
            )
        ),
        profit_appropriation_annual_data=tuple(
            _profit_appropriation_annual_data_from_dict(
                _require_object(
                    item,
                    field_name=(
                        "client."
                        "profit_appropriation_annual_data item"
                    ),
                )
            )
            for item in _require_list(
                data.get(
                    "profit_appropriation_annual_data",
                    [],
                ),
                field_name=(
                    "client.profit_appropriation_annual_data"
                ),
            )
        ),
        profit_appropriation_postings=tuple(
            _profit_appropriation_posting_from_dict(
                _require_object(
                    item,
                    field_name=(
                        "client."
                        "profit_appropriation_postings item"
                    ),
                )
            )
            for item in _require_list(
                data.get(
                    "profit_appropriation_postings",
                    [],
                ),
                field_name=(
                    "client.profit_appropriation_postings"
                ),
            )
        ),
        equity_contributions=tuple(
            _equity_contribution_from_dict(
                _require_object(
                    item,
                    field_name=(
                        "client.equity_contributions item"
                    ),
                )
            )
            for item in _require_list(
                data.get("equity_contributions", []),
                field_name="client.equity_contributions",
            )
        ),
        fiscal_years=tuple(
            _fiscal_year_from_dict(
                _require_object(
                    item,
                    field_name="client.fiscal_years item",
                )
            )
            for item in _require_list(
                data.get("fiscal_years", []),
                field_name="client.fiscal_years",
            )
        ),
    )


def _to_json_value(
    value: Any,
) -> Any:
    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _to_json_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (tuple, list)):
        return [
            _to_json_value(item)
            for item in value
        ]

    return value


def _require_object(
    value: object,
    *,
    field_name: str,
) -> JsonObject:
    if not isinstance(value, dict):
        raise ValueError(
            f"{field_name} must be a JSON object"
        )

    if not all(
        isinstance(key, str)
        for key in value
    ):
        raise ValueError(
            f"{field_name} must contain string keys"
        )

    return value


def _require_list(
    value: object,
    *,
    field_name: str,
) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(
            f"{field_name} must be a JSON array"
        )

    return value


def _require_string(
    value: object,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string"
        )

    return value


def _optional_string(
    value: object,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None

    return _require_string(
        value,
        field_name=field_name,
    )


def _optional_string_with_default(
    data: JsonObject,
    field_name: str,
) -> str:
    value = data.get(field_name, "")

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string"
        )

    return value


def _require_bool(
    value: object,
    *,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a boolean"
        )

    return value


def _require_int(
    value: object,
    *,
    field_name: str,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
    ):
        raise ValueError(
            f"{field_name} must be an integer"
        )

    return value


def _string_tuple(
    value: object,
    *,
    field_name: str,
) -> tuple[str, ...]:
    items = _require_list(
        value,
        field_name=field_name,
    )

    return tuple(
        _require_string(
            item,
            field_name=f"{field_name} item",
        )
        for item in items
    )


def _parse_uuid(
    value: object,
    *,
    field_name: str,
) -> UUID:
    text = _require_string(
        value,
        field_name=field_name,
    )

    try:
        return UUID(text)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a valid UUID"
        ) from exc


def _parse_date(
    value: object,
    *,
    field_name: str,
) -> date:
    text = _require_string(
        value,
        field_name=field_name,
    )

    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a valid ISO date"
        ) from exc


def _parse_datetime(
    value: object,
    *,
    field_name: str,
) -> datetime:
    text = _require_string(
        value,
        field_name=field_name,
    )

    try:
        result = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a valid ISO datetime"
        ) from exc

    if result.tzinfo is None:
        raise ValueError(
            f"{field_name} must include timezone information"
        )

    return result

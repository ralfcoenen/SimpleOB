"""Exportiert einen vollständigen Mandanten in das portable Transferformat."""

from datetime import datetime
from decimal import Decimal
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
from openbilanz.core.version import get_application_version
from openbilanz.database.booking_repository import (
    BookingRepository,
)
from openbilanz.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.equity_contribution_repository import (
    EquityContributionRepository,
)
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from openbilanz.database.profit_appropriation_annual_data_repository import (
    ProfitAppropriationAnnualDataRepository,
)
from openbilanz.database.profit_appropriation_posting_repository import (
    ProfitAppropriationPostingRepository,
)
from openbilanz.database.shareholder_repository import (
    ShareholderRepository,
)
from openbilanz.database.tax_depreciation_adjustment_repository import (
    TaxDepreciationAdjustmentRepository,
)


def _amount(value: Decimal) -> str:
    """Serialisiert einen Decimal-Wert verlustfrei."""

    return str(value)


class ClientTransferExporter:
    """Erzeugt einen vollständigen portablen Mandantenexport."""

    def __init__(
        self,
        *,
        company_repository: CompanyRepository,
        chart_of_accounts_repository: ChartOfAccountsRepository,
        booking_repository: BookingRepository,
        shareholder_repository: ShareholderRepository,
        fixed_asset_repository: FixedAssetRepository,
        fixed_asset_movement_repository: FixedAssetMovementRepository,
        fixed_asset_depreciation_repository: FixedAssetDepreciationRepository,
        tax_depreciation_adjustment_repository: (
            TaxDepreciationAdjustmentRepository
        ),
        profit_appropriation_annual_data_repository: (
            ProfitAppropriationAnnualDataRepository
        ),
        profit_appropriation_posting_repository: (
            ProfitAppropriationPostingRepository
        ),
        equity_contribution_repository: EquityContributionRepository,
    ) -> None:
        self._company_repository = company_repository
        self._chart_of_accounts_repository = (
            chart_of_accounts_repository
        )
        self._booking_repository = booking_repository
        self._shareholder_repository = shareholder_repository
        self._fixed_asset_repository = fixed_asset_repository
        self._fixed_asset_movement_repository = (
            fixed_asset_movement_repository
        )
        self._fixed_asset_depreciation_repository = (
            fixed_asset_depreciation_repository
        )
        self._tax_depreciation_adjustment_repository = (
            tax_depreciation_adjustment_repository
        )
        self._profit_appropriation_annual_data_repository = (
            profit_appropriation_annual_data_repository
        )
        self._profit_appropriation_posting_repository = (
            profit_appropriation_posting_repository
        )
        self._equity_contribution_repository = (
            equity_contribution_repository
        )

    def export(
        self,
        *,
        company_id: UUID,
        position_provider: Any,
    ) -> ClientTransfer:
        """Exportiert einen Mandanten vollständig."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        master_data = (
            self._company_repository.get_master_data(
                company_id
            )
        )

        if master_data is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )

        loaded_chart = (
            self._chart_of_accounts_repository
            .load_for_company(
                company_id=company_id,
                position_provider=position_provider,
            )
        )

        if loaded_chart is None:
            raise ValueError(
                "Für den Mandanten ist kein Kontenrahmen vorhanden."
            )

        chart_of_accounts, accounts = loaded_chart

        mapping_rules = {
            rule.account_number: rule
            for rule in chart_of_accounts.account_mapping_rules
        }

        transfer_accounts = tuple(
            self._build_account(
                account=account,
                mapping_rule=mapping_rules.get(
                    account.number
                ),
            )
            for account in accounts
        )

        control_accounts = (
            self._chart_of_accounts_repository
            .load_control_accounts(
                company_id
            )
        )

        vat_accounts = (
            self._chart_of_accounts_repository
            .load_vat_accounts(
                company_id
            )
        )

        account_roles = (
            self._chart_of_accounts_repository
            .load_account_roles(
                company_id
            )
        )

        if control_accounts is None:
            raise ValueError(
                "Steuerkonten des Mandanten fehlen."
            )

        if vat_accounts is None:
            raise ValueError(
                "Umsatzsteuerkonten des Mandanten fehlen."
            )

        managed_fiscal_years = (
            self._company_repository
            .get_managed_fiscal_years(
                company_id
            )
        )

        fiscal_year_references_by_end = {
            managed_fiscal_year.fiscal_year.end_date: (
                ClientTransferFiscalYearReference(
                    start_date=(
                        managed_fiscal_year
                        .fiscal_year.start_date
                    ),
                    end_date=(
                        managed_fiscal_year
                        .fiscal_year.end_date
                    ),
                )
            )
            for managed_fiscal_year
            in managed_fiscal_years
        }

        transfer_fiscal_years = tuple(
            self._build_fiscal_year(
                company_id=company_id,
                managed_fiscal_year=managed_fiscal_year,
            )
            for managed_fiscal_year
            in managed_fiscal_years
        )

        shareholders = tuple(
            self._build_shareholder(
                shareholder
            )
            for shareholder
            in self._shareholder_repository
            .list_for_company(
                company_id
            )
        )

        fixed_assets = tuple(
            self._build_fixed_asset(
                fixed_asset
            )
            for fixed_asset
            in self._fixed_asset_repository
            .list_for_company(
                company_id
            )
        )

        taxonomy_mappings = tuple(
            ClientTransferTaxonomyMapping(
                account_number=account_number,
                taxonomy_version=taxonomy_version,
                concept_name=concept_name,
            )
            for taxonomy_version, concepts
            in sorted(
                self._chart_of_accounts_repository
                .load_all_account_taxonomy_concepts(
                    company_id
                )
                .items()
            )
            for account_number, concept_name
            in sorted(
                concepts.items()
            )
        )

        profit_appropriation_annual_data = []
        profit_appropriation_postings = []
        equity_contributions = []

        for managed_fiscal_year in managed_fiscal_years:
            fiscal_year = managed_fiscal_year.fiscal_year

            annual_data = (
                self._profit_appropriation_annual_data_repository
                .get_for_fiscal_year(
                    company_id=company_id,
                    fiscal_year=fiscal_year,
                )
            )

            if annual_data is not None:
                profit_appropriation_annual_data.append(
                    self._build_profit_appropriation_annual_data(
                        fiscal_year=fiscal_year,
                        data=annual_data,
                    )
                )

            postings = (
                self._profit_appropriation_posting_repository
                .list_with_positions_for_source_fiscal_year(
                    company_id=company_id,
                    source_fiscal_year_end=(
                        fiscal_year.end_date
                    ),
                )
            )

            for posting, position in postings:
                source_fiscal_year = (
                    fiscal_year_references_by_end.get(
                        posting.source_fiscal_year_end
                    )
                )

                if source_fiscal_year is None:
                    raise ValueError(
                        "Quellgeschäftsjahr der "
                        "Ergebnisverwendungsbuchung "
                        "ist im Mandanten nicht vorhanden: "
                        f"{posting.source_fiscal_year_end}"
                    )

                profit_appropriation_postings.append(
                    self._build_profit_appropriation_posting(
                        posting=posting,
                        booking_line_position=position,
                        source_fiscal_year=(
                            source_fiscal_year
                        ),
                    )
                )

            contributions = (
                self._equity_contribution_repository
                .list_for_fiscal_year(
                    company_id=company_id,
                    fiscal_year=fiscal_year,
                )
            )

            equity_contributions.extend(
                ClientTransferEquityContribution(
                    booking_line=(
                        ClientTransferBookingLineReference(
                            booking_id=(
                                reference.booking_id
                            ),
                            position=(
                                reference
                                .booking_line_position
                            ),
                        )
                    ),
                )
                for reference in contributions
            )

        transfer = ClientTransfer(
            format=ClientTransferFormat(),
            application=ClientTransferApplication(
                name="SimpleOB",
                version=get_application_version(),
            ),
            exported_at=datetime.now().astimezone(),
            client=ClientTransferClient(
                company_id=company_id,
                master_data=ClientTransferMasterData(
                    name=master_data.company.name,
                    legal_form=master_data.legal_form,
                    tax_number=master_data.tax_number,
                    tax_office=master_data.tax_office,
                    tax_id=master_data.tax_id,
                    tax_economic_id=(
                        master_data.tax_economic_id
                    ),
                    bf4=master_data.bf4,
                    street=master_data.street,
                    house_number=master_data.house_number,
                    postal_code=master_data.postal_code,
                    city=master_data.city,
                    country=master_data.country,
                    federal_state=(
                        master_data.federal_state
                    ),
                    business=master_data.business,
                ),
                accounts=transfer_accounts,
                control_accounts=(
                    ClientTransferControlAccounts(
                        opening_balance_account=(
                            control_accounts
                            .opening_balance_account
                        ),
                        income_summary_account=(
                            control_accounts
                            .income_summary_account
                        ),
                        profit_account=(
                            control_accounts.profit_account
                        ),
                        loss_account=(
                            control_accounts.loss_account
                        ),
                        profit_loss_carryforward_account=(
                            control_accounts
                            .profit_loss_carryforward_account
                        ),
                        statutory_reserve_account=(
                            control_accounts
                            .statutory_reserve_account
                        ),
                        other_revenue_reserves_account=(
                            control_accounts
                            .other_revenue_reserves_account
                        ),
                        distribution_liability_account=(
                            control_accounts
                            .distribution_liability_account
                        ),
                        depreciation_expense_account=(
                            control_accounts
                            .depreciation_expense_account
                        ),
                        fixed_asset_disposal_gain_account=(
                            control_accounts
                            .fixed_asset_disposal_gain_account
                        ),
                        fixed_asset_disposal_loss_account=(
                            control_accounts
                            .fixed_asset_disposal_loss_account
                        ),
                    )
                ),
                vat_accounts=ClientTransferVatAccounts(
                    input_tax_7=(
                        vat_accounts.input_tax_7
                    ),
                    input_tax_19=(
                        vat_accounts.input_tax_19
                    ),
                    output_tax_7=(
                        vat_accounts.output_tax_7
                    ),
                    output_tax_19=(
                        vat_accounts.output_tax_19
                    ),
                ),
                account_roles=ClientTransferAccountRoles(
                    cash_accounts=tuple(
                        sorted(
                            account_roles.cash_accounts
                        )
                    ),
                    bank_accounts=tuple(
                        sorted(
                            account_roles.bank_accounts
                        )
                    ),
                    general_rate_sales_accounts=tuple(
                        sorted(
                            account_roles
                            .general_rate_sales_accounts
                        )
                    ),
                ),
                taxonomy_mappings=taxonomy_mappings,
                shareholders=shareholders,
                fiscal_years=transfer_fiscal_years,
                fixed_assets=fixed_assets,
                profit_appropriation_annual_data=tuple(
                    profit_appropriation_annual_data
                ),
                profit_appropriation_postings=tuple(
                    profit_appropriation_postings
                ),
                equity_contributions=tuple(
                    equity_contributions
                ),
            ),
        )

        validate_client_transfer_references(
            transfer
        )

        return transfer

    @staticmethod
    def _build_account(
        *,
        account: Any,
        mapping_rule: Any,
    ) -> ClientTransferAccount:
        return ClientTransferAccount(
            account_number=account.number,
            name=account.name,
            account_type=account.account_type.name,
            is_active=account.is_active,
            debit_position_code=(
                mapping_rule.debit_position.code
                if mapping_rule is not None
                and mapping_rule.debit_position
                is not None
                else None
            ),
            credit_position_code=(
                mapping_rule.credit_position.code
                if mapping_rule is not None
                and mapping_rule.credit_position
                is not None
                else None
            ),
        )

    def _build_fiscal_year(
        self,
        *,
        company_id: UUID,
        managed_fiscal_year: Any,
    ) -> ClientTransferFiscalYear:
        fiscal_year = managed_fiscal_year.fiscal_year

        bookings = (
            self._booking_repository
            .list_for_fiscal_year(
                company_id=company_id,
                fiscal_year=fiscal_year,
            )
        )

        return ClientTransferFiscalYear(
            start_date=fiscal_year.start_date,
            end_date=fiscal_year.end_date,
            status=managed_fiscal_year.status.value,
            opening_source=(
                ClientTransferFiscalYearReference(
                    start_date=(
                        managed_fiscal_year
                        .opening_source.start_date
                    ),
                    end_date=(
                        managed_fiscal_year
                        .opening_source.end_date
                    ),
                )
                if managed_fiscal_year.opening_source
                is not None
                else None
            ),
            bookings=tuple(
                ClientTransferBooking(
                    booking_id=booking.booking_id,
                    booking_date=booking.booking_date,
                    voucher_no=booking.voucher_no,
                    description=booking.description,
                    booking_type=(
                        booking.booking_type.value
                    ),
                    reversal_of_booking_id=(
                        booking.reversal_of_booking_id
                    ),
                    lines=tuple(
                        ClientTransferBookingLine(
                            position=position,
                            account_number=(
                                line.account_number
                            ),
                            side=line.side.value,
                            amount=_amount(
                                line.amount
                            ),
                        )
                        for position, line
                        in enumerate(booking.lines)
                    ),
                )
                for booking in bookings
            ),
        )

    @staticmethod
    def _build_shareholder(
        shareholder: Any,
    ) -> ClientTransferShareholder:
        return ClientTransferShareholder(
            shareholder_id=(
                shareholder.shareholder_id
            ),
            shareholder_number=(
                shareholder.shareholder_number
            ),
            name=shareholder.name,
            first_name=shareholder.first_name,
            legal_status=shareholder.legal_status,
            share_numerator=(
                shareholder.share_numerator
            ),
            share_denominator=(
                shareholder.share_denominator
            ),
            tax_number=shareholder.tax_number,
            tax_number_federal_state=(
                shareholder.tax_number_federal_state
            ),
            tax_id=shareholder.tax_id,
            wid=shareholder.wid,
        )

    def _build_fixed_asset(
        self,
        fixed_asset: Any,
    ) -> ClientTransferFixedAsset:
        movements = (
            self._fixed_asset_movement_repository
            .list_with_positions_for_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        )

        depreciations = (
            self._fixed_asset_depreciation_repository
            .list_with_positions_for_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        )

        return ClientTransferFixedAsset(
            fixed_asset_id=fixed_asset.fixed_asset_id,
            asset_code=fixed_asset.asset_code,
            description=fixed_asset.description,
            position_code=fixed_asset.position_code,
            asset_account_number=(
                fixed_asset.asset_account_number
            ),
            depreciation_expense_account_number=(
                fixed_asset
                .depreciation_expense_account_number
            ),
            acquisition_date=(
                fixed_asset.acquisition_date
            ),
            acquisition_cost=_amount(
                fixed_asset.acquisition_cost
            ),
            depreciation_start_date=(
                fixed_asset.depreciation_start_date
            ),
            useful_life_months=(
                fixed_asset.useful_life_months
            ),
            status=fixed_asset.status.value,
            disposal_date=fixed_asset.disposal_date,
            movements=tuple(
                ClientTransferFixedAssetMovement(
                    movement_id=movement.movement_id,
                    fiscal_year_end=(
                        movement.fiscal_year_end
                    ),
                    movement_date=(
                        movement.movement_date
                    ),
                    amount=_amount(
                        movement.amount
                    ),
                    booking_line=(
                        ClientTransferBookingLineReference(
                            booking_id=(
                                movement.booking_id
                            ),
                            position=position,
                        )
                    ),
                    movement_type=(
                        movement.movement_type.value
                    ),
                    reversed_movement_id=(
                        movement.reversed_movement_id
                    ),
                )
                for movement, position
                in movements
            ),
            depreciations=tuple(
                self._build_depreciation(
                    depreciation=depreciation,
                    booking_line_position=position,
                )
                for depreciation, position
                in depreciations
            ),
        )

    def _build_depreciation(
        self,
        *,
        depreciation: Any,
        booking_line_position: int,
    ) -> ClientTransferFixedAssetDepreciation:
        tax_adjustment = (
            self._tax_depreciation_adjustment_repository
            .get_for_depreciation(
                depreciation.depreciation_id
            )
        )

        return ClientTransferFixedAssetDepreciation(
            depreciation_id=(
                depreciation.depreciation_id
            ),
            fiscal_year_end=(
                depreciation.fiscal_year_end
            ),
            depreciation_date=(
                depreciation.depreciation_date
            ),
            amount=_amount(
                depreciation.amount
            ),
            booking_line=(
                ClientTransferBookingLineReference(
                    booking_id=(
                        depreciation.booking_id
                    ),
                    position=booking_line_position,
                )
            ),
            kind=depreciation.kind.value,
            source=depreciation.source.value,
            tax_adjustment=(
                ClientTransferTaxDepreciationAdjustment(
                    depreciation_id=(
                        depreciation.depreciation_id
                    ),
                    tax_amount=_amount(
                        tax_adjustment.tax_amount
                    ),
                )
                if tax_adjustment is not None
                else None
            ),
        )

    @staticmethod
    def _build_profit_appropriation_annual_data(
        *,
        fiscal_year: Any,
        data: Any,
    ) -> ClientTransferProfitAppropriationAnnualData:
        return ClientTransferProfitAppropriationAnnualData(
            fiscal_year=(
                ClientTransferFiscalYearReference(
                    start_date=fiscal_year.start_date,
                    end_date=fiscal_year.end_date,
                )
            ),
            statutory_reserve_addition=_amount(
                data.statutory_reserve_addition
            ),
            other_revenue_reserves_addition=_amount(
                data.other_revenue_reserves_addition
            ),
            statutory_reserve_release=_amount(
                data.statutory_reserve_release
            ),
            other_revenue_reserves_release=_amount(
                data.other_revenue_reserves_release
            ),
            distribution=_amount(
                data.distribution
            ),
            profit_loss_carryforward=_amount(
                data.profit_loss_carryforward
            ),
        )

    @staticmethod
    def _build_profit_appropriation_posting(
        *,
        posting: Any,
        booking_line_position: int,
        source_fiscal_year: (
            ClientTransferFiscalYearReference
        ),
    ) -> ClientTransferProfitAppropriationPosting:
        return ClientTransferProfitAppropriationPosting(
            posting_id=posting.posting_id,
            source_fiscal_year=source_fiscal_year,
            posting_date=posting.posting_date,
            amount=_amount(
                posting.amount
            ),
            booking_line=(
                ClientTransferBookingLineReference(
                    booking_id=posting.booking_id,
                    position=booking_line_position,
                )
            ),
            posting_type=posting.posting_type.value,
        )

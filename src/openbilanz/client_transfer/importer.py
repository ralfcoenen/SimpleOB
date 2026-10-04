"""Import eines portablen SimpleOB-Mandantentransfers."""

from collections import defaultdict
from decimal import Decimal

from openbilanz.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)
from openbilanz.client_transfer.model import (
    ClientTransfer,
    ClientTransferAccount,
    ClientTransferBooking,
)
from openbilanz.client_transfer.validation import (
    validate_client_transfer_references,
)
from openbilanz.database.booking_repository import (
    BookingRepository,
)
from openbilanz.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from openbilanz.database.company_repository import (
    CompanyRepository,
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
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.tax_depreciation_adjustment_repository import (
    TaxDepreciationAdjustmentRepository,
)
from openbilanz.domain.account import Account
from openbilanz.domain.account_mapping_rule import (
    AccountMappingRule,
)
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.depreciation_kind import DepreciationKind
from openbilanz.domain.depreciation_source import DepreciationSource
from openbilanz.domain.fixed_asset_depreciation import (
    FixedAssetDepreciation,
)
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_status import (
    FixedAssetStatus,
)
from openbilanz.domain.fixed_asset_movement import (
    FixedAssetMovement,
)
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from openbilanz.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from openbilanz.domain.profit_appropriation_posting import (
    ProfitAppropriationPosting,
)
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.domain.shareholder import Shareholder

class ClientTransferImporter:
    """Importiert einen portablen SimpleOB-Mandanten."""

    def __init__(
        self,
        *,
        company_repository: CompanyRepository,
        chart_of_accounts_repository: ChartOfAccountsRepository,
        booking_repository: BookingRepository,
        shareholder_repository: ShareholderRepository,
        fixed_asset_repository: FixedAssetRepository,
        fixed_asset_movement_repository: (
            FixedAssetMovementRepository
        ),
        fixed_asset_depreciation_repository: (
            FixedAssetDepreciationRepository
        ),
        tax_depreciation_adjustment_repository: (
            TaxDepreciationAdjustmentRepository
        ),
        profit_appropriation_annual_data_repository: (
            ProfitAppropriationAnnualDataRepository
        ),
        profit_appropriation_posting_repository: (
            ProfitAppropriationPostingRepository
        ),
    ) -> None:
        self._company_repository = company_repository
        self._chart_of_accounts_repository = (
            chart_of_accounts_repository
        )
        self._booking_repository = booking_repository
        self._shareholder_repository = (
            shareholder_repository
        )
        self._fixed_asset_repository = (
            fixed_asset_repository
        )
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

    def import_transfer(
        self,
        *,
        transfer: ClientTransfer,
        position_provider: FinancialStatementPositionProvider,
    ) -> None:
        """Importiert den bisher unterstützten Mandantenbestand."""

        if not isinstance(transfer, ClientTransfer):
            raise TypeError(
                "transfer must be a ClientTransfer"
            )

        validate_client_transfer_references(
            transfer
        )

        self._validate_supported_scope(
            transfer=transfer
        )

        company_id = transfer.client.company_id

        if (
            self._company_repository.get_master_data(
                company_id
            )
            is not None
        ):
            raise ValueError(
                "Ein Mandant mit dieser company_id "
                "ist bereits vorhanden."
            )

        try:
            company = Company(
                company_id=company_id,
                name=transfer.client.master_data.name,
            )

            self._company_repository.add(
                company,
                commit=False,
            )

            self._company_repository.save_master_data(
                self._build_master_data(
                    company=company,
                    transfer=transfer,
                ),
                commit=False,
            )

            for transfer_account in (
                transfer.client.accounts
            ):
                account, mapping_rule = (
                    self._build_account(
                        transfer_account=transfer_account,
                        position_provider=position_provider,
                    )
                )

                self._chart_of_accounts_repository.add_account(
                    company_id=company_id,
                    account=account,
                    mapping_rule=mapping_rule,
                    commit=False,
                )

            self._save_account_configuration(
                transfer=transfer
            )

            self._save_taxonomy_mappings(
                transfer=transfer
            )

            self._save_shareholders(
                transfer=transfer
            )

            self._save_fixed_assets(
                transfer=transfer
            )

            self._create_fiscal_years(
                transfer=transfer
            )

            self._save_bookings(
                transfer=transfer
            )

            self._save_fixed_asset_movements(
                transfer=transfer,
            )
            self._save_fixed_asset_depreciations(
                transfer=transfer,
            )

            self._save_tax_depreciation_adjustments(
                transfer=transfer,
            )

            self._save_profit_appropriation_annual_data(
                transfer=transfer,
            )

            self._save_profit_appropriation_postings(
                transfer=transfer,
            )

            self._set_opening_sources(
                transfer=transfer
            )

            self._close_fiscal_years(
                transfer=transfer
            )

            self._company_repository.commit()

        except Exception:
            self._company_repository.rollback()
            raise

    @staticmethod
    def _validate_supported_scope(
        *,
        transfer: ClientTransfer,
    ) -> None:
        client = transfer.client

        if client.equity_contributions:
            raise ValueError(
                "Der Import der Eigenkapitaleinlagen ist "
                "noch nicht implementiert."
            )

    @staticmethod
    def _build_master_data(
        *,
        company: Company,
        transfer: ClientTransfer,
    ) -> CompanyMasterData:
        data = transfer.client.master_data

        return CompanyMasterData(
            company=company,
            legal_form=data.legal_form,
            tax_number=data.tax_number,
            tax_office=data.tax_office,
            tax_id=data.tax_id,
            tax_economic_id=data.tax_economic_id,
            bf4=data.bf4,
            street=data.street,
            house_number=data.house_number,
            postal_code=data.postal_code,
            city=data.city,
            country=data.country,
            federal_state=data.federal_state,
            business=data.business,
        )

    @staticmethod
    def _build_account(
        *,
        transfer_account: ClientTransferAccount,
        position_provider: FinancialStatementPositionProvider,
    ) -> tuple[Account, AccountMappingRule | None]:
        try:
            account_type = AccountType[
                transfer_account.account_type
            ]
        except KeyError as exc:
            raise ValueError(
                "Unbekannter Kontotyp im "
                "Mandantentransfer: "
                f"{transfer_account.account_type}"
            ) from exc

        account = Account(
            template=TemplateAccount(
                account_number=(
                    transfer_account.account_number
                ),
                name=transfer_account.name,
                account_type=account_type,
            ),
            is_active=transfer_account.is_active,
        )

        debit_position = (
            position_provider.get(
                transfer_account.debit_position_code
            )
            if (
                transfer_account.debit_position_code
                is not None
            )
            else None
        )

        credit_position = (
            position_provider.get(
                transfer_account.credit_position_code
            )
            if (
                transfer_account.credit_position_code
                is not None
            )
            else None
        )

        if (
            debit_position is None
            and credit_position is None
        ):
            return account, None

        return (
            account,
            AccountMappingRule(
                account_number=account.number,
                debit_position=debit_position,
                credit_position=credit_position,
            ),
        )

    def _save_account_configuration(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        client = transfer.client
        company_id = client.company_id

        if client.control_accounts is not None:
            data = client.control_accounts

            self._chart_of_accounts_repository.save_control_accounts(
                company_id=company_id,
                control_accounts=AccountingControlAccounts(
                    opening_balance_account=(
                        data.opening_balance_account
                    ),
                    income_summary_account=(
                        data.income_summary_account
                    ),
                    profit_account=data.profit_account,
                    loss_account=data.loss_account,
                    profit_loss_carryforward_account=(
                        data.profit_loss_carryforward_account
                    ),
                    statutory_reserve_account=(
                        data.statutory_reserve_account
                    ),
                    other_revenue_reserves_account=(
                        data.other_revenue_reserves_account
                    ),
                    distribution_liability_account=(
                        data.distribution_liability_account
                    ),
                    depreciation_expense_account=(
                        data.depreciation_expense_account
                    ),
                    fixed_asset_disposal_gain_account=(
                        data.fixed_asset_disposal_gain_account
                    ),
                    fixed_asset_disposal_loss_account=(
                        data.fixed_asset_disposal_loss_account
                    ),
                ),
                commit=False,
            )

        if client.vat_accounts is not None:
            data = client.vat_accounts

            self._chart_of_accounts_repository.save_vat_accounts(
                company_id=company_id,
                vat_accounts=VatAccounts(
                    input_tax_7=data.input_tax_7,
                    input_tax_19=data.input_tax_19,
                    output_tax_7=data.output_tax_7,
                    output_tax_19=data.output_tax_19,
                ),
                commit=False,
            )

        roles = client.account_roles

        self._chart_of_accounts_repository.save_account_roles(
            company_id=company_id,
            account_roles=AccountingAccountRoles(
                cash_accounts=frozenset(
                    roles.cash_accounts
                ),
                bank_accounts=frozenset(
                    roles.bank_accounts
                ),
                general_rate_sales_accounts=frozenset(
                    roles.general_rate_sales_accounts
                ),
            ),
            commit=False,
        )

    def _save_taxonomy_mappings(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        mappings_by_version: dict[
            str,
            dict[str, str],
        ] = defaultdict(dict)

        for mapping in (
            transfer.client.taxonomy_mappings
        ):
            mappings_by_version[
                mapping.taxonomy_version
            ][mapping.account_number] = (
                mapping.concept_name
            )

        for (
            taxonomy_version,
            account_taxonomy_concepts,
        ) in sorted(
            mappings_by_version.items()
        ):
            self._chart_of_accounts_repository.save_account_taxonomy_concepts(
                company_id=transfer.client.company_id,
                taxonomy_version=taxonomy_version,
                account_taxonomy_concepts=(
                    account_taxonomy_concepts
                ),
                commit=False,
            )

    def _save_shareholders(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        company_id = transfer.client.company_id

        for data in transfer.client.shareholders:
            self._shareholder_repository.add(
                shareholder=Shareholder(
                    company_id=company_id,
                    shareholder_number=(
                        data.shareholder_number
                    ),
                    name=data.name,
                    first_name=data.first_name,
                    legal_status=data.legal_status,
                    share_numerator=data.share_numerator,
                    share_denominator=(
                        data.share_denominator
                    ),
                    tax_number=data.tax_number,
                    tax_number_federal_state=(
                        data.tax_number_federal_state
                    ),
                    tax_id=data.tax_id,
                    wid=data.wid,
                    shareholder_id=data.shareholder_id,
                ),
                commit=False,
            )

    def _save_fixed_assets(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        company_id = transfer.client.company_id

        for data in transfer.client.fixed_assets:
            self._fixed_asset_repository.add(
                fixed_asset=FixedAsset(
                    company_id=company_id,
                    asset_code=data.asset_code,
                    description=data.description,
                    position_code=data.position_code,
                    asset_account_number=(
                        data.asset_account_number
                    ),
                    depreciation_expense_account_number=(
                        data.depreciation_expense_account_number
                    ),
                    acquisition_date=data.acquisition_date,
                    acquisition_cost=Decimal(
                        data.acquisition_cost
                    ),
                    depreciation_start_date=(
                        data.depreciation_start_date
                    ),
                    useful_life_months=(
                        data.useful_life_months
                    ),
                    fixed_asset_id=data.fixed_asset_id,
                    status=FixedAssetStatus(
                        data.status
                    ),
                    disposal_date=data.disposal_date,
                ),
                commit=False,
            )

    def _create_fiscal_years(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        company_id = transfer.client.company_id

        for transfer_fiscal_year in (
            transfer.client.fiscal_years
        ):
            self._company_repository.add_fiscal_year(
                company_id,
                FiscalYear(
                    start_date=(
                        transfer_fiscal_year.start_date
                    ),
                    end_date=(
                        transfer_fiscal_year.end_date
                    ),
                ),
                commit=False,
            )

    def _save_bookings(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        company_id = transfer.client.company_id

        for transfer_fiscal_year in (
            transfer.client.fiscal_years
        ):
            fiscal_year = FiscalYear(
                start_date=(
                    transfer_fiscal_year.start_date
                ),
                end_date=(
                    transfer_fiscal_year.end_date
                ),
            )

            regular_bookings = tuple(
                booking
                for booking in transfer_fiscal_year.bookings
                if booking.booking_type != "REVERSAL"
            )

            reversal_bookings = tuple(
                booking
                for booking in transfer_fiscal_year.bookings
                if booking.booking_type == "REVERSAL"
            )

            for transfer_booking in (
                *regular_bookings,
                *reversal_bookings,
            ):
                self._booking_repository.add(
                    company_id=company_id,
                    fiscal_year=fiscal_year,
                    booking=self._build_booking(
                        transfer_booking=transfer_booking
                    ),
                    commit=False,
                )

    def _save_fixed_asset_movements(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        movements = [
            (fixed_asset, movement)
            for fixed_asset in transfer.client.fixed_assets
            for movement in fixed_asset.movements
        ]

        regular_movements = [
            (fixed_asset, movement)
            for fixed_asset, movement in movements
            if movement.movement_type != "REVERSAL"
        ]
        reversal_movements = [
            (fixed_asset, movement)
            for fixed_asset, movement in movements
            if movement.movement_type == "REVERSAL"
        ]

        for fixed_asset, movement in (
            regular_movements + reversal_movements
        ):
            self._fixed_asset_movement_repository.add(
                movement=FixedAssetMovement(
                    fixed_asset_id=(
                        fixed_asset.fixed_asset_id
                    ),
                    fiscal_year_end=(
                        movement.fiscal_year_end
                    ),
                    movement_date=movement.movement_date,
                    amount=Decimal(movement.amount),
                    booking_id=(
                        movement.booking_line.booking_id
                    ),
                    movement_type=FixedAssetMovementType(
                        movement.movement_type
                    ),
                    movement_id=movement.movement_id,
                    reversed_movement_id=(
                        movement.reversed_movement_id
                    ),
                ),
                booking_line_position=(
                    movement.booking_line.position
                ),
                commit=False,
            )

    @staticmethod
    def _build_booking(
        *,
        transfer_booking: ClientTransferBooking,
    ) -> Booking:
        try:
            booking_type = BookingType(
                transfer_booking.booking_type
            )
        except ValueError as exc:
            raise ValueError(
                "Unbekannter Buchungstyp im "
                "Mandantentransfer: "
                f"{transfer_booking.booking_type}"
            ) from exc

        ordered_lines = sorted(
            transfer_booking.lines,
            key=lambda line: line.position,
        )

        for expected_position, line in enumerate(
            ordered_lines
        ):
            if line.position != expected_position:
                raise ValueError(
                    "Buchungszeilen müssen fortlaufende "
                    "Positionen ab 0 besitzen."
                )

        return Booking(
            booking_date=transfer_booking.booking_date,
            lines=tuple(
                BookingLine(
                    account_number=line.account_number,
                    side=EntrySide.from_value(
                        line.side
                    ),
                    amount=Decimal(line.amount),
                )
                for line in ordered_lines
            ),
            voucher_no=transfer_booking.voucher_no,
            description=transfer_booking.description,
            booking_id=transfer_booking.booking_id,
            booking_type=booking_type,
            reversal_of_booking_id=(
                transfer_booking.reversal_of_booking_id
            ),
        )

    def _set_opening_sources(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        company_id = transfer.client.company_id

        for transfer_fiscal_year in (
            transfer.client.fiscal_years
        ):
            opening_source = (
                transfer_fiscal_year.opening_source
            )

            if opening_source is None:
                continue

            self._company_repository.set_opening_source(
                company_id=company_id,
                fiscal_year=FiscalYear(
                    start_date=(
                        transfer_fiscal_year.start_date
                    ),
                    end_date=(
                        transfer_fiscal_year.end_date
                    ),
                ),
                opening_source=FiscalYear(
                    start_date=opening_source.start_date,
                    end_date=opening_source.end_date,
                ),
                commit=False,
            )

    def _close_fiscal_years(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        company_id = transfer.client.company_id

        for transfer_fiscal_year in (
            transfer.client.fiscal_years
        ):
            if transfer_fiscal_year.status != "CLOSED":
                continue

            self._company_repository.close_fiscal_year(
                company_id=company_id,
                fiscal_year=FiscalYear(
                    start_date=(
                        transfer_fiscal_year.start_date
                    ),
                    end_date=(
                        transfer_fiscal_year.end_date
                    ),
                ),
                commit=False,
            )

    def _save_fixed_asset_depreciations(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        for fixed_asset in transfer.client.fixed_assets:
            for depreciation in fixed_asset.depreciations:
                self._fixed_asset_depreciation_repository.add(
                    depreciation=FixedAssetDepreciation(
                        fixed_asset_id=(
                            fixed_asset.fixed_asset_id
                        ),
                        fiscal_year_end=(
                            depreciation.fiscal_year_end
                        ),
                        depreciation_date=(
                            depreciation.depreciation_date
                        ),
                        amount=Decimal(
                            depreciation.amount
                        ),
                        booking_id=(
                            depreciation.booking_line.booking_id
                        ),
                        kind=DepreciationKind(
                            depreciation.kind
                        ),
                        source=DepreciationSource(
                            depreciation.source
                        ),
                        depreciation_id=(
                            depreciation.depreciation_id
                        ),
                    ),
                    booking_line_position=(
                        depreciation.booking_line.position
                    ),
                    commit=False,
                )

    def _save_tax_depreciation_adjustments(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        for fixed_asset in transfer.client.fixed_assets:
            for depreciation in fixed_asset.depreciations:
                adjustment = depreciation.tax_adjustment

                if adjustment is None:
                    continue

                self._tax_depreciation_adjustment_repository.save(
                    depreciation_id=(
                        depreciation.depreciation_id
                    ),
                    tax_amount=Decimal(
                        adjustment.tax_amount
                    ),
                    commit=False,
                )

    def _save_profit_appropriation_annual_data(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        company_id = transfer.client.company_id

        for data in (
            transfer.client.profit_appropriation_annual_data
        ):
            self._profit_appropriation_annual_data_repository.save_for_fiscal_year(
                company_id=company_id,
                fiscal_year=FiscalYear(
                    start_date=data.fiscal_year.start_date,
                    end_date=data.fiscal_year.end_date,
                ),
                data=ProfitAppropriationAnnualData(
                    statutory_reserve_addition=Decimal(
                        data.statutory_reserve_addition
                    ),
                    other_revenue_reserves_addition=Decimal(
                        data.other_revenue_reserves_addition
                    ),
                    statutory_reserve_release=Decimal(
                        data.statutory_reserve_release
                    ),
                    other_revenue_reserves_release=Decimal(
                        data.other_revenue_reserves_release
                    ),
                    distribution=Decimal(
                        data.distribution
                    ),
                    profit_loss_carryforward=Decimal(
                        data.profit_loss_carryforward
                    ),
                ),
                commit=False,
            )


    def _save_profit_appropriation_postings(
        self,
        *,
        transfer: ClientTransfer,
    ) -> None:
        company_id = transfer.client.company_id

        for data in (
            transfer.client.profit_appropriation_postings
        ):
            self._profit_appropriation_posting_repository.add(
                company_id=company_id,
                posting=ProfitAppropriationPosting(
                    source_fiscal_year_end=(
                        data.source_fiscal_year.end_date
                    ),
                    posting_date=data.posting_date,
                    amount=Decimal(data.amount),
                    booking_id=data.booking_line.booking_id,
                    posting_type=ProfitAppropriationPostingType(
                        data.posting_type
                    ),
                    posting_id=data.posting_id,
                ),
                booking_line_position=(
                    data.booking_line.position
                ),
                commit=False,
            )

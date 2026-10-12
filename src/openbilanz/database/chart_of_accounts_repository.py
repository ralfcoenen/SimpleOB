"""Repository für mandantenspezifische Kontenrahmen."""

from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from openbilanz.database.lock_error import DatabaseLockError

from openbilanz.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)
from openbilanz.database.models import (
    KontenrahmenKonfiguration,
    Kontenrolle,
    KontenTaxonomieZuordnung,
    Konto,
    Mandant,
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
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.domain.vat_accounts import VatAccounts


class ChartOfAccountsRepository:
    """Speichert und lädt den Kontenrahmen eines Mandanten."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def save_for_company(
        self,
        *,
        company_id: UUID,
        chart_of_accounts: ChartOfAccountsTemplate,
        accounts: tuple[Account, ...],
        commit: bool = True,
    ) -> None:
        """Speichert den vollständigen Kontenrahmen eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(
            chart_of_accounts,
            ChartOfAccountsTemplate,
        ):
            raise TypeError(
                "chart_of_accounts must be a "
                "ChartOfAccountsTemplate"
            )

        if not isinstance(accounts, tuple):
            raise TypeError(
                "accounts must be a tuple"
            )

        if not all(
            isinstance(account, Account)
            for account in accounts
        ):
            raise TypeError(
                "accounts must contain only Account objects"
            )

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )

        account_by_number = {
            account.number: account
            for account in accounts
        }

        template_numbers = {
            account.account_number
            for account in chart_of_accounts.accounts
        }

        if set(account_by_number) != template_numbers:
            raise ValueError(
                "Konten und Kontenrahmenvorlage stimmen "
                "nicht überein."
            )

        mapping_by_number: dict[
            str,
            AccountMappingRule,
        ] = {}

        for rule in (
            chart_of_accounts.account_mapping_rules
        ):
            if rule.account_number in mapping_by_number:
                raise ValueError(
                    "Für ein Konto ist mehr als eine "
                    "Zuordnungsregel vorhanden."
                )

            mapping_by_number[
                rule.account_number
            ] = rule

        (
            self._session.query(Konto)
            .filter(
                Konto.mandant_id
                == company_model.id
            )
            .delete(
                synchronize_session=False
            )
        )

        for template_account in (
            chart_of_accounts.accounts
        ):
            account = account_by_number[
                template_account.account_number
            ]

            rule = mapping_by_number.get(
                template_account.account_number
            )

            model = Konto(
                mandant_id=company_model.id,
                account_number=(
                    template_account.account_number
                ),
                name=template_account.name,
                account_type=(
                    template_account.account_type.name
                ),
                is_active=account.is_active,
                debit_position_code=(
                    rule.debit_position.code
                    if (
                        rule is not None
                        and rule.debit_position is not None
                    )
                    else None
                ),
                credit_position_code=(
                    rule.credit_position.code
                    if (
                        rule is not None
                        and rule.credit_position is not None
                    )
                    else None
                ),
            )

            self._session.add(model)

        if commit:
            self._session.commit()

    def add_account(
        self,
        *,
        company_id: UUID,
        account: Account,
        mapping_rule: AccountMappingRule | None,
        commit: bool = True,
    ) -> None:
        """Fügt dem Kontenrahmen eines Mandanten ein Konto hinzu."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(account, Account):
            raise TypeError(
                "account must be an Account"
            )

        if (
            mapping_rule is not None
            and not isinstance(
                mapping_rule,
                AccountMappingRule,
            )
        ):
            raise TypeError(
                "mapping_rule must be an "
                "AccountMappingRule or None"
            )

        if (
            mapping_rule is not None
            and mapping_rule.account_number
            != account.number
        ):
            raise ValueError(
                "Zuordnungsregel und Konto stimmen "
                "nicht überein."
            )

        company_model = self._lock_company(
            company_id
        )

        existing = (
            self._session.query(Konto)
            .filter(
                Konto.mandant_id
                == company_model.id,
                Konto.account_number
                == account.number,
            )
            .one_or_none()
        )

        if existing is not None:
            raise ValueError(
                "Das Konto ist bereits vorhanden."
            )

        model = Konto(
            mandant_id=company_model.id,
            account_number=account.number,
            name=account.name,
            account_type=account.account_type.name,
            is_active=account.is_active,
            debit_position_code=(
                mapping_rule.debit_position.code
                if (
                    mapping_rule is not None
                    and mapping_rule.debit_position
                    is not None
                )
                else None
            ),
            credit_position_code=(
                mapping_rule.credit_position.code
                if (
                    mapping_rule is not None
                    and mapping_rule.credit_position
                    is not None
                )
                else None
            ),
        )

        self._session.add(model)

        if commit:
            self._session.commit()

    def update_account(
        self,
        *,
        company_id: UUID,
        account: Account,
        mapping_rule: AccountMappingRule | None,
        commit: bool = True,
    ) -> None:
        """Aktualisiert ein vorhandenes Konto eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(account, Account):
            raise TypeError(
                "account must be an Account"
            )

        if (
            mapping_rule is not None
            and not isinstance(
                mapping_rule,
                AccountMappingRule,
            )
        ):
            raise TypeError(
                "mapping_rule must be an "
                "AccountMappingRule or None"
            )

        if (
            mapping_rule is not None
            and mapping_rule.account_number
            != account.number
        ):
            raise ValueError(
                "Zuordnungsregel und Konto stimmen "
                "nicht überein."
            )

        company_model = self._lock_company(
            company_id
        )

        model = (
            self._session.query(Konto)
            .filter(
                Konto.mandant_id
                == company_model.id,
                Konto.account_number
                == account.number,
            )
            .one_or_none()
        )

        if model is None:
            raise ValueError(
                "Das Konto ist nicht vorhanden."
            )

        model.name = account.name
        model.account_type = account.account_type.name
        model.is_active = account.is_active

        model.debit_position_code = (
            mapping_rule.debit_position.code
            if (
                mapping_rule is not None
                and mapping_rule.debit_position
                is not None
            )
            else None
        )

        model.credit_position_code = (
            mapping_rule.credit_position.code
            if (
                mapping_rule is not None
                and mapping_rule.credit_position
                is not None
            )
            else None
        )

        if commit:
            self._session.commit()

    def load_for_company(
        self,
        *,
        company_id: UUID,
        position_provider: (
            FinancialStatementPositionProvider
        ),
    ) -> tuple[
        ChartOfAccountsTemplate,
        tuple[Account, ...],
    ] | None:
        """Lädt den Kontenrahmen eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            return None

        models = (
            self._session.query(Konto)
            .filter(
                Konto.mandant_id
                == company_model.id
            )
            .order_by(
                Konto.account_number
            )
            .all()
        )

        if not models:
            return None

        template_accounts: list[
            TemplateAccount
        ] = []

        accounts: list[Account] = []

        mapping_rules: list[
            AccountMappingRule
        ] = []

        for model in models:
            try:
                account_type = AccountType[
                    model.account_type
                ]
            except KeyError as exc:
                raise ValueError(
                    "Unbekannter gespeicherter "
                    f"Kontotyp: {model.account_type!r}"
                ) from exc

            template_account = TemplateAccount(
                account_number=model.account_number,
                name=model.name,
                account_type=account_type,
            )

            template_accounts.append(
                template_account
            )

            accounts.append(
                Account(
                    template=template_account,
                    is_active=model.is_active,
                )
            )

            if (
                model.debit_position_code is None
                and model.credit_position_code is None
            ):
                continue

            try:
                debit_position = (
                    position_provider.get(
                        model.debit_position_code
                    )
                    if model.debit_position_code
                    else None
                )

                credit_position = (
                    position_provider.get(
                        model.credit_position_code
                    )
                    if model.credit_position_code
                    else None
                )
            except KeyError as exc:
                raise ValueError(
                    "Gespeicherte HGB-Zuordnung "
                    "ist unbekannt."
                ) from exc

            mapping_rules.append(
                AccountMappingRule(
                    account_number=(
                        model.account_number
                    ),
                    debit_position=debit_position,
                    credit_position=credit_position,
                )
            )

        chart_of_accounts = (
            ChartOfAccountsTemplate(
                name="Mandantenkontenrahmen",
                accounts=tuple(
                    template_accounts
                ),
                account_mapping_rules=tuple(
                    mapping_rules
                ),
            )
        )

        return (
            chart_of_accounts,
            tuple(accounts),
        )

    def save_control_accounts(
        self,
        *,
        company_id: UUID,
        control_accounts: AccountingControlAccounts,
        commit: bool = True,
    ) -> None:
        """Speichert die technischen Konten eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(
            control_accounts,
            AccountingControlAccounts,
        ):
            raise TypeError(
                "control_accounts must be "
                "AccountingControlAccounts"
            )

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )

        self._session.flush()

        account_numbers = {
            model.account_number
            for model in (
                self._session.query(Konto)
                .filter(
                    Konto.mandant_id
                    == company_model.id
                )
                .all()
            )
        }

        missing_accounts = (
            control_accounts.technical_account_numbers
            - account_numbers
        )

        if missing_accounts:
            missing = ", ".join(
                sorted(missing_accounts)
            )

            raise ValueError(
                "Technische Konten sind im "
                "Kontenrahmen nicht vorhanden: "
                f"{missing}"
            )

        model = (
            self._session.query(
                KontenrahmenKonfiguration
            )
            .filter(
                KontenrahmenKonfiguration.mandant_id
                == company_model.id
            )
            .one_or_none()
        )

        if model is None:
            model = KontenrahmenKonfiguration(
                mandant_id=company_model.id,
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
                    control_accounts.statutory_reserve_account
                ),
                other_revenue_reserves_account=(
                    control_accounts.other_revenue_reserves_account
                ),
                distribution_liability_account=(
                    control_accounts.distribution_liability_account
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
                input_tax_7="1571",
                input_tax_19="1576",
                output_tax_7="1771",
                output_tax_19="1776",
            )

            self._session.add(model)
        else:
            model.opening_balance_account = (
                control_accounts
                .opening_balance_account
            )
            model.income_summary_account = (
                control_accounts
                .income_summary_account
            )
            model.profit_account = (
                control_accounts.profit_account
            )
            model.loss_account = (
                control_accounts.loss_account
            )
            model.profit_loss_carryforward_account = (
                control_accounts
                .profit_loss_carryforward_account
            )
            model.statutory_reserve_account = (
                control_accounts.statutory_reserve_account
            )
            model.other_revenue_reserves_account = (
                control_accounts.other_revenue_reserves_account
            )
            model.distribution_liability_account = (
                control_accounts.distribution_liability_account
            )
            model.depreciation_expense_account = (
                control_accounts
                .depreciation_expense_account
            )
            model.fixed_asset_disposal_gain_account = (
                control_accounts
                .fixed_asset_disposal_gain_account
            )
            model.fixed_asset_disposal_loss_account = (
                control_accounts
                .fixed_asset_disposal_loss_account
            )

        if commit:
            self._session.commit()

    def save_vat_accounts(
        self,
        *,
        company_id: UUID,
        vat_accounts: VatAccounts,
        commit: bool = True,
    ) -> None:
        """Speichert die Umsatzsteuerkonten eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(vat_accounts, VatAccounts):
            raise TypeError(
                "vat_accounts must be VatAccounts"
            )

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )

        self._session.flush()

        account_numbers = {
            model.account_number
            for model in (
                self._session.query(Konto)
                .filter(
                    Konto.mandant_id
                    == company_model.id
                )
                .all()
            )
        }

        missing_accounts = (
            vat_accounts.account_numbers
            - account_numbers
        )

        if missing_accounts:
            missing = ", ".join(
                sorted(missing_accounts)
            )

            raise ValueError(
                "Umsatzsteuerkonten sind im "
                "Kontenrahmen nicht vorhanden: "
                f"{missing}"
            )

        model = (
            self._session.query(
                KontenrahmenKonfiguration
            )
            .filter(
                KontenrahmenKonfiguration.mandant_id
                == company_model.id
            )
            .one_or_none()
        )

        if model is None:
            raise ValueError(
                "Die Kontenrahmenkonfiguration "
                "ist nicht vorhanden."
            )

        model.input_tax_7 = (
            vat_accounts.input_tax_7
        )
        model.input_tax_19 = (
            vat_accounts.input_tax_19
        )
        model.output_tax_7 = (
            vat_accounts.output_tax_7
        )
        model.output_tax_19 = (
            vat_accounts.output_tax_19
        )

        if commit:
            self._session.commit()

    def load_control_accounts(
        self,
        company_id: UUID,
    ) -> AccountingControlAccounts | None:
        """Lädt die technischen Konten eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            return None

        model = (
            self._session.query(
                KontenrahmenKonfiguration
            )
            .filter(
                KontenrahmenKonfiguration.mandant_id
                == company_model.id
            )
            .one_or_none()
        )

        if model is None:
            return None

        return AccountingControlAccounts(
            opening_balance_account=(
                model.opening_balance_account
            ),
            income_summary_account=(
                model.income_summary_account
            ),
            profit_account=model.profit_account,
            loss_account=model.loss_account,
            profit_loss_carryforward_account=(
                model.profit_loss_carryforward_account
            ),
            statutory_reserve_account=(
                model.statutory_reserve_account
            ),
            other_revenue_reserves_account=(
                model.other_revenue_reserves_account
            ),
            distribution_liability_account=(
                model.distribution_liability_account
            ),
            depreciation_expense_account=(
                model.depreciation_expense_account
            ),
            fixed_asset_disposal_gain_account=(
                model.fixed_asset_disposal_gain_account
            ),
            fixed_asset_disposal_loss_account=(
                model.fixed_asset_disposal_loss_account
            ),
        )

    def load_vat_accounts(
        self,
        company_id: UUID,
    ) -> VatAccounts | None:
        """Lädt die Umsatzsteuerkonten eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            return None

        model = (
            self._session.query(
                KontenrahmenKonfiguration
            )
            .filter(
                KontenrahmenKonfiguration.mandant_id
                == company_model.id
            )
            .one_or_none()
        )

        if model is None:
            return None

        return VatAccounts(
            input_tax_7=model.input_tax_7,
            input_tax_19=model.input_tax_19,
            output_tax_7=model.output_tax_7,
            output_tax_19=model.output_tax_19,
        )

    def save_single_account_taxonomy_concept(
        self,
        *,
        company_id: UUID,
        taxonomy_version: str,
        account_number: str,
        concept_name: str | None,
    ) -> None:
        """Speichert oder entfernt die Taxonomiezuordnung eines einzelnen Kontos."""

        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")

        if not isinstance(taxonomy_version, str):
            raise TypeError("taxonomy_version must be a str")

        if not isinstance(account_number, str):
            raise TypeError("account_number must be a str")

        if concept_name is not None and not isinstance(concept_name, str):
            raise TypeError("concept_name must be a str or None")

        taxonomy_version = taxonomy_version.strip()
        account_number = account_number.strip()

        if not taxonomy_version:
            raise ValueError("taxonomy_version must not be empty")

        if not account_number:
            raise ValueError("account_number must not be empty")

        if concept_name is not None:
            concept_name = concept_name.strip()

            if not concept_name:
                raise ValueError("concept_name must not be empty")

        try:
            company_model = self._lock_company(company_id)

            account_exists = (
                self._session.query(Konto.id)
                .filter(
                    Konto.mandant_id == company_model.id,
                    Konto.account_number == account_number,
                )
                .first()
                is not None
            )

            if not account_exists:
                raise ValueError(
                    f"Konto {account_number} ist im Kontenrahmen "
                    "nicht vorhanden."
                )

            existing_mapping = (
                self._session.query(KontenTaxonomieZuordnung)
                .filter(
                    KontenTaxonomieZuordnung.mandant_id == company_model.id,
                    KontenTaxonomieZuordnung.taxonomy_version == taxonomy_version,
                    KontenTaxonomieZuordnung.account_number == account_number,
                )
                .one_or_none()
            )

            if concept_name is None:
                if existing_mapping is not None:
                    self._session.delete(existing_mapping)

            elif existing_mapping is None:
                self._session.add(
                    KontenTaxonomieZuordnung(
                        mandant_id=company_model.id,
                        account_number=account_number,
                        taxonomy_version=taxonomy_version,
                        concept_name=concept_name,
                    )
                )

            else:
                existing_mapping.concept_name = concept_name

            self._session.commit()

        except Exception:
            self._session.rollback()
            raise

    def save_account_taxonomy_concepts(
        self,
        *,
        company_id: UUID,
        taxonomy_version: str,
        account_taxonomy_concepts: dict[str, str],
        commit: bool = True,
    ) -> None:
        """Speichert Taxonomiezuordnungen von Mandantenkonten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(taxonomy_version, str):
            raise TypeError(
                "taxonomy_version must be a str"
            )

        taxonomy_version = taxonomy_version.strip()

        if not taxonomy_version:
            raise ValueError(
                "taxonomy_version must not be empty"
            )

        if not isinstance(
            account_taxonomy_concepts,
            dict,
        ):
            raise TypeError(
                "account_taxonomy_concepts must be a dict"
            )

        normalized_concepts: dict[str, str] = {}

        for account_number, concept_name in (
            account_taxonomy_concepts.items()
        ):
            if not isinstance(account_number, str):
                raise TypeError(
                    "account numbers must be strings"
                )

            if not isinstance(concept_name, str):
                raise TypeError(
                    "taxonomy concept names must be strings"
                )

            normalized_account_number = (
                account_number.strip()
            )
            normalized_concept_name = (
                concept_name.strip()
            )

            if not normalized_account_number:
                raise ValueError(
                    "account numbers must not be empty"
                )

            if not normalized_concept_name:
                raise ValueError(
                    "taxonomy concept names must not be empty"
                )

            normalized_concepts[
                normalized_account_number
            ] = normalized_concept_name

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )

        self._session.flush()

        account_numbers = {
            model.account_number
            for model in (
                self._session.query(Konto)
                .filter(
                    Konto.mandant_id
                    == company_model.id
                )
                .all()
            )
        }

        missing_accounts = (
            set(normalized_concepts)
            - account_numbers
        )

        if missing_accounts:
            missing = ", ".join(
                sorted(missing_accounts)
            )

            raise ValueError(
                "Konten für Taxonomiezuordnungen "
                "sind im Kontenrahmen nicht vorhanden: "
                f"{missing}"
            )

        (
            self._session.query(
                KontenTaxonomieZuordnung
            )
            .filter(
                KontenTaxonomieZuordnung.mandant_id
                == company_model.id,
                KontenTaxonomieZuordnung.taxonomy_version
                == taxonomy_version,
            )
            .delete(
                synchronize_session=False
            )
        )

        for account_number, concept_name in (
            sorted(normalized_concepts.items())
        ):
            self._session.add(
                KontenTaxonomieZuordnung(
                    mandant_id=company_model.id,
                    account_number=account_number,
                    taxonomy_version=taxonomy_version,
                    concept_name=concept_name,
                )
            )

        if commit:
            self._session.commit()

    def load_account_taxonomy_concepts(
        self,
        company_id: UUID,
        *,
        taxonomy_version: str,
    ) -> dict[str, str]:
        """Lädt Taxonomiezuordnungen von Mandantenkonten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(taxonomy_version, str):
            raise TypeError(
                "taxonomy_version must be a str"
            )

        taxonomy_version = taxonomy_version.strip()

        if not taxonomy_version:
            raise ValueError(
                "taxonomy_version must not be empty"
            )

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            return {}

        models = (
            self._session.query(
                KontenTaxonomieZuordnung
            )
            .filter(
                KontenTaxonomieZuordnung.mandant_id
                == company_model.id,
                KontenTaxonomieZuordnung.taxonomy_version
                == taxonomy_version,
            )
            .order_by(
                KontenTaxonomieZuordnung.account_number
            )
            .all()
        )

        return {
            model.account_number: model.concept_name
            for model in models
        }

    def load_all_account_taxonomy_concepts(
        self,
        company_id: UUID,
    ) -> dict[str, dict[str, str]]:
        """Lädt alle Taxonomiezuordnungen eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            return {}

        models = (
            self._session.query(
                KontenTaxonomieZuordnung
            )
            .filter(
                KontenTaxonomieZuordnung.mandant_id
                == company_model.id
            )
            .order_by(
                KontenTaxonomieZuordnung.taxonomy_version,
                KontenTaxonomieZuordnung.account_number,
            )
            .all()
        )

        result: dict[str, dict[str, str]] = {}

        for model in models:
            concepts = result.setdefault(
                model.taxonomy_version,
                {},
            )
            concepts[model.account_number] = (
                model.concept_name
            )

        return result

    def save_account_roles(
        self,
        *,
        company_id: UUID,
        account_roles: AccountingAccountRoles,
        commit: bool = True,
    ) -> None:
        """Speichert fachliche Kontenrollen eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(
            account_roles,
            AccountingAccountRoles,
        ):
            raise TypeError(
                "account_roles must be "
                "AccountingAccountRoles"
            )

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )

        self._session.flush()

        account_numbers = {
            model.account_number
            for model in (
                self._session.query(Konto)
                .filter(
                    Konto.mandant_id
                    == company_model.id
                )
                .all()
            )
        }

        missing_accounts = (
            account_roles.account_numbers
            - account_numbers
        )

        if missing_accounts:
            missing = ", ".join(
                sorted(missing_accounts)
            )

            raise ValueError(
                "Konten mit fachlichen Rollen sind im "
                "Kontenrahmen nicht vorhanden: "
                f"{missing}"
            )

        (
            self._session.query(Kontenrolle)
            .filter(
                Kontenrolle.mandant_id
                == company_model.id
            )
            .delete(
                synchronize_session=False
            )
        )

        role_assignments = (
            (
                "CASH",
                account_roles.cash_accounts,
            ),
            (
                "BANK",
                account_roles.bank_accounts,
            ),
            (
                "GENERAL_RATE_SALES",
                account_roles.general_rate_sales_accounts,
            ),
        )

        for role, role_account_numbers in role_assignments:
            for account_number in sorted(
                role_account_numbers
            ):
                self._session.add(
                    Kontenrolle(
                        mandant_id=company_model.id,
                        role=role,
                        account_number=account_number,
                    )
                )

        if commit:
            self._session.commit()


    def save_account_configuration(
        self,
        *,
        company_id: UUID,
        control_accounts: AccountingControlAccounts,
        vat_accounts: VatAccounts,
        account_roles: AccountingAccountRoles,
    ) -> None:
        """Speichert die Kontenkonfiguration eines Mandanten atomar."""

        self._lock_company(company_id)

        try:
            self.save_control_accounts(
                company_id=company_id,
                control_accounts=control_accounts,
                commit=False,
            )
            self.save_vat_accounts(
                company_id=company_id,
                vat_accounts=vat_accounts,
                commit=False,
            )
            self.save_account_roles(
                company_id=company_id,
                account_roles=account_roles,
                commit=False,
            )

            self._session.commit()

        except Exception:
            self._session.rollback()
            raise


    def load_account_roles(
        self,
        company_id: UUID,
    ) -> AccountingAccountRoles | None:
        """Lädt fachliche Kontenrollen eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            return None

        models = (
            self._session.query(Kontenrolle)
            .filter(
                Kontenrolle.mandant_id
                == company_model.id
            )
            .all()
        )

        if not models:
            return AccountingAccountRoles(
                cash_accounts=frozenset(),
                bank_accounts=frozenset(),
                general_rate_sales_accounts=frozenset(),
            )

        cash_accounts = frozenset(
            model.account_number
            for model in models
            if model.role == "CASH"
        )

        bank_accounts = frozenset(
            model.account_number
            for model in models
            if model.role == "BANK"
        )

        general_rate_sales_accounts = frozenset(
            model.account_number
            for model in models
            if model.role == "GENERAL_RATE_SALES"
        )

        known_roles = {
            "CASH",
            "BANK",
            "GENERAL_RATE_SALES",
        }

        unknown_roles = {
            model.role
            for model in models
            if model.role not in known_roles
        }

        if unknown_roles:
            roles = ", ".join(
                sorted(unknown_roles)
            )

            raise ValueError(
                "Unbekannte fachliche Kontenrollen "
                f"gespeichert: {roles}"
            )

        return AccountingAccountRoles(
            cash_accounts=cash_accounts,
            bank_accounts=bank_accounts,
            general_rate_sales_accounts=(
                general_rate_sales_accounts
            ),
        )

    def lock_company(
        self,
        company_id: UUID,
    ) -> None:
        """Sperrt den Mandanten für eine gemeinsame Transaktion."""

        self._lock_company(company_id)

    def _lock_company(
        self,
        company_id: UUID,
    ) -> Mandant:
        """Sperrt einen Mandanten für Änderungen am Kontenrahmen."""

        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")

        is_postgresql = (
            self._session.get_bind().dialect.name
            == "postgresql"
        )

        if is_postgresql:
            self._session.execute(
                text(
                    "SELECT set_config("
                    "'lock_timeout', '3000ms', true)"
                )
            )

        query = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id == str(company_id)
            )
        )

        if is_postgresql:
            query = (
                query
                .with_for_update(of=Mandant)
                .populate_existing()
            )

        try:
            company_model = query.one_or_none()

        except OperationalError as exc:
            sqlstate = getattr(
                exc.orig,
                "sqlstate",
                None,
            )

            if is_postgresql and sqlstate == "55P03":
                self._session.rollback()

                raise DatabaseLockError(
                    "Kontenverwaltung momentan gesperrt.\n\n"
                    "Ein anderer Benutzer bearbeitet derzeit "
                    "die Konten dieses Mandanten.\n\n"
                    "Ihr Vorgang konnte nicht abgeschlossen "
                    "werden. Es wurden keine Änderungen "
                    "gespeichert.\n\n"
                    "Bitte versuchen Sie es in einigen "
                    "Sekunden erneut."
                ) from exc

            raise

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )

        return company_model

    def _find_company(
        self,
        company_id: UUID,
    ) -> Mandant | None:
        """Lädt das persistierte Unternehmen."""

        return (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id
                == str(company_id)
            )
            .one_or_none()
        )

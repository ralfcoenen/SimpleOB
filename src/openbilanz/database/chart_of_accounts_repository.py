"""Repository für mandantenspezifische Kontenrahmen."""

from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)
from openbilanz.database.models import (
    KontenrahmenKonfiguration,
    Konto,
    Mandant,
)
from openbilanz.domain.account import Account
from openbilanz.domain.account_mapping_rule import (
    AccountMappingRule,
)
from openbilanz.domain.account_type import AccountType
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

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
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

        company_model = self._find_company(
            company_id
        )

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
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

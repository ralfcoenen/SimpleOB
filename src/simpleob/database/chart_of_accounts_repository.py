"""Repository für mandantenspezifische Kontenrahmen."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from simpleob.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)
from simpleob.database.lock_error import DatabaseLockError
from simpleob.database.models import (
    Anlagegut,
    Buchung,
    Buchungszeile,
    KontenrahmenKonfiguration,
    Kontenrolle,
    KontenTaxonomieZuordnung,
    Konto,
    Mandant,
    PersonenkontoZuordnung,
    Wirtschaftsjahr,
)
from simpleob.domain.account import Account
from simpleob.domain.account_mapping_rule import (
    AccountMappingRule,
)
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from simpleob.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.domain.vat_accounts import VatAccounts


class ChartOfAccountsRepository:
    """Speichert und lädt den Kontenrahmen eines Mandanten."""

    _CONFIGURATION_REFERENCE_LABELS = {
        "opening_balance_account": "Eröffnungsbilanzkonto",
        "income_summary_account": "GuV-Sammelkonto",
        "profit_account": "Jahresüberschusskonto",
        "loss_account": "Jahresfehlbetragskonto",
        "profit_loss_carryforward_account": "Gewinn-/Verlustvortragskonto",
        "statutory_reserve_account": "Gesetzliche Rücklage",
        "other_revenue_reserves_account": "Andere Gewinnrücklagen",
        "distribution_liability_account": "Ausschüttungsverbindlichkeit",
        "depreciation_expense_account": "Abschreibungsaufwand",
        "fixed_asset_disposal_gain_account": "Erträge aus Anlagenabgängen",
        "fixed_asset_disposal_loss_account": "Aufwendungen aus Anlagenabgängen",
        "input_tax_7": "Vorsteuerkonto 7 %",
        "input_tax_19": "Vorsteuerkonto 19 %",
        "output_tax_7": "Umsatzsteuerkonto 7 %",
        "output_tax_19": "Umsatzsteuerkonto 19 %",
    }

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

        if self._session.query(PersonenkontoZuordnung.id).filter(
            PersonenkontoZuordnung.mandant_id == company_model.id
        ).first() is not None:
            raise ValueError(
                "Der Kontenrahmen kann nicht vollständig ersetzt werden, "
                "solange dauerhaft zugeordnete Personenkonten vorhanden sind."
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

        person_account = (
            self._session.query(PersonenkontoZuordnung.id)
            .filter(
                PersonenkontoZuordnung.mandant_id == company_model.id,
                PersonenkontoZuordnung.account_number == account.number,
            )
            .first()
        )
        if person_account is not None:
            raise ValueError(
                "Personenkonten müssen über die Personenkontenverwaltung "
                "bearbeitet werden."
            )

        if (
            model.account_type != account.account_type.name
            and self.account_has_bookings(
                company_id=company_id,
                account_number=account.number,
            )
        ):
            raise ValueError(
                "Der Kontotyp kann nicht geändert werden, weil das Konto "
                "in Buchungen eines Geschäftsjahres verwendet wird."
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

    def account_has_bookings(
        self,
        *,
        company_id: UUID,
        account_number: str,
    ) -> bool:
        """Prüft Buchungsreferenzen in allen Geschäftsjahren des Mandanten."""

        company_model = self._lock_company(company_id)
        return (
            self._session.query(Buchungszeile.id)
            .join(Buchung, Buchung.id == Buchungszeile.buchung_id)
            .join(
                Wirtschaftsjahr,
                Wirtschaftsjahr.id == Buchung.wirtschaftsjahr_id,
            )
            .filter(
                Wirtschaftsjahr.mandant_id == company_model.id,
                Buchungszeile.account_number == account_number,
            )
            .first()
            is not None
        )

    def save_account_with_taxonomy_mapping(
        self,
        *,
        company_id: UUID,
        account: Account,
        mapping_rule: AccountMappingRule | None,
        taxonomy_version: str,
        taxonomy_concept_name: str | None,
        is_new: bool,
    ) -> None:
        """Speichert Konto, HGB-Regel und Taxonomiezuordnung atomar."""

        try:
            save_account = self.add_account if is_new else self.update_account
            save_account(
                company_id=company_id,
                account=account,
                mapping_rule=mapping_rule,
                commit=False,
            )
            self.save_single_account_taxonomy_concept(
                company_id=company_id,
                taxonomy_version=taxonomy_version,
                account_number=account.number,
                concept_name=taxonomy_concept_name,
                commit=False,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def delete_accounts(
        self,
        *,
        company_id: UUID,
        account_numbers: tuple[str, ...],
    ) -> dict[str, tuple[str, ...]]:
        """Löscht unbenutzte Konten und ihre Taxonomiezuordnungen atomar.

        Liefert Sperrgründe je Konto zurück. Wenn mindestens ein Konto
        fachlich verwendet wird, bleibt die gesamte Auswahl unverändert.
        """

        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")
        if not isinstance(account_numbers, tuple) or not all(
            isinstance(number, str) for number in account_numbers
        ):
            raise TypeError("account_numbers must be a tuple of strings")

        numbers = tuple(dict.fromkeys(number.strip() for number in account_numbers))
        if not numbers or any(not number for number in numbers):
            raise ValueError("Mindestens eine gültige Kontonummer ist erforderlich.")

        try:
            company_model = self._lock_company(company_id)
            accounts = (
                self._session.query(Konto)
                .filter(
                    Konto.mandant_id == company_model.id,
                    Konto.account_number.in_(numbers),
                )
                .all()
            )
            account_by_number = {
                account.account_number: account for account in accounts
            }
            missing = set(numbers) - account_by_number.keys()
            if missing:
                raise ValueError(
                    "Folgende Konten sind nicht vorhanden: "
                    + ", ".join(sorted(missing))
                )
            total_accounts = (
                self._session.query(Konto.id)
                .filter(Konto.mandant_id == company_model.id)
                .count()
            )
            if total_accounts - len(numbers) < 1:
                raise ValueError(
                    "Ein Kontenrahmen muss mindestens ein Konto enthalten."
                )

            dependencies: dict[str, set[str]] = {
                number: set() for number in numbers
            }
            for person_account in (
                self._session.query(PersonenkontoZuordnung)
                .filter(
                    PersonenkontoZuordnung.mandant_id == company_model.id,
                    PersonenkontoZuordnung.account_number.in_(numbers),
                )
                .all()
            ):
                dependencies[person_account.account_number].add(
                    "dauerhafte Personenkonto-Zuordnung"
                )
            configuration = (
                self._session.query(KontenrahmenKonfiguration)
                .filter(
                    KontenrahmenKonfiguration.mandant_id
                    == company_model.id
                )
                .one_or_none()
            )
            if configuration is not None:
                for field_name, label in self._CONFIGURATION_REFERENCE_LABELS.items():
                    number = getattr(configuration, field_name)
                    if number in dependencies:
                        dependencies[number].add(label)

            for role in (
                self._session.query(Kontenrolle)
                .filter(
                    Kontenrolle.mandant_id == company_model.id,
                    Kontenrolle.account_number.in_(numbers),
                )
                .all()
            ):
                dependencies[role.account_number].add(
                    f"Kontenrolle {role.role}"
                )

            booking_rows = (
                self._session.query(
                    Buchungszeile.account_number,
                    Wirtschaftsjahr.start_date,
                    Wirtschaftsjahr.end_date,
                )
                .join(Buchung, Buchung.id == Buchungszeile.buchung_id)
                .join(
                    Wirtschaftsjahr,
                    Wirtschaftsjahr.id == Buchung.wirtschaftsjahr_id,
                )
                .filter(
                    Wirtschaftsjahr.mandant_id == company_model.id,
                    Buchungszeile.account_number.in_(numbers),
                )
                .all()
            )
            for number, start_date, end_date in booking_rows:
                dependencies[number].add(
                    "Buchungen im Geschäftsjahr "
                    f"{start_date.year}/{end_date.year}"
                )

            fixed_assets = (
                self._session.query(Anlagegut)
                .filter(
                    Anlagegut.mandant_id == company_model.id,
                    (
                        Anlagegut.asset_account_number.in_(numbers)
                        | Anlagegut.depreciation_expense_account_number.in_(
                            numbers
                        )
                    ),
                )
                .all()
            )
            for asset in fixed_assets:
                for field_name, label in (
                    ("asset_account_number", "Anlagenkonto"),
                    (
                        "depreciation_expense_account_number",
                        "Abschreibungskonto eines Anlageguts",
                    ),
                ):
                    number = getattr(asset, field_name)
                    if number in dependencies:
                        dependencies[number].add(
                            f"{label} {asset.asset_code}"
                        )

            blocked = {
                number: tuple(sorted(reasons))
                for number, reasons in dependencies.items()
                if reasons
            }
            if blocked:
                self._session.rollback()
                return blocked

            (
                self._session.query(KontenTaxonomieZuordnung)
                .filter(
                    KontenTaxonomieZuordnung.mandant_id
                    == company_model.id,
                    KontenTaxonomieZuordnung.account_number.in_(numbers),
                )
                .delete(synchronize_session=False)
            )
            (
                self._session.query(Konto)
                .filter(
                    Konto.mandant_id == company_model.id,
                    Konto.account_number.in_(numbers),
                )
                .delete(synchronize_session=False)
            )
            self._session.commit()
            return {}
        except Exception:
            self._session.rollback()
            raise

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

        person_roles = {
            row.account_number: PersonAccountRole(row.role)
            for row in self._session.query(PersonenkontoZuordnung)
            .filter(PersonenkontoZuordnung.mandant_id == company_model.id)
            .all()
        }

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
                    person_account_role=person_roles.get(model.account_number),
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
                person_account_roles=tuple(sorted(person_roles.items())),
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
        vat_accounts: VatAccounts | None = None,
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

        if vat_accounts is not None:
            missing_vat_accounts = vat_accounts.account_numbers - account_numbers
            if missing_vat_accounts:
                raise ValueError(
                    "Umsatzsteuerkonten sind im Kontenrahmen nicht vorhanden: "
                    + ", ".join(sorted(missing_vat_accounts))
                )

        account_types = dict(
            self._session.query(
                Konto.account_number,
                Konto.account_type,
            )
            .filter(Konto.mandant_id == company_model.id)
            .all()
        )
        expected_control_types = (
            (control_accounts.opening_balance_account, AccountType.EQUITY, "Eröffnungsbilanzkonto"),
            (control_accounts.income_summary_account, AccountType.EQUITY, "GuV-Sammelkonto"),
            (control_accounts.profit_account, AccountType.EQUITY, "Jahresüberschusskonto"),
            (control_accounts.loss_account, AccountType.EQUITY, "Jahresfehlbetragskonto"),
            (control_accounts.profit_loss_carryforward_account, AccountType.EQUITY, "Gewinn-/Verlustvortragskonto"),
            (control_accounts.statutory_reserve_account, AccountType.EQUITY, "gesetzliches Rücklagenkonto"),
            (control_accounts.other_revenue_reserves_account, AccountType.EQUITY, "Gewinnrücklagenkonto"),
            (control_accounts.distribution_liability_account, AccountType.LIABILITY, "Ausschüttungsverbindlichkeit"),
            (control_accounts.depreciation_expense_account, AccountType.EXPENSE, "Abschreibungskonto"),
            (control_accounts.fixed_asset_disposal_gain_account, AccountType.REVENUE, "Anlagenabgangsertragskonto"),
            (control_accounts.fixed_asset_disposal_loss_account, AccountType.EXPENSE, "Anlagenabgangsverlustkonto"),
        )
        for account_number, expected_type, label in expected_control_types:
            if account_types.get(account_number) != expected_type.name:
                raise ValueError(
                    f"{label} {account_number} muss den Kontotyp "
                    f"{expected_type.name} haben."
                )
        if vat_accounts is not None:
            wrong_vat_types = (
                [
                    number
                    for number in (
                        vat_accounts.input_tax_7,
                        vat_accounts.input_tax_19,
                    )
                    if account_types.get(number) != AccountType.ASSET.name
                ],
                [
                    number
                    for number in (
                        vat_accounts.output_tax_7,
                        vat_accounts.output_tax_19,
                    )
                    if account_types.get(number) != AccountType.LIABILITY.name
                ],
            )
            if wrong_vat_types[0]:
                raise ValueError(
                    "Vorsteuerkonten müssen Aktivkonten sein: "
                    + ", ".join(sorted(set(wrong_vat_types[0])))
                )
            if wrong_vat_types[1]:
                raise ValueError(
                    "Umsatzsteuerkonten müssen Passivkonten sein: "
                    + ", ".join(sorted(set(wrong_vat_types[1])))
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
            if vat_accounts is None:
                raise ValueError(
                    "Zum erstmaligen Speichern technischer Konten müssen "
                    "auch Umsatz- und Vorsteuerkonten angegeben werden."
                )
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
                input_tax_7=vat_accounts.input_tax_7,
                input_tax_19=vat_accounts.input_tax_19,
                output_tax_7=vat_accounts.output_tax_7,
                output_tax_19=vat_accounts.output_tax_19,
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

        account_types = dict(
            self._session.query(
                Konto.account_number,
                Konto.account_type,
            )
            .filter(Konto.mandant_id == company_model.id)
            .all()
        )
        unsuitable_input_accounts = sorted(
            number
            for number in (vat_accounts.input_tax_7, vat_accounts.input_tax_19)
            if account_types.get(number) != AccountType.ASSET.name
        )
        if unsuitable_input_accounts:
            raise ValueError(
                "Vorsteuerkonten müssen Aktivkonten sein: "
                + ", ".join(unsuitable_input_accounts)
            )
        unsuitable_output_accounts = sorted(
            number
            for number in (vat_accounts.output_tax_7, vat_accounts.output_tax_19)
            if account_types.get(number) != AccountType.LIABILITY.name
        )
        if unsuitable_output_accounts:
            raise ValueError(
                "Umsatzsteuerkonten müssen Passivkonten sein: "
                + ", ".join(unsuitable_output_accounts)
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
        commit: bool = True,
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

            if commit:
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

        role_account_types = dict(
            self._session.query(
                Konto.account_number,
                Konto.account_type,
            )
            .filter(Konto.mandant_id == company_model.id)
            .all()
        )
        for account_set, expected_type, message in (
            (
                account_roles.cash_accounts,
                AccountType.ASSET,
                "Kassenkonten müssen Aktivkonten sein",
            ),
            (
                account_roles.bank_accounts,
                AccountType.ASSET,
                "Bankkonten müssen Aktivkonten sein",
            ),
            (
                account_roles.general_rate_sales_accounts,
                AccountType.REVENUE,
                "Umsatzerlöskonten müssen Ertragskonten sein",
            ),
            (
                account_roles.vat_advance_payments,
                AccountType.ASSET,
                "Umsatzsteuer-Vorauszahlungskonten müssen Aktivkonten sein",
            ),
            (
                account_roles.vat_current_year,
                AccountType.LIABILITY,
                "Umsatzsteuerkonten des laufenden Jahres müssen Passivkonten sein",
            ),
            (
                account_roles.vat_prior_year_receivables,
                AccountType.ASSET,
                "Umsatzsteuerforderungen aus Vorjahren müssen Aktivkonten sein",
            ),
            (
                account_roles.vat_prior_year_payables,
                AccountType.LIABILITY,
                "Umsatzsteuerverbindlichkeiten aus Vorjahren müssen Passivkonten sein",
            ),
        ):
            unsuitable = sorted(
                number
                for number in account_set
                if role_account_types.get(number) != expected_type.name
            )
            if unsuitable:
                raise ValueError(message + ": " + ", ".join(unsuitable))

        account_mappings = {
            number: (debit_code, credit_code)
            for number, debit_code, credit_code in self._session.query(
                Konto.account_number,
                Konto.debit_position_code,
                Konto.credit_position_code,
            ).filter(Konto.mandant_id == company_model.id).all()
        }
        required_vat_mappings = (
            (
                account_roles.vat_advance_payments,
                "debit",
                "HGB.266.AKTIVA.B.II.4",
                "Umsatzsteuer-Vorauszahlungen",
            ),
            (
                account_roles.vat_current_year,
                "debit",
                "HGB.266.AKTIVA.B.II.4",
                "Umsatzsteuer laufendes Jahr (Soll)",
            ),
            (
                account_roles.vat_current_year,
                "credit",
                "HGB.266.PASSIVA.C.8",
                "Umsatzsteuer laufendes Jahr (Haben)",
            ),
            (
                account_roles.vat_prior_year_receivables,
                "debit",
                "HGB.266.AKTIVA.B.II.4",
                "Umsatzsteuerforderungen Vorjahr",
            ),
            (
                account_roles.vat_prior_year_payables,
                "credit",
                "HGB.266.PASSIVA.C.8",
                "Umsatzsteuerverbindlichkeiten Vorjahr",
            ),
        )
        for account_set, side, expected_code, label in required_vat_mappings:
            for number in account_set:
                debit_code, credit_code = account_mappings.get(
                    number, (None, None)
                )
                actual_code = debit_code if side == "debit" else credit_code
                if actual_code != expected_code:
                    side_label = "Soll" if side == "debit" else "Haben"
                    raise ValueError(
                        f"{label} {number} benötigt die HGB-{side_label}-"
                        f"Zuordnung {expected_code}."
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
            (
                "VAT_ADVANCE_PAYMENTS",
                account_roles.vat_advance_payments,
            ),
            (
                "VAT_CURRENT_YEAR",
                account_roles.vat_current_year,
            ),
            (
                "VAT_PRIOR_YEAR_RECEIVABLES",
                account_roles.vat_prior_year_receivables,
            ),
            (
                "VAT_PRIOR_YEAR_PAYABLES",
                account_roles.vat_prior_year_payables,
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
                vat_accounts=vat_accounts,
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

        vat_advance_payments = frozenset(
            model.account_number
            for model in models
            if model.role == "VAT_ADVANCE_PAYMENTS"
        )

        vat_current_year = frozenset(
            model.account_number
            for model in models
            if model.role == "VAT_CURRENT_YEAR"
        )

        vat_prior_year_receivables = frozenset(
            model.account_number
            for model in models
            if model.role == "VAT_PRIOR_YEAR_RECEIVABLES"
        )

        vat_prior_year_payables = frozenset(
            model.account_number
            for model in models
            if model.role == "VAT_PRIOR_YEAR_PAYABLES"
        )

        known_roles = {
            "CASH",
            "BANK",
            "GENERAL_RATE_SALES",
            "VAT_ADVANCE_PAYMENTS",
            "VAT_CURRENT_YEAR",
            "VAT_PRIOR_YEAR_RECEIVABLES",
            "VAT_PRIOR_YEAR_PAYABLES",
        }
        legacy_open_item_roles = {
            "CUSTOMER_RECEIVABLES",
            "SUPPLIER_PAYABLES",
            "CUSTOMER_CREDIT_BALANCES",
            "SUPPLIER_CREDIT_BALANCES",
        }

        unknown_roles = {
            model.role
            for model in models
            if model.role not in known_roles
            and model.role not in legacy_open_item_roles
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
            vat_advance_payments=vat_advance_payments,
            vat_current_year=vat_current_year,
            vat_prior_year_receivables=vat_prior_year_receivables,
            vat_prior_year_payables=vat_prior_year_payables,
        )

    def validate_payment_cash_bank_account(
        self,
        *,
        company_id: UUID,
        account_number: str,
    ) -> None:
        """Prüft ein aktives, mandanteneigenes Bank- oder Kassenkonto."""
        roles = self.load_account_roles(company_id)
        configured_accounts = (
            roles.cash_accounts | roles.bank_accounts
            if roles is not None
            else frozenset()
        )
        if account_number not in configured_accounts:
            raise ValueError(
                "Das Zahlungskonto ist keinem Bank- oder Kassenkonto "
                "des Mandanten zugeordnet."
            )
        self._validate_active_account_type(
            company_id=company_id,
            account_number=account_number,
            account_type=AccountType.ASSET,
            label="Bank-/Kassenkonto",
        )

    def _validate_active_account_type(
        self,
        *,
        company_id: UUID,
        account_number: str,
        account_type: AccountType,
        label: str,
    ) -> None:
        company_model = self._find_company(company_id)
        if company_model is None:
            raise ValueError("Das Unternehmen ist nicht vorhanden.")
        account = (
            self._session.query(Konto)
            .filter(
                Konto.mandant_id == company_model.id,
                Konto.account_number == account_number,
            )
            .one_or_none()
        )
        if account is None or not account.is_active:
            raise ValueError(f"Das {label} ist nicht vorhanden oder nicht aktiv.")
        if account.account_type != account_type.name:
            account_kind = "Passivkonto" if account_type is AccountType.LIABILITY else "Aktivkonto"
            raise ValueError(f"Das {label} muss ein {account_kind} sein.")

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

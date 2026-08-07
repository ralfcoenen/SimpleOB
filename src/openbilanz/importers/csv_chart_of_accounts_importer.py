"""CSV-Importer für Kontenrahmen."""

import csv
from pathlib import Path

from openbilanz.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)
from openbilanz.domain.account_mapping_rule import AccountMappingRule
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.importers.chart_of_accounts_importer import (
    ChartOfAccountsImporter,
)
from openbilanz.importers.errors import (
    ChartOfAccountsImportError,
)


class CsvChartOfAccountsImporter(ChartOfAccountsImporter):
    """Importiert einen Kontenrahmen aus einer CSV-Datei."""


    def __init__(
        self,
        *,
        position_provider: FinancialStatementPositionProvider | None = None,
    ) -> None:
        self._position_provider = position_provider
        
    def load(
        self,
        path: Path,
    ) -> ChartOfAccountsTemplate:
        """Lädt Konten aus einer semikolongetrennten CSV-Datei."""

        with path.open(
            mode="r",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(
                csv_file,
                delimiter=";",
            )

            rows = tuple(reader)

        accounts = tuple(
            self._create_account(row)
            for row in rows
        )

        mapping_rules = tuple(
            self._create_mapping_rule(row)
            for row in rows
            if self._has_mapping(row)
        )

        return self._create_chart_of_accounts(
            path=path,
            accounts=accounts,
            mapping_rules=mapping_rules,
        )
 
    @staticmethod
    def _create_chart_of_accounts(
        *,
        path: Path,
        accounts: tuple[TemplateAccount, ...],
        mapping_rules: tuple[AccountMappingRule, ...],
    ) -> ChartOfAccountsTemplate:
        """Erzeugt den importierten Kontenrahmen."""

        return ChartOfAccountsTemplate(
            name=path.stem,
            accounts=accounts,
            account_mapping_rules=mapping_rules,
        )
 
    @staticmethod
    def _required_value(
        row: dict[str, str],
        column: str,
    ) -> str:
        """Liefert den Wert einer Pflichtspalte."""

        try:
            return row[column]
        except KeyError as exc:
            raise ChartOfAccountsImportError(
                f"Fehlende Spalte: {column!r}"
            ) from exc
    
    def _create_account(
        self,
        row: dict[str, str],
    ) -> TemplateAccount:
        """Erzeugt ein Konto aus einer CSV-Zeile."""

        account_number = self._required_value(
            row,
            "account_number",
        )
        name = self._required_value(
            row,
            "name",
        )
        account_type_name = self._required_value(
            row,
            "account_type",
        )

        try:
            account_type = AccountType[account_type_name]
        except KeyError as exc:
            raise ChartOfAccountsImportError(
                f"Unbekannter Kontotyp: {account_type_name!r}"
            ) from exc

        return TemplateAccount(
            account_number=account_number,
            name=name,
            account_type=account_type,
        )
    
    @staticmethod
    def _has_mapping(
        row: dict[str, str],
    ) -> bool:
        """Prüft, ob eine CSV-Zeile eine Abschlusszuordnung enthält."""

        return bool(
            row.get("debit_position_code")
            or row.get("credit_position_code")
        )


    def _create_mapping_rule(
        self,
        row: dict[str, str],
    ) -> AccountMappingRule:
        """Erzeugt eine Kontenzuordnungsregel aus einer CSV-Zeile."""

        if self._position_provider is None:
            raise ChartOfAccountsImportError(
                "Für den Import von Kontenzuordnungen "
                "wird ein PositionProvider benötigt."
            )

        account_number = self._required_value(
            row,
            "account_number",
        )

        statement_type = self._required_value(
            row,
            "statement_type",
        )

        
        debit_position_code = row.get("debit_position_code", "")
        credit_position_code = row.get("credit_position_code", "")

        self._validate_statement_type(
            statement_type=statement_type,
            debit_position_code=debit_position_code,
            credit_position_code=credit_position_code,
        )


        debit_position = (
            self._position_provider.get(debit_position_code)
            if debit_position_code
            else None
        )
        credit_position = (
            self._position_provider.get(credit_position_code)
            if credit_position_code
            else None
        )

        return AccountMappingRule(
            account_number=account_number,
            debit_position=debit_position,
            credit_position=credit_position,
        )

    @staticmethod
    def _validate_statement_type(
        *,
        statement_type: str,
        debit_position_code: str,
        credit_position_code: str,
    ) -> None:
        """Prüft, ob Abschlussart und Positionscodes zusammenpassen."""

        position_codes = (
            debit_position_code,
            credit_position_code,
        )

        if statement_type == "BALANCE_SHEET":
            expected_prefix = "HGB.266."
        elif statement_type == "INCOME_STATEMENT":
            expected_prefix = "HGB.275."
        else:
            raise ChartOfAccountsImportError(
                f"Unbekannter statement_type: {statement_type!r}"
            )

        for position_code in position_codes:
            if (
                position_code
                and not position_code.startswith(expected_prefix)
            ):
                raise ChartOfAccountsImportError(
                    "statement_type passt nicht zum "
                    f"Abschlusspositionscode {position_code!r}."
                )
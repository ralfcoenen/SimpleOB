"""CSV-Importer für Kontenrahmen."""

import csv
from pathlib import Path

from simpleob.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.template_account import TemplateAccount
from simpleob.importers.chart_of_accounts_importer import (
    ChartOfAccountsImporter,
)
from simpleob.importers.errors import (
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

            required_columns = {
                "account_number",
                "name",
                "account_type",
            }
            if reader.fieldnames is None or not required_columns.issubset(
                reader.fieldnames
            ):
                raise ChartOfAccountsImportError(
                    "Fehlende Spalte in Konten-CSV. Benötigt werden "
                    "die Spalten "
                    "account_number, name und account_type."
                )

            mapping_columns = {
                "statement_type",
                "debit_position_code",
                "credit_position_code",
            }
            present_mapping_columns = mapping_columns.intersection(
                reader.fieldnames
            )
            if present_mapping_columns and present_mapping_columns != mapping_columns:
                raise ChartOfAccountsImportError(
                    "HGB-Zuordnungen benötigen die Spalten "
                    "statement_type, debit_position_code und "
                    "credit_position_code."
                )

            try:
                rows = tuple(reader)
            except csv.Error as exc:
                raise ChartOfAccountsImportError(
                    f"Die Konten-CSV ist fehlerhaft: {exc}"
                ) from exc

        if not rows:
            raise ChartOfAccountsImportError(
                "Die Konten-CSV enthält keine Konten."
            )
        if any(None in row or any(value is None for value in row.values()) for row in rows):
            raise ChartOfAccountsImportError(
                "Mindestens eine Konten-CSV-Zeile hat eine ungültige Spaltenanzahl."
            )

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

    def save(
        self,
        chart: ChartOfAccountsTemplate,
        path: Path,
    ) -> None:
        """Speichert Konten und vorhandene HGB-Zuordnungen im Importformat."""

        if not isinstance(chart, ChartOfAccountsTemplate):
            raise TypeError("chart must be a ChartOfAccountsTemplate")
        if not isinstance(path, Path):
            raise TypeError("path must be a Path")

        rules_by_account = {
            rule.account_number: rule
            for rule in chart.account_mapping_rules
        }
        if len(rules_by_account) != len(chart.account_mapping_rules):
            raise ValueError(
                "Ein Konto darf nur eine HGB-Zuordnungsregel besitzen."
            )

        fieldnames = (
            "account_number",
            "name",
            "account_type",
            "statement_type",
            "debit_position_code",
            "credit_position_code",
        )
        with path.open("x", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
                delimiter=";",
                lineterminator="\n",
            )
            writer.writeheader()
            for account in chart.accounts:
                rule = rules_by_account.get(account.account_number)
                debit_code = (
                    rule.debit_position.code
                    if rule is not None and rule.debit_position is not None
                    else ""
                )
                credit_code = (
                    rule.credit_position.code
                    if rule is not None and rule.credit_position is not None
                    else ""
                )
                statement_type = ""
                if debit_code or credit_code:
                    position_code = debit_code or credit_code
                    if position_code.startswith("HGB.266."):
                        statement_type = "BALANCE_SHEET"
                    elif position_code.startswith("HGB.275."):
                        statement_type = "INCOME_STATEMENT"
                    else:
                        raise ValueError(
                            "Unbekannter HGB-Abschlusspositionscode: "
                            f"{position_code}"
                        )
                    self._validate_statement_type(
                        statement_type=statement_type,
                        debit_position_code=debit_code,
                        credit_position_code=credit_code,
                    )

                writer.writerow(
                    {
                        "account_number": account.account_number,
                        "name": account.name,
                        "account_type": account.account_type.name,
                        "statement_type": statement_type,
                        "debit_position_code": debit_code,
                        "credit_position_code": credit_code,
                    }
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

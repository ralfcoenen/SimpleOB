"""Lädt Kontenrahmen mit optionaler mandantenneutraler Konfiguration."""

import json
import re
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.accounting_control_accounts import AccountingControlAccounts
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.importers.csv_account_taxonomy_mapping_importer import (
    CsvAccountTaxonomyMappingImporter,
)
from simpleob.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)


@dataclass(frozen=True, slots=True)
class ChartOfAccountsTemplateBundle:
    """Kontenrahmen und optionale, wiederverwendbare Kontenzuordnungen."""

    chart: ChartOfAccountsTemplate
    control_accounts: AccountingControlAccounts | None = None
    vat_accounts: VatAccounts | None = None
    account_roles: AccountingAccountRoles | None = None
    taxonomy_version: str | None = None
    taxonomy_mappings: dict[str, str] | None = None


class ChartOfAccountsTemplateBundleImporter:
    """Lädt eine Konten-CSV und eine gleichnamige JSON-Beikonfiguration."""

    CONFIG_SUFFIX = ".config.json"

    def __init__(self, *, chart_importer: CsvChartOfAccountsImporter) -> None:
        self._chart_importer = chart_importer
        self._taxonomy_importer = CsvAccountTaxonomyMappingImporter()

    def load(self, csv_path: Path) -> ChartOfAccountsTemplateBundle:
        chart = self._chart_importer.load(csv_path)
        config_path = csv_path.with_name(
            f"{csv_path.stem}{self.CONFIG_SUFFIX}"
        )
        if not config_path.exists():
            return ChartOfAccountsTemplateBundle(chart=chart)

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Die Vorlagenkonfiguration {config_path.name} ist ungültig: {exc}"
            ) from exc
        if not isinstance(data, dict) or data.get("format_version") != 1:
            raise ValueError("Unbekanntes Format der Kontenrahmen-Konfiguration.")

        controls_data = self._object(data, "system_accounts")
        vat_data = self._object(data, "vat_accounts")
        roles_data = data.get("account_roles", {})
        if not isinstance(roles_data, dict):
            raise ValueError("account_roles muss ein Objekt sein.")

        controls = AccountingControlAccounts(**controls_data)
        vat = VatAccounts(**vat_data)
        roles = AccountingAccountRoles(
            cash_accounts=self._account_set(roles_data, "cash_accounts"),
            bank_accounts=self._account_set(roles_data, "bank_accounts"),
            general_rate_sales_accounts=self._account_set(
                roles_data, "general_rate_sales_accounts"
            ),
            customer_receivables=self._account_set(
                roles_data, "customer_receivables"
            ),
            supplier_payables=self._account_set(roles_data, "supplier_payables"),
            customer_credit_balances=self._account_set(
                roles_data, "customer_credit_balances"
            ),
            supplier_credit_balances=self._account_set(
                roles_data, "supplier_credit_balances"
            ),
        )

        taxonomy_version = data.get("taxonomy_version")
        mapping_file = data.get("taxonomy_mapping_file")
        mappings: dict[str, str] = {}
        if mapping_file is not None:
            if not isinstance(mapping_file, str) or not mapping_file.strip():
                raise ValueError("taxonomy_mapping_file muss ein relativer Pfad sein.")
            if not isinstance(taxonomy_version, str) or not taxonomy_version.strip():
                raise ValueError("Für Taxonomiezuordnungen ist eine Version erforderlich.")
            mapping_path = (config_path.parent / mapping_file).resolve()
            mappings = self._taxonomy_importer.load(mapping_path)
        elif taxonomy_version is not None:
            if not isinstance(taxonomy_version, str) or not taxonomy_version.strip():
                raise ValueError("taxonomy_version muss eine nichtleere Zeichenfolge sein.")

        bundle = ChartOfAccountsTemplateBundle(
            chart=chart,
            control_accounts=controls,
            vat_accounts=vat,
            account_roles=roles,
            taxonomy_version=taxonomy_version,
            taxonomy_mappings=mappings,
        )
        self.validate(bundle)
        return bundle

    def validate(
        self,
        bundle: ChartOfAccountsTemplateBundle,
        *,
        require_account_configuration: bool = True,
    ) -> None:
        """Prüft alle verfügbaren Konfigurationen vor der Übernahme."""

        if (
            bundle.taxonomy_version is not None
            and bundle.taxonomy_version != "6.9"
        ):
            raise ValueError(
                "Die Kontenrahmen-Vorlage verwendet die nicht unterstützte "
                f"E-Bilanz-Taxonomieversion {bundle.taxonomy_version}. "
                "Unterstützt wird derzeit ausschließlich Version 6.9."
            )

        if (
            require_account_configuration
            and (
                bundle.control_accounts is None
                or bundle.vat_accounts is None
            )
        ):
            raise ValueError(
                "Systemkonten sowie Umsatz- und Vorsteuerkonten müssen "
                "vor der Mandantenanlage vollständig zugeordnet sein."
            )
        self._validate_references(
            chart=bundle.chart,
            controls=bundle.control_accounts,
            vat=bundle.vat_accounts,
            roles=bundle.account_roles,
            taxonomy_mappings=bundle.taxonomy_mappings or {},
        )

    def save_configuration(
        self,
        bundle: ChartOfAccountsTemplateBundle,
        config_path: Path,
        *,
        taxonomy_mapping_file: str | None = None,
    ) -> None:
        """Speichert eine neue, mandantenneutrale Beikonfiguration ohne Überschreiben."""

        self.validate(bundle)
        roles = bundle.account_roles or AccountingAccountRoles(
            cash_accounts=frozenset(),
            bank_accounts=frozenset(),
            general_rate_sales_accounts=frozenset(),
        )
        data = {
            "format_version": 1,
            "system_accounts": {
                field: getattr(bundle.control_accounts, field)
                for field in AccountingControlAccounts.__dataclass_fields__
            },
            "vat_accounts": {
                field: getattr(bundle.vat_accounts, field)
                for field in VatAccounts.__dataclass_fields__
            },
            "account_roles": {
                field: sorted(getattr(roles, field))
                for field in AccountingAccountRoles.__dataclass_fields__
            },
        }
        if bundle.taxonomy_version is not None:
            data["taxonomy_version"] = bundle.taxonomy_version
        if taxonomy_mapping_file is not None:
            if (
                not isinstance(taxonomy_mapping_file, str)
                or not taxonomy_mapping_file.strip()
                or Path(taxonomy_mapping_file).name != taxonomy_mapping_file
            ):
                raise ValueError(
                    "taxonomy_mapping_file muss ein einfacher Dateiname sein."
                )
            if not bundle.taxonomy_mappings:
                raise ValueError(
                    "Ein Taxonomiedateiname wurde ohne Zuordnungen angegeben."
                )
            data["taxonomy_mapping_file"] = taxonomy_mapping_file
        with config_path.open("x", encoding="utf-8") as config_file:
            json.dump(data, config_file, ensure_ascii=False, indent=2)
            config_file.write("\n")

    def save_template(
        self,
        bundle: ChartOfAccountsTemplateBundle,
        templates_directory: Path,
        name: str,
    ) -> Path:
        """Speichert ein vollständiges Vorlagenpaket ohne bestehende Dateien zu ersetzen."""

        if not isinstance(templates_directory, Path):
            raise TypeError("templates_directory must be a Path")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Der Vorlagenname darf nicht leer sein.")

        stem = re.sub(r"[^\w.-]+", "_", name.strip(), flags=re.UNICODE)
        stem = stem.strip("._-")
        if not stem:
            raise ValueError("Der Vorlagenname enthält keinen gültigen Dateinamen.")

        bundle_to_save = (
            bundle
            if bundle.taxonomy_version is not None
            else replace(bundle, taxonomy_version="6.9")
        )
        self.validate(bundle_to_save)
        templates_directory.mkdir(parents=True, exist_ok=True)
        destination = templates_directory / stem
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(
                f"Eine eigene Vorlage mit dem Namen {stem!r} ist bereits vorhanden."
            )

        with tempfile.TemporaryDirectory(
            prefix=f".{stem}-",
            dir=templates_directory,
        ) as temporary_directory:
            staging = Path(temporary_directory)
            csv_path = staging / f"{stem}.csv"
            config_path = staging / f"{stem}{self.CONFIG_SUFFIX}"
            self._chart_importer.save(bundle_to_save.chart, csv_path)

            mapping_file = None
            if bundle_to_save.taxonomy_mappings:
                mapping_file = f"{stem}.taxonomy.csv"
                self._taxonomy_importer.save(
                    bundle_to_save.taxonomy_mappings,
                    staging / mapping_file,
                )

            self.save_configuration(
                bundle_to_save,
                config_path,
                taxonomy_mapping_file=mapping_file,
            )
            if destination.exists() or destination.is_symlink():
                raise FileExistsError(
                    f"Eine eigene Vorlage mit dem Namen {stem!r} ist bereits vorhanden."
                )
            staging.rename(destination)

        return destination / f"{stem}.csv"

    @staticmethod
    def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
        value = data.get(key)
        if not isinstance(value, dict):
            raise ValueError(f"{key} muss ein Objekt sein.")
        return value

    @staticmethod
    def _account_set(data: dict[str, Any], key: str) -> frozenset[str]:
        value = data.get(key, [])
        if not isinstance(value, list) or not all(
            isinstance(number, str) for number in value
        ):
            raise ValueError(f"{key} muss eine Liste aus Kontonummern sein.")
        return frozenset(value)

    @staticmethod
    def _validate_references(
        *,
        chart: ChartOfAccountsTemplate,
        controls: AccountingControlAccounts | None,
        vat: VatAccounts | None,
        roles: AccountingAccountRoles | None,
        taxonomy_mappings: dict[str, str],
    ) -> None:
        account_numbers = {account.account_number for account in chart.accounts}
        account_types = {
            account.account_number: account.account_type
            for account in chart.accounts
        }
        referenced = set(taxonomy_mappings)
        if controls is not None:
            referenced.update(controls.technical_account_numbers)
        if vat is not None:
            referenced.update(vat.account_numbers)
        if roles is not None:
            referenced.update(roles.account_numbers)
        missing = referenced - account_numbers
        if missing:
            raise ValueError(
                "Die Vorlagenkonfiguration verweist auf nicht vorhandene Konten: "
                + ", ".join(sorted(missing))
            )

        expected_role_types = (
            (
                roles.cash_accounts,
                AccountType.ASSET,
                "Kasse",
            ),
            (
                roles.bank_accounts,
                AccountType.ASSET,
                "Bank",
            ),
            (
                roles.general_rate_sales_accounts,
                AccountType.REVENUE,
                "Umsatzerlöse allgemeiner Steuersatz",
            ),
            (
                roles.customer_receivables,
                AccountType.ASSET,
                "Kundenforderungen",
            ),
            (
                roles.supplier_payables,
                AccountType.LIABILITY,
                "Lieferantenverbindlichkeiten",
            ),
            (
                roles.customer_credit_balances,
                AccountType.LIABILITY,
                "Kundenguthaben",
            ),
            (
                roles.supplier_credit_balances,
                AccountType.ASSET,
                "Lieferantenguthaben",
            ),
        ) if roles is not None else ()
        expected_control_types = (
            (
                (controls.opening_balance_account, AccountType.EQUITY, "Eröffnungsbilanz"),
                (controls.income_summary_account, AccountType.EQUITY, "GuV-Sammelkonto"),
                (controls.profit_account, AccountType.EQUITY, "Jahresüberschuss"),
                (controls.loss_account, AccountType.EQUITY, "Jahresfehlbetrag"),
                (controls.profit_loss_carryforward_account, AccountType.EQUITY, "Gewinn-/Verlustvortrag"),
                (controls.statutory_reserve_account, AccountType.EQUITY, "gesetzliche Rücklage"),
                (controls.other_revenue_reserves_account, AccountType.EQUITY, "andere Gewinnrücklagen"),
                (controls.distribution_liability_account, AccountType.LIABILITY, "Ausschüttungsverbindlichkeit"),
                (controls.depreciation_expense_account, AccountType.EXPENSE, "Abschreibung"),
                (controls.fixed_asset_disposal_gain_account, AccountType.REVENUE, "Anlagenabgangsertrag"),
                (controls.fixed_asset_disposal_loss_account, AccountType.EXPENSE, "Anlagenabgangsverlust"),
            )
            if controls is not None
            else ()
        )
        for number, expected_type, label in expected_control_types:
            if account_types.get(number) is not expected_type:
                raise ValueError(
                    f"Technisches Konto {label} {number} erwartet Kontotyp "
                    f"{expected_type.name}."
                )

        for account_set, expected_type, label in expected_role_types:
            unsuitable = sorted(
                number
                for number in account_set
                if account_types.get(number) is not expected_type
            )
            if unsuitable:
                raise ValueError(
                    f"Kontenrolle {label} erwartet Kontotyp "
                    f"{expected_type.name}: "
                    + ", ".join(unsuitable)
                )

        for account_set, expected_type, label in (
            (frozenset((vat.input_tax_7, vat.input_tax_19)), AccountType.ASSET, "Vorsteuer"),
            (frozenset((vat.output_tax_7, vat.output_tax_19)), AccountType.LIABILITY, "Umsatzsteuer"),
        ) if vat is not None else ():
            unsuitable = sorted(
                number
                for number in account_set
                if account_types.get(number) is not expected_type
            )
            if unsuitable:
                raise ValueError(
                    f"{label}konten erwarten Kontotyp "
                    f"{expected_type.name}: "
                    + ", ".join(unsuitable)
                )

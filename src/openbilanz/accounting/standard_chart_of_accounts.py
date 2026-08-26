"""Fest definierter OpenBilanz-Standardkontenrahmen."""

from openbilanz.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)
from openbilanz.domain.account_mapping_rule import (
    AccountMappingRule,
)
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.template_account import TemplateAccount


def create_standard_chart_of_accounts(
    *,
    position_provider: FinancialStatementPositionProvider,
) -> ChartOfAccountsTemplate:
    """Erzeugt den ausgelieferten OpenBilanz-Standardkontenrahmen."""

    accounts = (
        TemplateAccount(
            account_number="0200",
            name="Technische Anlagen und Maschinen",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="0400",
            name="Betriebs- und Geschäftsausstattung",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="0800",
            name="Gezeichnetes Kapital",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="1000",
            name="Kasse",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1400",
            name="Forderungen aus Lieferungen und Leistungen",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1571",
            name="Abziehbare Vorsteuer 7 %",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1576",
            name="Abziehbare Vorsteuer 19 %",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1600",
            name="Verbindlichkeiten aus Lieferungen und Leistungen",
            account_type=AccountType.LIABILITY,
        ),
        TemplateAccount(
            account_number="1700",
            name="Sonstige Verbindlichkeiten",
            account_type=AccountType.LIABILITY,
        ),
        TemplateAccount(
            account_number="1771",
            name="Umsatzsteuer 7 %",
            account_type=AccountType.LIABILITY,
        ),
        TemplateAccount(
            account_number="1776",
            name="Umsatzsteuer 19 %",
            account_type=AccountType.LIABILITY,
        ),
        TemplateAccount(
            account_number="2970",
            name="Gewinnvortrag / Verlustvortrag",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="3100",
            name="Fremdleistungen",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4210",
            name="Miete",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4360",
            name="Versicherungen",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4380",
            name="Beiträge",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4500",
            name="Fahrzeugkosten",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4600",
            name="Werbekosten",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4660",
            name="Reisekosten",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4800",
            name="Reparaturen und Instandhaltung",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4830",
            name="Abschreibungen auf Sachanlagen",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4840",
            name="Buchwert abgegangener Sachanlagen",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4900",
            name="Sonstige betriebliche Aufwendungen",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4920",
            name="Telefon und Internet",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4930",
            name="Bürobedarf",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4945",
            name="Fortbildungskosten",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4970",
            name="Nebenkosten des Geldverkehrs",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="4980",
            name="Sonstiger Betriebsbedarf",
            account_type=AccountType.EXPENSE,
        ),
        TemplateAccount(
            account_number="8990",
            name="GuV-Sammelkonto",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="8020",
            name="Jahresüberschuss",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="8021",
            name="Jahresfehlbetrag",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="8400",
            name="Umsatzerlöse 19 %",
            account_type=AccountType.REVENUE,
        ),
        TemplateAccount(
            account_number="8500",
            name="Sonstige betriebliche Erträge",
            account_type=AccountType.REVENUE,
        ),
        TemplateAccount(
            account_number="8510",
            name="Erlöse aus Anlagenabgängen",
            account_type=AccountType.REVENUE,
        ),
        TemplateAccount(
            account_number="9000",
            name="Eröffnungsbilanzkonto",
            account_type=AccountType.EQUITY,
        ),
    )

    mapping_specs = (
        ("0200", "HGB.266.AKTIVA.A.II.2", None),
        ("0400", "HGB.266.AKTIVA.A.II.3", None),
        ("0800", None, "HGB.266.PASSIVA.A.I"),
        ("1000", "HGB.266.AKTIVA.B.IV", None),
        ("1200", "HGB.266.AKTIVA.B.IV", None),
        ("1400", "HGB.266.AKTIVA.B.II.1", None),
        ("1571", "HGB.266.AKTIVA.B.II.4", None),
        ("1576", "HGB.266.AKTIVA.B.II.4", None),
        ("1600", None, "HGB.266.PASSIVA.C.4"),
        ("1700", None, "HGB.266.PASSIVA.C.8"),
        ("1771", None, "HGB.266.PASSIVA.C.8"),
        ("1776", None, "HGB.266.PASSIVA.C.8"),
        ("2970", None, "HGB.266.PASSIVA.A.IV"),
        ("3100", "HGB.275.GKV.5.b", None),
        ("4210", "HGB.275.GKV.8", None),
        ("4360", "HGB.275.GKV.8", None),
        ("4380", "HGB.275.GKV.8", None),
        ("4500", "HGB.275.GKV.8", None),
        ("4600", "HGB.275.GKV.8", None),
        ("4660", "HGB.275.GKV.8", None),
        ("4800", "HGB.275.GKV.8", None),
        ("4830", "HGB.275.GKV.7.a", None),
        ("4840", "HGB.275.GKV.8", None),
        ("4900", "HGB.275.GKV.8", None),
        ("4920", "HGB.275.GKV.8", None),
        ("4930", "HGB.275.GKV.8", None),
        ("4945", "HGB.275.GKV.8", None),
        ("4970", "HGB.275.GKV.8", None),
        ("4980", "HGB.275.GKV.8", None),
        ("8020", None, "HGB.266.PASSIVA.A.V"),
        ("8021", "HGB.266.PASSIVA.A.V", None),
        ("8400", None, "HGB.275.GKV.1"),
        ("8500", None, "HGB.275.GKV.4"),
        ("8510", None, "HGB.275.GKV.4"),
    )

    mapping_rules = tuple(
        AccountMappingRule(
            account_number=account_number,
            debit_position=(
                position_provider.get(
                    debit_position_code
                )
                if debit_position_code is not None
                else None
            ),
            credit_position=(
                position_provider.get(
                    credit_position_code
                )
                if credit_position_code is not None
                else None
            ),
        )
        for (
            account_number,
            debit_position_code,
            credit_position_code,
        ) in mapping_specs
    )

    return ChartOfAccountsTemplate(
        name="OpenBilanz Standard",
        accounts=accounts,
        account_mapping_rules=mapping_rules,
    )

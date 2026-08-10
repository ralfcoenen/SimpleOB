"""Tests für die Konsistenzprüfung des Jahresabschlusses."""

from datetime import date
from decimal import Decimal

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.accounting.trial_balance import TrialBalance
from openbilanz.domain.account_mapping_rule import AccountMappingRule
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.closing_consistency_result import ClosingConsistencyResult
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.services.closing_consistency_service import (
    ClosingConsistencyService,
)
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.posting_service import PostingService


class UnbalancedTrialBalance(TrialBalance):
    """Test-Summen- und Saldenliste mit erzwungener Inkonsistenz."""

    @property
    def is_turnover_balanced(self) -> bool:
        return False

    @property
    def is_balance_balanced(self) -> bool:
        return False
    
class TurnoverUnbalancedTrialBalance(TrialBalance):
    """Test-SuSa mit unausgeglichenen Umsätzen."""

    @property
    def is_turnover_balanced(self) -> bool:
        return False

    @property
    def is_balance_balanced(self) -> bool:
        return True


class BalanceUnbalancedTrialBalance(TrialBalance):
    """Test-SuSa mit unausgeglichenen Salden."""

    @property
    def is_turnover_balanced(self) -> bool:
        return True

    @property
    def is_balance_balanced(self) -> bool:
        return False
    

def test_balanced_trial_balance_is_consistent() -> None:
    """Eine ausgeglichene Summen- und Saldenliste ist konsistent."""

    ledger = Ledger()

    booking = Booking(
        booking_date=date(2026, 12, 31),
        description="Testbuchung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("1000.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("1000.00"),
            ),
        ),
    )

    PostingService().post_booking(
        booking=booking,
        ledger=ledger,
    )

    trial_balance = TrialBalance(
        ledger
    )

    service = ClosingConsistencyService()

    result = service.validate_trial_balance(
        trial_balance
    )

    assert result.is_consistent
    assert result.errors == ()
    
def test_unbalanced_trial_balance_is_inconsistent() -> None:
    """Eine unausgeglichene Summen- und Saldenliste ist inkonsistent."""

    trial_balance = UnbalancedTrialBalance(
        Ledger()
    )

    service = ClosingConsistencyService()

    result = service.validate_trial_balance(
        trial_balance
    )

    assert not result.is_consistent

    assert result.errors == (
        "Soll- und Habenumsätze stimmen nicht überein.",
        "Soll- und Habensalden stimmen nicht überein.",
    )
    
def test_turnover_difference_is_reported() -> None:
    """Eine Umsatzdifferenz wird einzeln gemeldet."""

    trial_balance = TurnoverUnbalancedTrialBalance(
        Ledger()
    )

    result = ClosingConsistencyService().validate_trial_balance(
        trial_balance
    )

    assert not result.is_consistent
    assert result.errors == (
        "Soll- und Habenumsätze stimmen nicht überein.",
    )


def test_balance_difference_is_reported() -> None:
    """Eine Saldendifferenz wird einzeln gemeldet."""

    trial_balance = BalanceUnbalancedTrialBalance(
        Ledger()
    )

    result = ClosingConsistencyService().validate_trial_balance(
        trial_balance
    )

    assert not result.is_consistent
    assert result.errors == (
        "Soll- und Habensalden stimmen nicht überein.",
    )

def test_balanced_balance_sheet_is_consistent() -> None:
    """Eine ausgeglichene Bilanz ist konsistent."""

    assets = FinancialStatementPosition(
        code="assets",
        name="Aktiva",
    )

    liabilities = FinancialStatementPosition(
        code="liabilities",
        name="Passiva",
    )

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("1000.00"),
            liabilities: Decimal("1000.00"),
        },
    )

    result = ClosingConsistencyService().validate_balance_sheet(
        balance_sheet
    )

    assert result.is_consistent
    assert result.errors == ()
   

def test_unbalanced_balance_sheet_is_inconsistent() -> None:
    """Eine unausgeglichene Bilanz ist inkonsistent."""

    assets = FinancialStatementPosition(
        code="assets",
        name="Aktiva",
    )

    liabilities = FinancialStatementPosition(
        code="liabilities",
        name="Passiva",
    )

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("1000.00"),
            liabilities: Decimal("900.00"),
        },
    )

    result = ClosingConsistencyService().validate_balance_sheet(
        balance_sheet
    )

    assert not result.is_consistent
    assert result.errors == (
        "Aktiva und Passiva stimmen nicht überein.",
    )
    
def test_matching_net_income_is_consistent() -> None:
    """GuV-Ergebnis und Jahresabschlussergebnis stimmen überein."""

    income_statement_root = FinancialStatementPosition(
        code="income_statement",
        name="Gewinn- und Verlustrechnung",
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={
            income_statement_root: Decimal("5000.00"),
        },
    )

    closing_result = ClosingResult(
        net_income=Decimal("5000.00"),
    )

    result = ClosingConsistencyService().validate_net_income(
        income_statement=income_statement,
        closing_result=closing_result,
    )

    assert result.is_consistent
    assert result.errors == ()
    
def test_mismatching_net_income_is_inconsistent() -> None:
    """Abweichende Jahresergebnisse werden erkannt."""

    income_statement_root = FinancialStatementPosition(
        code="income_statement",
        name="Gewinn- und Verlustrechnung",
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={
            income_statement_root: Decimal("5000.00"),
        },
    )

    closing_result = ClosingResult(
        net_income=Decimal("4500.00"),
    )

    result = ClosingConsistencyService().validate_net_income(
        income_statement=income_statement,
        closing_result=closing_result,
    )

    assert not result.is_consistent
    assert result.errors == (
        "GuV-Ergebnis und Jahresabschlussergebnis "
        "stimmen nicht überein.",
    )


def test_unmapped_account_is_inconsistent() -> None:
    """Ein Konto ohne Abschlusszuordnung macht den Abschluss inkonsistent."""

    balance = AccountBalance(
        account_number="1200",
        debit=Decimal("1000.00"),
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Testkontenrahmen",
        accounts=(),
        account_mapping_rules=(),
    )

    mapper = AccountMapper(
        chart_of_accounts
    )

    result = ClosingConsistencyService().validate_account_mappings(
        balances=(balance,),
        mapper=mapper,
    )

    assert not result.is_consistent
    assert result.errors == (
        "Konto 1200 ist keiner Abschlussposition zugeordnet.",
    )

def test_missing_debit_mapping_is_inconsistent() -> None:
    """Eine fehlende Soll-Zuordnung wird als Inkonsistenz erkannt."""

    credit_position = FinancialStatementPosition(
        code="liabilities",
        name="Passiva",
    )

    balance = AccountBalance(
        account_number="1200",
        debit=Decimal("1000.00"),
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Testkontenrahmen",
        accounts=(
            TemplateAccount(
                account_number="1200",
                name="Bank",
                account_type=AccountType.ASSET,
            ),
        ),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="1200",
                debit_position=None,
                credit_position=credit_position,
            ),
        ),
    )

    mapper = AccountMapper(
        chart_of_accounts
    )

    result = ClosingConsistencyService().validate_account_mappings(
        balances=(balance,),
        mapper=mapper,
    )

    assert not result.is_consistent
    assert result.errors == (
        "Konto 1200 ist keiner Abschlussposition zugeordnet.",
    )

def test_missing_credit_mapping_is_inconsistent() -> None:
    """Eine fehlende Haben-Zuordnung wird als Inkonsistenz erkannt."""

    debit_position = FinancialStatementPosition(
        code="assets",
        name="Aktiva",
    )

    balance = AccountBalance(
        account_number="1800",
        credit=Decimal("1000.00"),
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Testkontenrahmen",
        accounts=(
            TemplateAccount(
                account_number="1800",
                name="Eigenkapital",
                account_type=AccountType.EQUITY,
            ),
        ),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="1800",
                debit_position=debit_position,
                credit_position=None,
            ),
        ),
    )

    mapper = AccountMapper(
        chart_of_accounts
    )

    result = ClosingConsistencyService().validate_account_mappings(
        balances=(balance,),
        mapper=mapper,
    )

    assert not result.is_consistent
    assert result.errors == (
        "Konto 1800 ist keiner Abschlussposition zugeordnet.",
    )

def test_mapped_account_is_consistent() -> None:
    """Ein vollständig zugeordnetes Konto ist konsistent."""

    assets = FinancialStatementPosition(
        code="assets",
        name="Aktiva",
    )

    balance = AccountBalance(
        account_number="1200",
        debit=Decimal("1000.00"),
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Testkontenrahmen",
        accounts=(
            TemplateAccount(
                account_number="1200",
                name="Bank",
                account_type=AccountType.ASSET,
            ),
        ),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="1200",
                debit_position=assets,
                credit_position=None,
            ),
        ),
    )

    mapper = AccountMapper(
        chart_of_accounts
    )

    result = ClosingConsistencyService().validate_account_mappings(
        balances=(balance,),
        mapper=mapper,
    )

    assert result.is_consistent
    assert result.errors == ()
    

def test_zero_balance_account_does_not_require_mapping() -> None:
    """Ein Konto ohne Saldo benötigt keine Abschlusszuordnung."""

    balance = AccountBalance(
        account_number="1200",
        debit=Decimal("1000.00"),
        credit=Decimal("1000.00"),
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Testkontenrahmen",
        accounts=(),
        account_mapping_rules=(),
    )

    mapper = AccountMapper(
        chart_of_accounts
    )

    result = ClosingConsistencyService().validate_account_mappings(
        balances=(balance,),
        mapper=mapper,
    )

    assert result.is_consistent
    assert result.errors == ()
    
def test_complete_consistent_closing_is_consistent() -> None:
    """Ein vollständig konsistenter Jahresabschluss ist konsistent."""

    assets = FinancialStatementPosition(
        code="assets",
        name="Aktiva",
    )

    liabilities = FinancialStatementPosition(
        code="liabilities",
        name="Passiva",
    )

    income_statement_root = FinancialStatementPosition(
        code="income_statement",
        name="Gewinn- und Verlustrechnung",
    )

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("1000.00"),
            liabilities: Decimal("1000.00"),
        },
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={
            income_statement_root: Decimal("500.00"),
        },
    )

    closing_result = ClosingResult(
        net_income=Decimal("500.00"),
    )

    ledger = Ledger()

    booking = Booking(
        booking_date=date(2026, 12, 31),
        description="Testbuchung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("1000.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("1000.00"),
            ),
        ),
    )

    PostingService().post_booking(
        booking=booking,
        ledger=ledger,
    )

    trial_balance = TrialBalance(
        ledger
    )

    balances = (
        AccountBalance(
            account_number="1200",
            debit=Decimal("1000.00"),
        ),
        AccountBalance(
            account_number="1800",
            credit=Decimal("1000.00"),
        ),
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Testkontenrahmen",
        accounts=(
            TemplateAccount(
                account_number="1200",
                name="Bank",
                account_type=AccountType.ASSET,
            ),
            TemplateAccount(
                account_number="1800",
                name="Eigenkapital",
                account_type=AccountType.EQUITY,
            ),
        ),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="1200",
                debit_position=assets,
                credit_position=None,
            ),
            AccountMappingRule(
                account_number="1800",
                debit_position=None,
                credit_position=liabilities,
            ),
        ),
    )

    mapper = AccountMapper(
        chart_of_accounts
    )

    result = ClosingConsistencyService().validate(
        trial_balance=trial_balance,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        closing_result=closing_result,
        balances=balances,
        mapper=mapper,
    )

    assert result.is_consistent
    assert result.errors == ()
    
def test_complete_inconsistent_closing_reports_all_errors() -> None:
    """Mehrere Konsistenzfehler werden gemeinsam zurückgegeben."""

    assets = FinancialStatementPosition(
        code="assets",
        name="Aktiva",
    )

    liabilities = FinancialStatementPosition(
        code="liabilities",
        name="Passiva",
    )

    income_statement_root = FinancialStatementPosition(
        code="income_statement",
        name="Gewinn- und Verlustrechnung",
    )

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("1000.00"),
            liabilities: Decimal("900.00"),
        },
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={
            income_statement_root: Decimal("500.00"),
        },
    )

    closing_result = ClosingResult(
        net_income=Decimal("450.00"),
    )

    trial_balance = UnbalancedTrialBalance(
        Ledger()
    )

    balances = (
        AccountBalance(
            account_number="1200",
            debit=Decimal("1000.00"),
        ),
    )

    mapper = AccountMapper(
        ChartOfAccountsTemplate(
            name="Testkontenrahmen",
            accounts=(),
            account_mapping_rules=(),
        )
    )

    result = ClosingConsistencyService().validate(
        trial_balance=trial_balance,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        closing_result=closing_result,
        balances=balances,
        mapper=mapper,
    )

    assert not result.is_consistent

    assert result.errors == (
        "Soll- und Habenumsätze stimmen nicht überein.",
        "Soll- und Habensalden stimmen nicht überein.",
        "Aktiva und Passiva stimmen nicht überein.",
        "GuV-Ergebnis und Jahresabschlussergebnis "
        "stimmen nicht überein.",
        "Konto 1200 ist keiner Abschlussposition zugeordnet.",
    )
    
def test_consistency_result_without_errors_is_consistent() -> None:
    """Ein Ergebnis ohne Fehler ist konsistent."""

    result = ClosingConsistencyResult(
        errors=()
    )

    assert result.is_consistent
    assert result.errors == ()


def test_consistency_result_with_errors_is_inconsistent() -> None:
    """Ein Ergebnis mit Fehlern ist inkonsistent."""

    result = ClosingConsistencyResult(
        errors=(
            "Testfehler",
        )
    )

    assert not result.is_consistent
    assert result.errors == (
        "Testfehler",
    )
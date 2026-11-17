from unittest.mock import Mock

from PySide6.QtWidgets import QApplication

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.statement_category import StatementCategory
from simpleob.domain.account import Account
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.template_account import TemplateAccount
from simpleob.ui_qt.account_editor_dialog import AccountEditorDialog


def _app():
    return QApplication.instance() or QApplication([])


def _positions():
    first = FinancialStatementPosition(
        "HGB.266.AKTIVA.B.I.1",
        "Anlageposition eins",
        category=StatementCategory.ASSET,
    )
    second = FinancialStatementPosition(
        "HGB.266.AKTIVA.B.II.1",
        "Anlageposition zwei",
        category=StatementCategory.ASSET,
    )
    assets = FinancialStatementPosition(
        "HGB.266.AKTIVA",
        "Aktiva",
        children=(first, second),
    )
    liabilities = FinancialStatementPosition(
        "HGB.266.PASSIVA",
        "Passiva",
        children=(
            FinancialStatementPosition(
                "HGB.266.PASSIVA.A",
                "Eigenkapital",
                category=StatementCategory.LIABILITY,
            ),
        ),
    )
    income_statement = FinancialStatementPosition(
        "HGB.275",
        "GuV",
        children=(
            FinancialStatementPosition(
                "HGB.275.GKV.1",
                "Umsatzerlöse",
                category=StatementCategory.INCOME,
            ),
            FinancialStatementPosition(
                "HGB.275.GKV.8",
                "Sonstige Aufwendungen",
                category=StatementCategory.EXPENSE,
            ),
        ),
    )
    return assets, liabilities, income_statement, first, second


def _select_debit_position(dialog, position):
    dialog._debit_position_box.setCurrentText(
        dialog._position_display_name(position)
    )


def _new_dialog(**kwargs):
    assets, liabilities, income_statement, _first, _second = _positions()
    return AccountEditorDialog(
        None,
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
        taxonomy_mapping_enabled=True,
        **kwargs,
    )


def test_new_account_saves_hgb_and_taxonomy_in_one_editor():
    _app()
    assets, liabilities, income_statement, first, _second = _positions()
    choices_provider = Mock(
        return_value=((
            "concept.receivable",
            "Forderungen",
        ),)
    )
    dialog = AccountEditorDialog(
        None,
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
        taxonomy_mapping_enabled=True,
        taxonomy_choices_provider=choices_provider,
    )
    dialog._account_number_entry.setText("1210")
    dialog._name_entry.setText("Forderungen aus Lieferungen und Leistungen")
    _select_debit_position(dialog, first)
    dialog._taxonomy_position_box.setCurrentIndex(
        dialog._taxonomy_position_box.findData("concept.receivable")
    )

    dialog._save()

    assert dialog.result is not None
    assert dialog.result.account.number == "1210"
    assert dialog.result.mapping_rule == AccountMappingRule(
        account_number="1210",
        debit_position=first,
        credit_position=None,
    )
    assert dialog.result.taxonomy_concept_name == "concept.receivable"
    assert dialog.result.taxonomy_mapping_changed


def test_hgb_change_refreshes_choices_and_saves_new_valid_mapping():
    _app()
    assets, liabilities, income_statement, first, second = _positions()
    account = Account(
        TemplateAccount("1210", "Forderungen", AccountType.ASSET)
    )
    mapping_rule = AccountMappingRule("1210", first, None)
    provider = Mock(
        side_effect=lambda position: (
            (
                "concept.first" if position == first else "concept.second",
                "Position",
            ),
        )
    )
    dialog = AccountEditorDialog(
        None,
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
        account=account,
        mapping_rule=mapping_rule,
        taxonomy_mapping_enabled=True,
        taxonomy_concept_name="concept.first",
        taxonomy_choices_provider=provider,
        taxonomy_concept_validator=lambda position, concept: _validate_existing(
            position,
            concept,
            first,
        ),
    )

    _select_debit_position(dialog, second)
    assert any(call.args[0] == second for call in provider.call_args_list)
    dialog._taxonomy_position_box.setCurrentIndex(
        dialog._taxonomy_position_box.findData("concept.second")
    )
    dialog._save()

    assert dialog.result is not None
    assert dialog.result.mapping_rule.debit_position == second
    assert dialog.result.taxonomy_concept_name == "concept.second"


def test_missing_taxonomy_keeps_existing_mapping_on_account_edit():
    _app()
    assets, liabilities, income_statement, first, _second = _positions()
    account = Account(
        TemplateAccount("1210", "Forderungen", AccountType.ASSET)
    )
    dialog = AccountEditorDialog(
        None,
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
        account=account,
        mapping_rule=AccountMappingRule("1210", first, None),
        taxonomy_mapping_enabled=True,
        taxonomy_concept_name="concept.existing",
        taxonomy_choices_provider=_missing_taxonomy,
    )
    dialog._name_entry.setText("Geänderte Bezeichnung")

    dialog._save()

    assert dialog.result is not None
    assert dialog.result.account.name == "Geänderte Bezeichnung"
    assert dialog.result.taxonomy_concept_name == "concept.existing"
    assert not dialog.result.taxonomy_mapping_changed
    assert "Taxonomiemodell nicht installiert" in (
        dialog._taxonomy_status_label.text()
    )


def test_technical_and_booked_field_protections_are_scoped():
    _app()
    assets, liabilities, income_statement, first, _second = _positions()
    technical = AccountEditorDialog(
        None,
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
        account=Account(
            TemplateAccount("9000", "EBK", AccountType.EQUITY)
        ),
        mapping_rule=AccountMappingRule("9000", first, None),
        taxonomy_mapping_enabled=True,
        protect_technical_fields=True,
    )
    assert not technical._account_type_box.isEnabled()
    assert not technical._debit_position_box.isEnabled()
    assert not technical._is_active_box.isEnabled()
    assert technical._name_entry.isEnabled()
    assert technical._taxonomy_position_box.isEnabled()

    booked = _new_dialog(account_type_locked=True)
    assert not booked._account_type_box.isEnabled()
    assert booked._debit_position_box.isEnabled()
    assert booked._taxonomy_position_box.isEnabled()


def _validate_existing(position, concept, first):
    if (position, concept) != (first, "concept.first"):
        raise ValueError("unpassend")


def _missing_taxonomy(_position):
    raise FileNotFoundError("Taxonomie fehlt")

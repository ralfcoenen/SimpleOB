from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.domain.account import Account
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.accounting_control_accounts import AccountingControlAccounts
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.template_account import TemplateAccount
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.importers.chart_of_accounts_template_bundle_importer import (
    ChartOfAccountsTemplateBundle,
    ChartOfAccountsTemplateBundleImporter,
)
from simpleob.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)
from simpleob.ui_qt.account_configuration_dialog import (
    AccountConfigurationDialog,
)
from simpleob.ui_qt.account_editor_dialog import (
    AccountEditorDialog,
    AccountEditorResult,
)
from simpleob.ui_qt.chart_of_accounts_template_editor_dialog import (
    ChartOfAccountsTemplateEditorDialog,
)
from simpleob.ui_qt.new_company_dialog import NewCompanyDialog


def _app():
    return QApplication.instance() or QApplication([])


def _roots():
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()
    return assets, liabilities, income_statement


def _editor(bundle, *, templates_directory=None, taxonomy_choices_provider=None):
    assets, liabilities, income_statement = _roots()
    importer = ChartOfAccountsTemplateBundleImporter(
        chart_importer=CsvChartOfAccountsImporter(
            position_provider=HgbFinancialStatementPositionProvider(
                (assets, liabilities, income_statement)
            )
        )
    )
    return ChartOfAccountsTemplateEditorDialog(
        None,
        bundle=bundle,
        bundle_importer=importer,
        templates_directory=templates_directory,
        taxonomy_choices_provider=taxonomy_choices_provider,
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
    )


def _single_account_bundle(*, mapped=True, taxonomy=None):
    assets, _liabilities, _income_statement = _roots()
    account = TemplateAccount("7000", "Bankkonto", AccountType.ASSET)
    rules = (
        (
            AccountMappingRule(
                "7000",
                assets.children[0],
                None,
            ),
        )
        if mapped
        else ()
    )
    return ChartOfAccountsTemplateBundle(
        chart=ChartOfAccountsTemplate(
            "Test",
            (account,),
            account_mapping_rules=rules,
        ),
        taxonomy_mappings=taxonomy,
    )


def _referenced_bundle():
    _assets, liabilities, _income_statement = _roots()
    accounts = (
        TemplateAccount("7000", "Eigenkapital", AccountType.EQUITY),
        TemplateAccount("7001", "Verbindlichkeit", AccountType.LIABILITY),
        TemplateAccount("7002", "Aufwand", AccountType.EXPENSE),
        TemplateAccount("7003", "Ertrag", AccountType.REVENUE),
        TemplateAccount("7004", "Aktivkonto", AccountType.ASSET),
    )
    controls = {
        "opening_balance_account": "7000",
        "income_summary_account": "7000",
        "profit_account": "7000",
        "loss_account": "7000",
        "profit_loss_carryforward_account": "7000",
        "statutory_reserve_account": "7000",
        "other_revenue_reserves_account": "7000",
        "distribution_liability_account": "7001",
        "depreciation_expense_account": "7002",
        "fixed_asset_disposal_gain_account": "7003",
        "fixed_asset_disposal_loss_account": "7002",
    }
    return ChartOfAccountsTemplateBundle(
        chart=ChartOfAccountsTemplate(
            "Custom",
            accounts,
            account_mapping_rules=(
                AccountMappingRule("7000", liabilities.children[0], None),
            ),
        ),
        control_accounts=AccountingControlAccounts(**controls),
        vat_accounts=VatAccounts("7004", "7004", "7001", "7001"),
        account_roles=AccountingAccountRoles(
            cash_accounts=frozenset({"7004"}),
            bank_accounts=frozenset(),
            general_rate_sales_accounts=frozenset(),
        ),
        taxonomy_mappings={"7000": "sample.concept"},
    )


def _configuration_test_bundle(*, opening_balance_account="7000"):
    bundle = _referenced_bundle()
    accounts = (
        *bundle.chart.accounts,
        TemplateAccount("7005", "Weiteres Eigenkapital", AccountType.EQUITY),
        TemplateAccount("7006", "Weiteres Aktivkonto", AccountType.ASSET),
    )
    controls = replace(
        bundle.control_accounts,
        opening_balance_account=opening_balance_account,
    )
    return replace(
        bundle,
        chart=replace(bundle.chart, accounts=accounts),
        control_accounts=controls,
    )


def _patch_configuration_dialog(monkeypatch, on_open):
    captured = []

    class ConfigDialog(AccountConfigurationDialog):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured.append(self)

        def exec(self):
            return on_open(self)

    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.AccountConfigurationDialog",
        ConfigDialog,
    )
    return captured


def test_editor_copies_taxonomy_mapping_and_cancel_keeps_source_unchanged():
    _app()
    source = _single_account_bundle(
        taxonomy={"7000": "original.concept"}
    )
    dialog = _editor(source)

    dialog._bundle.taxonomy_mappings["7000"] = "changed.concept"
    dialog.reject()

    assert source.taxonomy_mappings == {"7000": "original.concept"}
    assert dialog.result is None


def test_editor_adds_account_to_working_copy(monkeypatch):
    _app()
    dialog = _editor(_single_account_bundle())
    assets, _liabilities, _income_statement = _roots()
    account = Account(
        TemplateAccount("7001", "Neues Konto", AccountType.ASSET)
    )
    result = AccountEditorResult(
        account,
        AccountMappingRule("7001", assets.children[0], None),
    )

    class AcceptedEditor:
        def __init__(self, *_args, **kwargs):
            assert kwargs["template_mode"] is True
            self.result = result

        def exec(self):
            return 1

    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.AccountEditorDialog",
        AcceptedEditor,
    )
    dialog._add_account()

    assert {item.account_number for item in dialog._bundle.chart.accounts} == {
        "7000",
        "7001",
    }
    assert dialog._bundle.chart.get("7001").name == "Neues Konto"


def test_renumber_requires_confirmation_and_moves_all_references(monkeypatch):
    _app()
    dialog = _editor(_referenced_bundle())
    assets, _liabilities, _income_statement = _roots()
    new_account = Account(
        TemplateAccount("8000", "Eigenkapital", AccountType.EQUITY)
    )
    result = AccountEditorResult(
        new_account,
        AccountMappingRule("8000", assets.children[0], None),
    )
    prompts = []
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.question",
        lambda *_args: (prompts.append(_args) or QMessageBox.StandardButton.Yes),
    )

    dialog._store_edited_account(old_number="7000", result=result)

    assert len(prompts) == 1
    assert "Systemkonto: Eröffnungsbilanzkonto" in prompts[0][2]
    assert "E-Bilanz-Taxonomiezuordnung: sample.concept" in prompts[0][2]
    assert dialog._bundle.control_accounts.opening_balance_account == "8000"
    assert dialog._bundle.taxonomy_mappings == {"8000": "sample.concept"}
    assert dialog._bundle.chart.account_mapping_rules[0].account_number == "8000"
    dialog.close()


def test_declined_reference_transfer_leaves_working_copy_unchanged(monkeypatch):
    _app()
    dialog = _editor(_referenced_bundle())
    before = dialog._bundle
    account = before.chart.get("7000")
    result = AccountEditorResult(
        Account(TemplateAccount("8000", account.name, account.account_type)),
        None,
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.question",
        lambda *_args: QMessageBox.StandardButton.No,
    )

    dialog._store_edited_account(old_number="7000", result=result)

    assert dialog._bundle == before
    dialog.close()


def test_referenced_account_cannot_be_removed(monkeypatch):
    _app()
    dialog = _editor(_referenced_bundle())
    row = next(
        index
        for index in range(dialog._table.rowCount())
        if dialog._table.item(index, 0).text() == "7000"
    )
    dialog._table.selectRow(row)
    warnings = []
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.warning",
        lambda *_args: warnings.append(_args),
    )

    dialog._remove_account()

    assert warnings
    assert dialog._bundle.chart.contains("7000")
    dialog.close()


def test_imported_accounts_without_hgb_mapping_can_be_applied(monkeypatch):
    _app()
    dialog = _editor(_single_account_bundle(mapped=False))
    warnings = []
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.warning",
        lambda *_args: warnings.append(_args),
    )

    dialog._apply()

    assert not warnings
    assert dialog.result is not None
    assert dialog.result.chart.account_mapping_rules == ()
    dialog.close()


def test_missing_hgb_mapping_does_not_hide_invalid_references(monkeypatch):
    _app()
    dialog = _editor(
        _single_account_bundle(
            mapped=False,
            taxonomy={"9999": "missing.concept"},
        )
    )
    errors = []
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.critical",
        lambda *_args: errors.append(_args),
    )

    dialog._apply()

    assert dialog.result is None
    assert errors
    assert "9999" in errors[0][2]
    dialog.close()


def test_template_editor_rejects_duplicate_renumber(monkeypatch):
    _app()
    dialog = _editor(_single_account_bundle())
    account = dialog._bundle.chart.accounts[0]
    result = AccountEditorResult(
        Account(TemplateAccount("7000", account.name, account.account_type)),
        None,
    )
    errors = []
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.critical",
        lambda *_args: errors.append(_args),
    )

    dialog._store_edited_account(old_number=None, result=result)

    assert errors
    assert len(dialog._bundle.chart.accounts) == 1
    dialog.close()


def test_unreferenced_account_can_be_removed_from_working_copy(monkeypatch):
    _app()
    bundle = _single_account_bundle()
    original = bundle.chart.accounts[0]
    original_rule = bundle.chart.account_mapping_rules[0]
    bundle = replace(
        bundle,
        chart=ChartOfAccountsTemplate(
            "Test",
            (
                original,
                TemplateAccount("7001", "Entbehrliches Konto", AccountType.ASSET),
            ),
            account_mapping_rules=(
                original_rule,
                AccountMappingRule("7001", original_rule.debit_position, None),
            ),
        ),
    )
    dialog = _editor(bundle)
    row = next(
        index
        for index in range(dialog._table.rowCount())
        if dialog._table.item(index, 0).text() == "7001"
    )
    dialog._table.selectRow(row)
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.question",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )

    dialog._remove_account()

    assert tuple(
        account.account_number for account in dialog._bundle.chart.accounts
    ) == ("7000",)
    assert tuple(
        rule.account_number
        for rule in dialog._bundle.chart.account_mapping_rules
    ) == ("7000",)
    assert len(bundle.chart.accounts) == 2
    dialog.close()


def test_template_mode_requires_hgb_by_default_and_allows_explicit_exception(
    monkeypatch,
):
    _app()
    assets, liabilities, income_statement = _roots()
    dialog = AccountEditorDialog(
        None,
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
        template_mode=True,
    )
    assert dialog._hgb_mapping_required_box.isChecked()
    dialog._account_number_entry.setText("7100")
    dialog._name_entry.setText("Ausnahmekonto")
    errors = []
    monkeypatch.setattr(
        "simpleob.ui_qt.account_editor_dialog.QMessageBox.critical",
        lambda *_args: errors.append(_args),
    )

    dialog._save()

    assert errors
    assert dialog.result is None
    dialog._hgb_mapping_required_box.setChecked(False)
    dialog._save()
    assert dialog.result is not None
    assert dialog.result.mapping_rule is None
    assert dialog.result.hgb_mapping_required is False
    dialog.close()


def test_template_mode_edit_uses_same_hgb_requirement_and_exception(
    monkeypatch,
):
    _app()
    assets, liabilities, income_statement = _roots()
    dialog = AccountEditorDialog(
        None,
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
        account=Account(
            TemplateAccount("7000", "Bestehendes Konto", AccountType.ASSET)
        ),
        template_mode=True,
    )
    assert dialog._hgb_mapping_required_box.isChecked()
    errors = []
    monkeypatch.setattr(
        "simpleob.ui_qt.account_editor_dialog.QMessageBox.critical",
        lambda *_args: errors.append(_args),
    )

    dialog._save()

    assert errors
    assert dialog.result is None
    dialog._hgb_mapping_required_box.setChecked(False)
    dialog._save()

    assert dialog.result is not None
    assert dialog.result.mapping_rule is None
    assert dialog.result.hgb_mapping_required is False
    dialog.close()


def test_template_account_editor_renumbers_account_and_its_hgb_rule():
    _app()
    assets, liabilities, income_statement = _roots()
    account = Account(
        TemplateAccount("7000", "Konto", AccountType.ASSET)
    )
    rule = AccountMappingRule("7000", assets.children[0], None)
    dialog = AccountEditorDialog(
        None,
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
        account=account,
        mapping_rule=rule,
        template_mode=True,
    )
    assert dialog._account_number_entry.isEnabled()
    dialog._account_number_entry.setText("7100")

    dialog._save()

    assert dialog.result is not None
    assert dialog.result.account.number == "7100"
    assert dialog.result.mapping_rule.account_number == "7100"
    dialog.close()


def test_account_editor_preserves_missing_taxonomy_mapping_on_unchanged_edit():
    _app()
    def provider(_position):
        return (("allowed.concept", "Zulässige Position"),)

    editor = _editor(_single_account_bundle(), taxonomy_choices_provider=provider)
    account = editor._bundle.chart.accounts[0]
    rule = editor._bundle.chart.account_mapping_rules[0]
    account_dialog = editor._edit_dialog(
        account=account,
        mapping_rule=rule,
    )

    assert account_dialog._taxonomy_position_box.currentData() is None
    assert account_dialog._taxonomy_position_box.currentText() == (
        "Keine explizite Zuordnung"
    )
    account_dialog._save()

    assert account_dialog.result is not None
    assert account_dialog.result.taxonomy_mapping_changed is False
    editor._store_edited_account(
        old_number="7000",
        result=account_dialog.result,
    )
    assert editor._bundle.taxonomy_mappings is None
    editor.close()


def test_account_editor_adds_and_changes_explicit_taxonomy_mapping():
    _app()
    def provider(_position):
        return (
            ("first.concept", "Erste Position"),
            ("second.concept", "Zweite Position"),
        )

    editor = _editor(
        _single_account_bundle(),
        taxonomy_choices_provider=provider,
    )
    account = editor._bundle.chart.accounts[0]
    rule = editor._bundle.chart.account_mapping_rules[0]
    account_dialog = editor._edit_dialog(account=account, mapping_rule=rule)
    assert account_dialog._taxonomy_position_box.currentData() is None
    account_dialog._taxonomy_position_box.setCurrentIndex(
        account_dialog._taxonomy_position_box.findData("first.concept")
    )
    account_dialog._save()
    editor._store_edited_account(old_number="7000", result=account_dialog.result)
    assert editor._bundle.taxonomy_mappings == {"7000": "first.concept"}

    account_dialog = editor._edit_dialog(
        account=editor._bundle.chart.accounts[0],
        mapping_rule=editor._bundle.chart.account_mapping_rules[0],
    )
    assert account_dialog._taxonomy_position_box.currentData() == "first.concept"
    account_dialog._taxonomy_position_box.setCurrentIndex(
        account_dialog._taxonomy_position_box.findData("second.concept")
    )
    account_dialog._save()
    editor._store_edited_account(old_number="7000", result=account_dialog.result)
    assert editor._bundle.taxonomy_mappings == {"7000": "second.concept"}
    editor.close()


def test_account_editor_explicitly_removes_taxonomy_mapping():
    _app()
    editor = _editor(
        _single_account_bundle(taxonomy={"7000": "known.concept"}),
        taxonomy_choices_provider=lambda _position: (
            ("known.concept", "Bekannte Position"),
        ),
    )
    account_dialog = editor._edit_dialog(
        account=editor._bundle.chart.accounts[0],
        mapping_rule=editor._bundle.chart.account_mapping_rules[0],
    )
    account_dialog._taxonomy_position_box.setCurrentIndex(0)
    account_dialog._save()
    editor._store_edited_account(old_number="7000", result=account_dialog.result)

    assert editor._bundle.taxonomy_mappings == {}
    editor.close()


def test_cancelled_account_edit_does_not_change_taxonomy_mapping():
    _app()
    editor = _editor(
        _single_account_bundle(taxonomy={"7000": "known.concept"}),
        taxonomy_choices_provider=lambda _position: (
            ("known.concept", "Bekannte Position"),
            ("other.concept", "Andere Position"),
        ),
    )
    before = dict(editor._bundle.taxonomy_mappings)
    account_dialog = editor._edit_dialog(
        account=editor._bundle.chart.accounts[0],
        mapping_rule=editor._bundle.chart.account_mapping_rules[0],
    )
    account_dialog._taxonomy_position_box.setCurrentIndex(
        account_dialog._taxonomy_position_box.findData("other.concept")
    )
    account_dialog.reject()

    assert account_dialog.result is None
    assert editor._bundle.taxonomy_mappings == before
    editor.close()


def test_renumbering_preserves_taxonomy_mapping_and_hgb_change_requires_correction(
    monkeypatch,
):
    _app()
    assets, _liabilities, _income_statement = _roots()
    original_position = assets.children[0]

    def choices(position):
        if position == original_position:
            return (("old.concept", "Alte Position"),)
        return (("new.concept", "Neue Position"),)

    bundle = _single_account_bundle(taxonomy={"7000": "old.concept"})
    editor = _editor(bundle, taxonomy_choices_provider=choices)
    account_dialog = editor._edit_dialog(
        account=editor._bundle.chart.accounts[0],
        mapping_rule=editor._bundle.chart.account_mapping_rules[0],
    )
    account_dialog._account_number_entry.setText("7100")
    account_dialog._save()
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.question",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )
    editor._store_edited_account(old_number="7000", result=account_dialog.result)
    assert editor._bundle.taxonomy_mappings == {"7100": "old.concept"}

    account_dialog = editor._edit_dialog(
        account=editor._bundle.chart.accounts[0],
        mapping_rule=editor._bundle.chart.account_mapping_rules[0],
    )
    another_position = next(
        position
        for label, position in account_dialog._debit_positions.items()
        if label != account_dialog._debit_position_box.currentText()
    )
    another_label = next(
        label
        for label, position in account_dialog._debit_positions.items()
        if position == another_position
    )
    account_dialog._debit_position_box.setCurrentText(another_label)
    assert "passt nicht" in account_dialog._taxonomy_status_label.text()
    errors = []
    monkeypatch.setattr(
        "simpleob.ui_qt.account_editor_dialog.QMessageBox.critical",
        lambda *_args: errors.append(_args),
    )
    account_dialog._save()
    assert errors
    assert account_dialog.result is None

    account_dialog._taxonomy_position_box.setCurrentIndex(
        account_dialog._taxonomy_position_box.findData("new.concept")
    )
    account_dialog._save()
    assert account_dialog.result is not None
    assert account_dialog.result.taxonomy_concept_name == "new.concept"
    editor.close()


def test_changed_taxonomy_mapping_survives_template_save_and_reload(tmp_path):
    _app()
    def provider(_position):
        return (
            ("sample.concept", "Beispielposition"),
            ("updated.concept", "Geänderte Position"),
        )

    editor = _editor(
        _referenced_bundle(),
        templates_directory=tmp_path / "templates",
        taxonomy_choices_provider=provider,
    )
    account_dialog = editor._edit_dialog(
        account=editor._bundle.chart.accounts[0],
        mapping_rule=editor._bundle.chart.account_mapping_rules[0],
    )
    account_dialog._taxonomy_position_box.setCurrentIndex(
        account_dialog._taxonomy_position_box.findData("updated.concept")
    )
    account_dialog._save()
    editor._store_edited_account(old_number="7000", result=account_dialog.result)

    saved_csv = editor._bundle_importer.save_template(
        editor._bundle,
        tmp_path / "templates",
        "Roundtrip",
    )
    reloaded = editor._bundle_importer.load(saved_csv)
    assert reloaded.taxonomy_mappings == {"7000": "updated.concept"}
    editor.close()


def test_configuration_button_opens_with_existing_values_and_accepts_changes(
    monkeypatch,
    tmp_path,
):
    _app()
    editor = _editor(
        _configuration_test_bundle(),
        templates_directory=tmp_path / "templates",
    )

    def accept_with_changes(config):
        assert config._opening_balance_box.currentData() == "7000"
        assert config._input_tax_7_box.currentData() == "7004"
        assert config._output_tax_19_box.currentData() == "7001"
        assert config._role_assignments["cash_accounts"] == {"7004"}

        config._select_account(config._opening_balance_box, "7005")
        config._select_account(config._input_tax_19_box, "7006")
        for index in range(config._role_account_list.count()):
            item = config._role_account_list.item(index)
            number = item.data(Qt.ItemDataRole.UserRole)
            if number == "7004":
                item.setCheckState(Qt.CheckState.Unchecked)
            elif number == "7006":
                item.setCheckState(Qt.CheckState.Checked)
        config._save()
        return QDialog.DialogCode.Accepted

    captured = _patch_configuration_dialog(monkeypatch, accept_with_changes)
    assert editor._configure_accounts_button.text() == (
        "Systemkonten und Kontenrollen …"
    )
    editor._configure_accounts_button.click()

    assert len(captured) == 1
    assert editor._bundle.control_accounts.opening_balance_account == "7005"
    assert editor._bundle.vat_accounts.input_tax_19 == "7006"
    assert editor._bundle.account_roles.cash_accounts == frozenset({"7006"})

    saved_csv = editor._bundle_importer.save_template(
        editor._bundle,
        tmp_path / "templates",
        "Changed configuration",
    )
    reloaded = editor._bundle_importer.load(saved_csv)
    assert reloaded.control_accounts == editor._bundle.control_accounts
    assert reloaded.vat_accounts == editor._bundle.vat_accounts
    assert reloaded.account_roles == editor._bundle.account_roles
    editor.close()


def test_configuration_dialog_cancel_keeps_working_bundle_unchanged(monkeypatch):
    _app()
    editor = _editor(_configuration_test_bundle())
    before = editor._bundle

    def cancel_after_change(config):
        config._select_account(config._opening_balance_box, "7005")
        return QDialog.DialogCode.Rejected

    _patch_configuration_dialog(monkeypatch, cancel_after_change)
    editor._configure_accounts_button.click()

    assert editor._bundle == before
    editor.close()


def test_account_can_be_removed_after_system_account_reference_is_replaced(
    monkeypatch,
):
    _app()
    editor = _editor(
        _configuration_test_bundle(opening_balance_account="7005")
    )

    def replace_system_reference(config):
        assert config._opening_balance_box.currentData() == "7005"
        config._select_account(config._opening_balance_box, "7000")
        config._save()
        return QDialog.DialogCode.Accepted

    _patch_configuration_dialog(monkeypatch, replace_system_reference)
    editor._configure_accounts_button.click()
    assert editor._bundle.control_accounts.opening_balance_account == "7000"
    assert editor._references_for("7005") == ()

    row = next(
        index
        for index in range(editor._table.rowCount())
        if editor._table.item(index, 0).text() == "7005"
    )
    editor._table.selectRow(row)
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.question",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )
    editor._remove_account()

    assert all(
        account.account_number != "7005"
        for account in editor._bundle.chart.accounts
    )
    editor.close()


def test_save_as_template_does_not_close_or_accept_editor(monkeypatch, tmp_path):
    _app()
    dialog = _editor(
        _referenced_bundle(),
        templates_directory=tmp_path / "templates",
    )
    saved_path = tmp_path / "templates" / "Meine_Vorlage" / "Meine_Vorlage.csv"
    bundle_before_save = dialog._bundle
    save_calls = []

    def save_template(*args):
        save_calls.append(args)
        return saved_path

    monkeypatch.setattr(
        dialog._bundle_importer,
        "save_template",
        save_template,
    )
    accepted_calls = []
    monkeypatch.setattr(
        dialog,
        "accept",
        lambda: accepted_calls.append(True),
    )
    messages = []
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QInputDialog.getText",
        lambda *_args: ("Meine Vorlage", True),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.information",
        lambda *_args: messages.append(_args),
    )

    dialog._save_as_template()

    assert len(save_calls) == 1
    assert save_calls[0][0] is bundle_before_save
    assert dialog.result is None
    assert accepted_calls == []
    assert messages
    dialog.close()


def test_save_as_template_can_complete_missing_configuration(monkeypatch, tmp_path):
    _app()
    source_bundle = _single_account_bundle(mapped=False)
    configured_bundle = replace(
        source_bundle,
        control_accounts=object(),
        vat_accounts=object(),
        account_roles=object(),
    )
    prepare_calls = []
    dialog = _editor(
        source_bundle,
        templates_directory=tmp_path / "templates",
    )
    initial_working_bundle = dialog._bundle
    dialog._prepare_bundle_for_save = (
        lambda bundle: (prepare_calls.append(bundle) or configured_bundle)
    )
    saved_bundles = []
    monkeypatch.setattr(
        dialog._bundle_importer,
        "save_template",
        lambda bundle, *_args: (
            saved_bundles.append(bundle)
            or tmp_path / "templates/Ready/Ready.csv"
        ),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QInputDialog.getText",
        lambda *_args: ("Ready", True),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.chart_of_accounts_template_editor_dialog.QMessageBox.information",
        lambda *_args: None,
    )

    dialog._save_as_template()

    assert prepare_calls == [initial_working_bundle]
    assert saved_bundles == [configured_bundle]
    assert dialog._bundle.control_accounts is configured_bundle.control_accounts
    assert dialog.result is None
    dialog.close()


def test_new_company_lists_own_templates_as_individual_charts(tmp_path):
    _app()
    template_directory = tmp_path / "templates"
    package_directory = template_directory / "Custom"
    package_directory.mkdir(parents=True)
    chart_path = package_directory / "Custom.csv"
    chart_path.write_text(
        "account_number;name;account_type\n7000;Eigenes Konto;ASSET\n",
        encoding="utf-8",
    )
    taxonomy_path = package_directory / "Custom.taxonomy.csv"
    taxonomy_path.write_text(
        "account_number;concept_name\n7000;sample.concept\n",
        encoding="utf-8",
    )

    dialog = NewCompanyDialog(
        None,
        repository=object(),
        template_directory=template_directory,
    )

    index = dialog._chart_box.findData(str(chart_path))
    assert index >= 0
    assert dialog._chart_box.itemText(index) == "Custom (eigene Vorlage)"
    assert dialog._chart_paths.count(chart_path) == 1
    assert taxonomy_path not in dialog._chart_paths
    assert dialog._chart_box.currentText() == "SimpleOB-Standard"
    assert dialog._is_standard_chart(
        Path(dialog._chart_box.currentData())
    )
    assert not dialog._is_standard_chart(chart_path)
    dialog.close()


def test_new_company_shows_invalid_chart_import_as_gui_error(tmp_path, monkeypatch):
    _app()
    invalid_chart = tmp_path / "invalid.csv"
    invalid_chart.write_text("wrong;columns\nvalue;value\n", encoding="utf-8")
    dialog = NewCompanyDialog(None, repository=object())
    dialog._company_name_entry.setText("Importtest")
    dialog._custom_chart_path = invalid_chart
    messages = []
    monkeypatch.setattr(
        "simpleob.ui_qt.new_company_dialog.QMessageBox.critical",
        lambda _parent, title, message: messages.append((title, message)),
    )

    dialog._create_company()

    assert len(messages) == 1
    assert messages[0][0] == "Kontenrahmen ungültig"
    assert "Fehlende Spalte" in messages[0][1]
    assert dialog.chart_bundle is None
    dialog.close()


def test_new_company_reuses_configuration_dialog_before_saving_incomplete_template(
    monkeypatch,
):
    _app()
    new_company = NewCompanyDialog(None, repository=object())
    source_bundle = _single_account_bundle(
        mapped=False,
        taxonomy={"7000": "custom.concept"},
    )
    controls = object()
    vat = object()
    roles = object()

    class AcceptedConfigurationDialog:
        def __init__(self, _parent, **kwargs):
            assert kwargs["for_new_company"] is True
            assert kwargs["control_accounts"] is None

        @staticmethod
        def exec():
            return QDialog.DialogCode.Accepted

        @staticmethod
        def _result():
            return controls, vat, roles

        @property
        def result(self):
            return self._result()

    monkeypatch.setattr(
        "simpleob.ui_qt.new_company_dialog.AccountConfigurationDialog",
        AcceptedConfigurationDialog,
    )

    configured = new_company._prepare_bundle_for_template_save(source_bundle)

    assert configured is not None
    assert configured.control_accounts is controls
    assert configured.vat_accounts is vat
    assert configured.account_roles is roles
    assert configured.taxonomy_mappings == source_bundle.taxonomy_mappings
    new_company.close()


def test_new_company_uses_edited_bundle_and_marks_standard_as_individual(
    monkeypatch,
):
    _app()
    dialog = NewCompanyDialog(None, repository=object())
    source_path = dialog._selected_chart_path()
    assert source_path is not None
    source_bytes = source_path.read_bytes()

    class AcceptedTemplateEditor:
        def __init__(self, _parent, *, bundle, **_kwargs):
            self.result = bundle

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "simpleob.ui_qt.new_company_dialog.ChartOfAccountsTemplateEditorDialog",
        AcceptedTemplateEditor,
    )
    dialog._edit_chart_template()
    assert dialog._bundle_was_edited
    assert dialog._edited_chart_source_path == source_path
    assert source_path.read_bytes() == source_bytes

    dialog._company_name_entry.setText("Editor Test UG")
    monkeypatch.setattr(
        "simpleob.ui_qt.new_company_dialog.QMessageBox.warning",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )

    class AcceptedConfigurationDialog:
        def __init__(self, _parent, **kwargs):
            self.result = (
                kwargs["control_accounts"],
                kwargs["vat_accounts"],
                kwargs["account_roles"],
            )

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "simpleob.ui_qt.new_company_dialog.AccountConfigurationDialog",
        AcceptedConfigurationDialog,
    )
    dialog._create_company()

    assert dialog.result is not None
    assert dialog.chart_bundle is not None
    assert dialog.uses_standard_chart is False
    assert source_path.read_bytes() == source_bytes
    dialog.close()

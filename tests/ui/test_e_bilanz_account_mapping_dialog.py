from PySide6.QtWidgets import QApplication

from simpleob.ui_qt.e_bilanz_account_mapping_dialog import (
    EBilanzAccountMappingDialog,
)


def _app():
    return QApplication.instance() or QApplication([])


def test_existing_unverified_concept_is_not_replaced_on_save():
    _app()
    dialog = EBilanzAccountMappingDialog(
        None,
        account_number="2900",
        account_name="Gezeichnetes Kapital",
        choices=(("valid.concept", "Gültige Auswahl"),),
        current_concept_name="existing.concept",
        current_concept_error="Taxonomiemodell nicht installiert.",
    )

    assert dialog._combobox.currentData() == (
        "unavailable",
        "existing.concept",
    )
    assert not dialog._save_button.isEnabled()
    dialog._save()

    assert not dialog.saved
    assert dialog.result == "existing.concept"


def test_explicit_selection_saves_valid_concept():
    _app()
    dialog = EBilanzAccountMappingDialog(
        None,
        account_number="2900",
        account_name="Gezeichnetes Kapital",
        choices=(("valid.concept", "Gültige Auswahl"),),
        current_concept_name="existing.concept",
        current_concept_error="Taxonomiemodell nicht installiert.",
    )

    dialog._combobox.setCurrentIndex(
        dialog._combobox.findData("valid.concept")
    )
    dialog._save()

    assert dialog.saved
    assert dialog.result == "valid.concept"

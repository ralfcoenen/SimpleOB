"""Regressionen für die anwendungsweite Auswahl beim Eingabefokus."""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from simpleob.ui_qt.input_focus import SelectAllOnFocusFilter


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_mouse_and_tab_focus_select_existing_text_and_allow_replacement() -> None:
    app = _app()
    event_filter = SelectAllOnFocusFilter(app)
    app.installEventFilter(event_filter)
    window = QWidget()
    layout = QVBoxLayout(window)
    first = QLineEdit("vorhanden")
    second = QLineEdit("ersetzen")
    layout.addWidget(first)
    layout.addWidget(second)
    window.show()
    app.processEvents()

    first.setFocus()
    app.processEvents()
    QTest.mouseClick(second, Qt.MouseButton.LeftButton)
    app.processEvents()
    assert second.selectedText() == "ersetzen"

    QTest.keyClicks(second, "neu")
    assert second.text() == "neu"

    first.setFocus()
    app.processEvents()
    QTest.keyClick(first, Qt.Key.Key_Tab)
    app.processEvents()
    assert second.selectedText() == "neu"

    window.close()
    app.removeEventFilter(event_filter)
    event_filter.deleteLater()


def test_selected_text_can_still_be_edited_at_a_specific_position() -> None:
    app = _app()
    event_filter = SelectAllOnFocusFilter(app)
    app.installEventFilter(event_filter)
    window = QWidget()
    layout = QVBoxLayout(window)
    before = QLineEdit()
    field = QLineEdit("Wert")
    layout.addWidget(before)
    layout.addWidget(field)
    window.show()
    before.setFocus()
    app.processEvents()

    QTest.keyClick(before, Qt.Key.Key_Tab)
    app.processEvents()
    assert field.selectedText() == "Wert"

    QTest.mouseClick(
        field,
        Qt.MouseButton.LeftButton,
        pos=QPoint(2, field.height() // 2),
    )
    QTest.keyClicks(field, "X")
    assert field.text().replace("X", "") == "Wert"

    window.close()
    app.removeEventFilter(event_filter)
    event_filter.deleteLater()


def test_spin_date_and_editable_combo_focus_select_their_editor_text() -> None:
    app = _app()
    event_filter = SelectAllOnFocusFilter(app)
    app.installEventFilter(event_filter)
    window = QWidget()
    layout = QVBoxLayout(window)
    date_edit = QDateEdit()
    date_edit.setDisplayFormat("dd.MM.yyyy")
    spin_box = QSpinBox()
    spin_box.setValue(42)
    double_spin_box = QDoubleSpinBox()
    double_spin_box.setValue(12.5)
    combo_box = QComboBox()
    combo_box.setEditable(True)
    combo_box.addItem("Auswahl")
    combo_box.setEditText("Eigener Wert")
    for widget in (date_edit, spin_box, double_spin_box, combo_box):
        layout.addWidget(widget)
    window.show()

    for widget, expected in (
        # QDateEdit ist absichtlich segmentiert und wählt den aktiven
        # Datumsabschnitt statt der gesamten Anzeige aus.
        (date_edit, date_edit.lineEdit().text()[:2]),
        (spin_box, "42"),
        (double_spin_box, double_spin_box.text()),
        (combo_box, "Eigener Wert"),
    ):
        widget.setFocus()
        app.processEvents()
        editor = (
            widget.lineEdit()
            if isinstance(widget, (QDateEdit, QSpinBox, QDoubleSpinBox, QComboBox))
            else widget
        )
        assert isinstance(editor, QLineEdit)
        assert editor.selectedText() == expected

    window.close()
    app.removeEventFilter(event_filter)
    event_filter.deleteLater()



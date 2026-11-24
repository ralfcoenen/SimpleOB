"""Anwendungsweite Textauswahl für bearbeitbare Qt-Eingabefelder."""

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QWidget,
)


class SelectAllOnFocusFilter(QObject):
    """Markiert vorhandene Eingaben nach einem tatsächlichen Fokuswechsel."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.FocusIn:
            return super().eventFilter(watched, event)

        target = self._selection_target(watched)
        if target is not None:
            # Verzögert bis nach dem auslösenden Mausklick, der sonst die
            # gerade gesetzte Auswahl mit seiner Cursorpositionierung aufhebt.
            QTimer.singleShot(
                0,
                lambda widget=watched, selection=target:
                self._select_if_still_focused(widget, selection),
            )

        return super().eventFilter(watched, event)

    @staticmethod
    def _selection_target(watched: QObject) -> QLineEdit | None:
        if isinstance(watched, QLineEdit):
            if watched.isEnabled() and not watched.isReadOnly():
                return watched
            return None

        if isinstance(watched, QComboBox):
            if watched.isEnabled() and watched.isEditable():
                return watched.lineEdit()
            return None

        if isinstance(watched, QAbstractSpinBox):
            if watched.isEnabled() and not watched.isReadOnly():
                return watched.lineEdit()

        return None

    @staticmethod
    def _select_if_still_focused(
        watched: QObject,
        selection_target: QLineEdit,
    ) -> None:
        if not isinstance(watched, QWidget) or not watched.isEnabled():
            return
        if QApplication.focusWidget() is not watched:
            return
        if selection_target.isReadOnly():
            return
        selection_target.selectAll()


def install_select_all_on_focus(app: QApplication) -> SelectAllOnFocusFilter:
    """Installiert den anwendungsweiten Fokusfilter höchstens einmal."""

    existing = getattr(app, "_simpleob_input_focus_filter", None)
    if isinstance(existing, SelectAllOnFocusFilter):
        return existing

    event_filter = SelectAllOnFocusFilter(app)
    app.installEventFilter(event_filter)
    app._simpleob_input_focus_filter = event_filter
    return event_filter

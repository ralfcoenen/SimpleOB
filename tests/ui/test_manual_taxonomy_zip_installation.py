from unittest.mock import Mock

from PySide6.QtWidgets import QApplication, QMainWindow

from simpleob.ui_qt.main_window import MainWindow


def test_cancelled_taxonomy_zip_picker_does_not_change_anything(
    monkeypatch,
) -> None:
    QApplication.instance() or QApplication([])
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window._workspace = Mock()
    monkeypatch.setattr(
        "simpleob.ui_qt.main_window.QFileDialog.getOpenFileName",
        lambda *_args: ("", ""),
    )

    MainWindow._install_taxonomy_from_zip(window)

    window._workspace.inspect_taxonomy_archive.assert_not_called()
    window._workspace.install_taxonomy_from_archive.assert_not_called()

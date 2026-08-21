"""Hauptfenster der experimentellen PySide6-Oberfläche."""

from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Hauptfenster der PySide6-Oberfläche."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("OpenBilanz – PySide6")
        self.resize(1100, 700)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self.setCentralWidget(central_widget)

        self._create_tabs()

    def _create_tabs(self) -> None:
        """Erzeugt die Hauptarbeitsbereiche."""

        tab_names = (
            "Konten",
            "Journal",
            "Buchen",
            "Anlagen",
            "Bilanz",
            "GuV",
            "Auswertungen",
            "Jahresabschluss",
            "E-Bilanz",
        )

        for tab_name in tab_names:
            self._tabs.addTab(QWidget(), tab_name)

"""PySide6-Hauptfenster von SimpleOB."""

from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    """Minimales Hauptfenster der PySide6-Oberfläche."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("SimpleOB")
        self.resize(1300, 800)
        self.setMinimumSize(1100, 700)

        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)

        title_label = QLabel("SimpleOB")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title_label)

        subtitle_label = QLabel("Buchhaltung und Jahresabschluss")
        layout.addWidget(subtitle_label)

        layout.addStretch()

        self.setCentralWidget(central_widget)

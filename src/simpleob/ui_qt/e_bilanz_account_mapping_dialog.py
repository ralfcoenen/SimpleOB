"""Dialog zur E-Bilanz-Taxonomiezuordnung eines Kontos."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class EBilanzAccountMappingDialog(QDialog):
    """Bearbeitet die Taxonomiezuordnung eines einzelnen Kontos."""

    def __init__(
        self,
        parent: QWidget,
        *,
        account_number: str,
        account_name: str,
        choices: tuple[tuple[str, str], ...],
        current_concept_name: str | None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(
            f"E-Bilanz-Zuordnung – Konto {account_number}"
        )
        self.setMinimumWidth(620)

        self.result: str | None = current_concept_name
        self.saved = False

        self._concept_by_label = {
            label: concept_name
            for concept_name, label in choices
        }

        self._label_by_concept = {
            concept_name: label
            for concept_name, label in choices
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        account_layout = QHBoxLayout()

        account_label = QLabel("Konto:")
        account_layout.addWidget(account_label)

        account_value = QLabel(
            f"{account_number} – {account_name}"
        )
        account_layout.addWidget(account_value, 1)

        layout.addLayout(account_layout)

        taxonomy_layout = QHBoxLayout()

        taxonomy_label = QLabel("Taxonomie 6.9:")
        taxonomy_layout.addWidget(taxonomy_label)

        self._combobox = QComboBox()
        self._combobox.addItems(
            [
                label
                for _, label in choices
            ]
        )
        self._combobox.setMinimumWidth(500)

        if current_concept_name is not None:
            current_label = self._label_by_concept.get(
                current_concept_name
            )

            if current_label is not None:
                self._combobox.setCurrentText(
                    current_label
                )

        taxonomy_layout.addWidget(
            self._combobox,
            1,
        )

        layout.addLayout(taxonomy_layout)

        button_layout = QHBoxLayout()

        remove_button = QPushButton(
            "Zuordnung entfernen"
        )
        remove_button.clicked.connect(
            self._remove
        )
        button_layout.addWidget(remove_button)

        button_layout.addStretch()

        cancel_button = QPushButton(
            "Abbrechen"
        )
        cancel_button.clicked.connect(
            self.reject
        )
        button_layout.addWidget(cancel_button)

        save_button = QPushButton(
            "Speichern"
        )
        save_button.clicked.connect(
            self._save
        )
        save_button.setDefault(True)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

        self._combobox.setFocus()

    def _save(self) -> None:
        """Übernimmt die ausgewählte Taxonomiezuordnung."""

        label = self._combobox.currentText()

        concept_name = self._concept_by_label.get(
            label
        )

        if concept_name is None:
            return

        self.result = concept_name
        self.saved = True
        self.accept()

    def _remove(self) -> None:
        """Entfernt die vorhandene Taxonomiezuordnung."""

        self.result = None
        self.saved = True
        self.accept()

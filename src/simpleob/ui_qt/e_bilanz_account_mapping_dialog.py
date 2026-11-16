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
        current_concept_error: str | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(
            f"E-Bilanz-Zuordnung – Konto {account_number}"
        )
        self.setMinimumWidth(620)

        self.result: str | None = current_concept_name
        self.saved = False

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
        self._combobox.setMinimumWidth(500)
        self._valid_concepts = {
            concept_name
            for concept_name, _label in choices
        }
        if (
            current_concept_name is not None
            and current_concept_name not in self._valid_concepts
        ):
            self._combobox.addItem(
                f"Gespeicherte Zuordnung (nicht bestätigt): "
                f"{current_concept_name}",
                ("unavailable", current_concept_name),
            )
        for concept_name, label in choices:
            self._combobox.addItem(label, concept_name)

        if current_concept_name is not None:
            for index in range(self._combobox.count()):
                data = self._combobox.itemData(index)
                if data == current_concept_name or data == (
                    "unavailable",
                    current_concept_name,
                ):
                    self._combobox.setCurrentIndex(index)
                    break

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        if current_concept_error:
            self._status_label.setText(
                "Die gespeicherte Zuordnung wurde nicht als gültig bestätigt: "
                f"{current_concept_error}"
            )
        elif (
            current_concept_name is not None
            and current_concept_name in self._valid_concepts
        ):
            self._status_label.setText(
                "Die gespeicherte Zuordnung hat genau einen gültigen "
                "Calculation-Pfad."
            )
        elif current_concept_name is None:
            self._status_label.setText(
                "Wählen Sie eine Taxonomieposition aus."
                if choices
                else "Für diese HGB-Position gibt es keine eindeutige "
                "Taxonomieposition zur Auswahl."
            )
        else:
            self._status_label.setText(
                "Die gespeicherte Zuordnung ist in der gültigen Auswahlliste "
                "nicht enthalten. Wählen Sie eine gültige Position oder "
                "entfernen Sie die Zuordnung ausdrücklich."
            )

        taxonomy_layout.addWidget(
            self._combobox,
            1,
        )

        layout.addLayout(taxonomy_layout)
        layout.addWidget(self._status_label)

        button_layout = QHBoxLayout()

        remove_button = QPushButton(
            "Zuordnung entfernen"
        )
        remove_button.clicked.connect(
            self._remove
        )
        remove_button.setEnabled(current_concept_name is not None)
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
        self._save_button = save_button
        self._combobox.currentIndexChanged.connect(
            self._update_save_enabled
        )
        self._update_save_enabled()
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

        self._combobox.setFocus()

    def _save(self) -> None:
        """Übernimmt die ausgewählte Taxonomiezuordnung."""

        concept_name = self._combobox.currentData()
        if (
            not isinstance(concept_name, str)
            or concept_name not in self._valid_concepts
        ):
            return

        self.result = concept_name
        self.saved = True
        self.accept()

    def _update_save_enabled(self) -> None:
        concept_name = self._combobox.currentData()
        self._save_button.setEnabled(
            isinstance(concept_name, str)
            and concept_name in self._valid_concepts
        )

    def _remove(self) -> None:
        """Entfernt die vorhandene Taxonomiezuordnung."""

        self.result = None
        self.saved = True
        self.accept()

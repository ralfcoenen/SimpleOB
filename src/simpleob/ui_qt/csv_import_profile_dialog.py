"""Vierstufiger CSV-Importassistent vor dem bestehenden Buchungsdialog."""

import csv
import re
import unicodedata
from dataclasses import replace
from html import escape
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from simpleob.amount_input import format_german_amount
from simpleob.domain.bank_transaction import BankImportSource, TransactionImportStatus
from simpleob.domain.csv_import_profile import (
    CsvAmount,
    CsvColumn,
    CsvColumns,
    CsvImportProfile,
    CsvStatus,
    qonto_compatibility_profile,
)
from simpleob.importers.bank_csv_errors import BankCsvImportError
from simpleob.importers.profile_csv_importer import ProfileCsvImporter
from simpleob.services.csv_import_profile_store import (
    CsvImportProfileError,
    CsvImportProfileStore,
)

# Reine Vorschläge anhand eindeutiger Spaltennamen, keine zusätzliche Importlogik.
_FIELDS = {
    "external_transaction_id": (
        "Transaktions-ID",
        "Eindeutige Umsatzkennung der Bank; schützt vor erneutem Import.",
        ("Umsatzkennung", "Transaction ID", "Transaktions-ID"),
        True,
    ),
    "booking_date": (
        "Buchungsdatum",
        "Tag, an dem die Bank den Umsatz gebucht hat.",
        ("Buchungstag", "Settlement date (local)", "Buchungsdatum"),
        True,
    ),
    "currency": (
        "Währung",
        "Währungskürzel des Umsatzes, zum Beispiel EUR.",
        ("Waehrung", "Currency", "Währung"),
        True,
    ),
    "transaction_date": (
        "Transaktionsdatum",
        "Optional: Tag des ursprünglichen Zahlungsvorgangs.",
        ("Operation date (local)", "Transaktionsdatum"),
        False,
    ),
    "counterparty": (
        "Zahlungspartner",
        "Optional: Name des Empfängers oder Absenders.",
        ("Partner", "Counterparty name", "Zahlungspartner"),
        False,
    ),
    "reference": (
        "Verwendungszweck",
        "Optional: Referenz oder Beschreibung der Zahlung.",
        ("Verwendungszweck", "Reference", "Referenz"),
        False,
    ),
    "amount": (
        "Betrag",
        "Vollständiger Betrag einschließlich Cent; Vorzeichen siehe unten.",
        ("Betrag_EUR", "Total amount (incl. VAT)", "Betrag"),
        True,
    ),
    "inflow": (
        "Zahlungseingang",
        "Bei getrennten Spalten: positiver Betrag oder leer/null.",
        ("Zahlungseingang", "Eingang"),
        True,
    ),
    "outflow": (
        "Zahlungsausgang",
        "Bei getrennten Spalten: positiver Betrag oder leer/null.",
        ("Zahlungsausgang", "Ausgang"),
        True,
    ),
    "status": (
        "Buchungsstatus",
        "Unterscheidet abgewickelte von vorgemerkten Umsätzen.",
        ("Bearbeitungsstand", "Status"),
        True,
    ),
}


class _ImportPage(QWizardPage):
    def __init__(self, owner, step, title, explanation):
        super().__init__(owner)
        self.owner = owner
        self.step = step
        self.setTitle(f"Schritt {step + 1} von 4 – {title}")
        self.setSubTitle(explanation)

    def initializePage(self):
        self.owner._enter_step(self.step)

    def validatePage(self):
        return self.owner._validate_step(self.step)

    def isComplete(self):
        return bool(self.owner.transactions) if self.step == 2 else True

    def cleanupPage(self):
        # Eingaben beim Zurückgehen behalten; Vorschauen werden ausdrücklich invalidiert.
        pass


class CsvImportProfileDialog(QWizard):
    """Prüft CSV mit ProfileCsvImporter, speichert und übergibt geprüfte Umsätze."""

    def __init__(
        self,
        *,
        parent,
        profile=None,
        profiles=None,
        csv_path=None,
        profile_store=None,
        edit_mapping=False,
        persist_profile=False,
    ):
        super().__init__(parent)
        self.setWindowTitle("CSV-Importassistent")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        # Explizite leere Grafiken vermeiden native macOS-Bundle-Abfragen, auch offscreen.
        background = QPixmap(1, 1)
        background.fill(Qt.GlobalColor.transparent)
        self.setPixmap(QWizard.WizardPixmap.BackgroundPixmap, background)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage)
        self.setButtonText(QWizard.WizardButton.BackButton, "Zurück")
        self.setButtonText(QWizard.WizardButton.NextButton, "Weiter")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Abbrechen")
        self.setButtonText(
            QWizard.WizardButton.FinishButton, "Profil speichern und zum Bankimport"
        )
        available = self.screen().availableGeometry()
        self.setMinimumSize(
            min(820, available.width() - 30), min(540, available.height() - 60)
        )
        self.resize(
            min(1040, available.width() - 30), min(760, available.height() - 60)
        )
        self.setSizeGripEnabled(True)
        self._store = (
            profile_store if profile_store is not None else CsvImportProfileStore()
        )
        self._profiles = tuple(profiles) if profiles is not None else self._store.load()
        self._persist_profile = persist_profile
        self._original = None
        self._source_manually_set = False
        self._updating_source = False
        self._profile_id = uuid4()
        self._csv_path = Path(csv_path) if csv_path is not None else None
        self._headers = ()
        self._sample_rows = []
        self._header_settings = None
        self._checked_profile = None
        self._checked_bytes = None
        self.transactions = ()
        self.profile = None
        self._bindings = {}
        self._required = {}
        self._loaded_bindings = {}
        self._status_defaults = {}
        self._make_file_page()
        self._make_mapping_page()
        self._make_review_page()
        self._make_save_page()
        self._error = QPlainTextEdit()
        self._error.setReadOnly(True)
        self._error.setMaximumHeight(90)
        self._error.setStyleSheet("color: #9b1c1c;")
        self._error.hide()
        self.setSideWidget(None)
        # Fehler innerhalb jeder Seite anzeigen, damit die Navigation sichtbar bleibt.
        self.currentIdChanged.connect(self._move_error)
        self._connect_changes()
        if profile is not None:
            index = next(
                (
                    index
                    for index in range(1, self._profile_combo.count())
                    if self._profile_combo.itemData(index).profile_id
                    == profile.profile_id
                ),
                -1,
            )
            if index < 0:
                raise CsvImportProfileError(
                    "Das ausgewählte Profil ist nicht mehr vorhanden."
                )
            self._profile_combo.setCurrentIndex(index)
        else:
            self._apply_profile()
        self._edit_mapping.setChecked(edit_mapping)
        self._update_flow()
        if self._csv_path:
            self._update_file_name()

    def _page(self, step, title, text, scroll=False):
        page = _ImportPage(self, step, title, text)
        outer = QVBoxLayout(page)
        if scroll:
            area = QScrollArea()
            area.setWidgetResizable(True)
            if step == 3:
                area.setFrameShape(QFrame.Shape.NoFrame)
            body = QWidget()
            layout = QVBoxLayout(body)
            area.setWidget(body)
            outer.addWidget(area)
        else:
            layout = outer
        self.addPage(page)
        return layout

    @staticmethod
    def _combo(options):
        combo = QComboBox()
        for label, value in options:
            combo.addItem(label, value)
        return combo

    def _make_file_page(self):
        layout = self._page(
            0,
            "CSV-Datei auswählen",
            "Wählen Sie zuerst die Datei. Ein gespeichertes Profil übernimmt die bisherigen Einstellungen.",
        )
        form = QFormLayout()
        self._profile_combo = QComboBox()
        self._profile_combo.addItem("Neues Profil einrichten", None)
        for profile in self._profiles:
            self._profile_combo.addItem(profile.name, profile)
        form.addRow("Gespeichertes Profil (optional)", self._profile_combo)
        self._edit_mapping = QCheckBox(
            "Spaltenzuordnung und Formate vor der Prüfung bearbeiten"
        )
        form.addRow(self._edit_mapping)
        file_row = QHBoxLayout()
        self._file_name = QLineEdit()
        self._file_name.setReadOnly(True)
        self._file_name.setPlaceholderText("Noch keine CSV-Datei ausgewählt")
        choose = QPushButton("CSV-Datei auswählen …")
        choose.clicked.connect(self._choose_file)
        file_row.addWidget(self._file_name, 1)
        file_row.addWidget(choose)
        form.addRow(QLabel("CSV-Datei"))
        form.addRow(file_row)
        self._delimiter = self._combo(
            [
                ("Semikolon (;)", ";"),
                ("Komma (,)", ","),
                ("Tabulator", "\t"),
                ("Strich (|)", "|"),
            ]
        )
        self._delimiter.setEditable(True)
        form.addRow("Spalten getrennt durch", self._delimiter)
        self._encoding = self._combo(
            [
                ("UTF-8 (üblich)", "utf-8"),
                ("UTF-8 mit Dateikennung", "utf-8-sig"),
                ("Windows (Westeuropa)", "cp1252"),
                ("ISO Westeuropa", "iso-8859-1"),
                ("UTF-16", "utf-16"),
            ]
        )
        form.addRow("Zeichencodierung", self._encoding)
        read = QPushButton("Kopfzeile einlesen / aktualisieren")
        read.clicked.connect(self._read_headers)
        form.addRow(read)
        layout.addLayout(form)
        self._column_label = QLabel(
            "Nach dem Einlesen werden hier alle erkannten Spalten angezeigt."
        )
        self._column_label.setWordWrap(True)
        layout.addWidget(self._column_label)
        self._column_names = QListWidget()
        self._column_names.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._column_names.setMaximumHeight(210)
        layout.addWidget(self._column_names)
        note = QLabel(
            "Es wird noch nichts gebucht. Profile gelten für alle Mandanten; das Bank-Sachkonto wählen Sie anschließend im Bankimport."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self._qonto_notice = QLabel()
        self._qonto_notice.setWordWrap(True)
        layout.addWidget(self._qonto_notice)
        layout.addStretch(1)

    def _make_mapping_page(self):
        layout = self._page(
            1,
            "CSV-Spalten zuordnen",
            "Ordnen Sie die erkannten Spalten zu. Pflichtfelder sind mit „erforderlich“ bezeichnet; optionale Felder können leer bleiben.",
            scroll=True,
        )
        self._mapping_table = QTableWidget(len(_FIELDS), 3)
        self._mapping_table.setHorizontalHeaderLabels(
            ["Bedeutung in SimpleOB", "Zugeordnete CSV-Spalte", "Erklärung"]
        )
        self._mapping_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._mapping_table.verticalHeader().hide()
        self._mapping_table.setColumnWidth(0, 180)
        self._mapping_table.setColumnWidth(2, 230)
        self._mapping_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._mapping_table.setWordWrap(True)
        for row, (key, (label, explanation, _aliases, mandatory)) in enumerate(
            _FIELDS.items()
        ):
            self._mapping_table.setItem(
                row,
                0,
                QTableWidgetItem(
                    label + (" (erforderlich)" if mandatory else " (optional)")
                ),
            )
            self._mapping_table.setItem(row, 2, QTableWidgetItem(explanation))
            combo = QComboBox()
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            combo.setMinimumContentsLength(22)
            combo.currentIndexChanged.connect(
                lambda _index, key=key: self._binding_changed(key)
            )
            self._bindings[key] = combo
            self._mapping_table.setCellWidget(row, 1, combo)
            self._mapping_table.setRowHeight(row, 48)
        layout.addWidget(self._mapping_table)
        form = QFormLayout()
        self._amount_model = self._combo(
            [
                ("Eine Betragsspalte mit positiven und negativen Werten", "signed"),
                (
                    "Getrennte Spalten für Zahlungseingang und Zahlungsausgang",
                    "separate",
                ),
            ]
        )
        self._positive = self._combo(
            [
                ("Positive Werte sind Zahlungseingänge", "inflow"),
                ("Positive Werte sind Zahlungsausgänge", "outflow"),
            ]
        )
        form.addRow("Betragsmodell", self._amount_model)
        form.addRow("Vorzeichen", self._positive)
        self._assume_settled = QCheckBox(
            "Keine Statusspalte: Ich bestätige, dass alle Umsätze endgültig abgewickelt sind."
        )
        form.addRow(self._assume_settled)
        layout.addLayout(form)
        self._status_table = QTableWidget(0, 2)
        self._status_table.setHorizontalHeaderLabels(
            ["Status in der CSV-Datei", "Bedeutung in SimpleOB"]
        )
        self._status_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._status_table.setMinimumHeight(115)
        self._status_table.setMaximumHeight(165)
        layout.addWidget(self._status_table)
        row = QHBoxLayout()
        add = QPushButton("Weiteren Statuswert zuordnen")
        add.clicked.connect(lambda: self._add_status())
        remove = QPushButton("Ausgewählten Status entfernen")
        remove.clicked.connect(self._remove_status)
        row.addWidget(add)
        row.addWidget(remove)
        layout.addLayout(row)
        formats = QFormLayout()
        self._unmapped = self._combo(
            [
                ("Als Fehler melden", "error"),
                ("Nicht buchen (nicht abgewickelt)", "not_settled"),
            ]
        )
        self._case_sensitive = QCheckBox(
            "Groß-/Kleinschreibung der Statuswerte unterscheiden"
        )
        self._date_format = self._combo(
            [
                ("16.11.2026 – Tag.Monat.Jahr", "%d.%m.%Y"),
                ("2026-11-16 – Jahr-Monat-Tag", "%Y-%m-%d"),
                ("16/11/2026 – Tag/Monat/Jahr", "%d/%m/%Y"),
            ]
        )
        self._decimal = self._combo([("Komma (119,00)", ","), ("Punkt (119.00)", ".")])
        self._thousands = self._combo(
            [
                ("Keines (1234)", None),
                ("Punkt (1.234)", "."),
                ("Komma (1,234)", ","),
                ("Leerzeichen (1 234)", " "),
                ("Apostroph (1’234)", "'"),
                ("Geschütztes Leerzeichen", "\u00a0"),
            ]
        )
        formats.addRow("Nicht zugeordnete Statuswerte", self._unmapped)
        formats.addRow(self._case_sensitive)
        formats.addRow("Datumsformat", self._date_format)
        formats.addRow("Dezimaltrennzeichen", self._decimal)
        formats.addRow("Tausendertrennzeichen", self._thousands)
        layout.addLayout(formats)
        layout.addStretch(1)

    def _make_review_page(self):
        layout = self._page(
            2,
            "Bankumsätze prüfen",
            "Dies ist eine reine Vorschau. Wählen Sie einen Umsatz für seine Details. Vorgemerkte Umsätze gelangen nicht in die Buchungsvorschläge.",
        )
        self._review_summary = QLabel()
        self._review_summary.setWordWrap(True)
        layout.addWidget(self._review_summary)
        self._preview = QTableWidget(0, 5)
        self._preview.setHorizontalHeaderLabels(
            [
                "Buchungsdatum",
                "Zahlungspartner",
                "Verwendungszweck",
                "Betrag",
                "Buchungsstatus",
            ]
        )
        self._preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._preview.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._preview.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for column, width in ((0, 110), (1, 180), (3, 105), (4, 175)):
            self._preview.setColumnWidth(column, width)
        self._preview.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._preview.setMinimumHeight(140)
        self._preview.currentCellChanged.connect(self._show_details)
        layout.addWidget(self._preview, 3)
        self._detail_heading = QLabel(
            "Wählen Sie einen Umsatz, um Originalwerte und Interpretation zu vergleichen."
        )
        self._detail_heading.setWordWrap(True)
        layout.addWidget(self._detail_heading)
        self._details = QTableWidget(0, 3)
        self._details.setHorizontalHeaderLabels(
            ["CSV-Spalte", "CSV-Originalwert", "Interpretierter Wert"]
        )
        self._details.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._details.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._details.setMinimumHeight(130)
        layout.addWidget(self._details, 2)

    def _make_save_page(self):
        layout = self._page(
            3,
            "Profil speichern",
            "Speichern Sie die geprüften Einstellungen für spätere Importe. Anschließend wählen Sie im Bankimport Konten und bestätigen die Buchungen.",
            scroll=True,
        )
        form = QFormLayout()
        self._name = QLineEdit()
        form.addRow("Profilname", self._name)
        self._source = QComboBox()
        self._source.setEditable(True)
        self._source.addItems(sorted({p.import_source.value for p in self._profiles}))
        self._source.setCurrentText("")
        form.addRow("Dauerhafte Quellenkennung", self._source)
        layout.addLayout(form)
        self._source_help = QLabel(
            "Für eine bereits verwendete Bankquelle dieselbe Kennung auswählen. Eine neue Kennung trennt die Duplikatprüfung von bisherigen Importen. Zulässig sind Kleinbuchstaben, Ziffern, Punkt, Bindestrich und Unterstrich; Beginn mit einem Buchstaben, z. B. meine_bank."
        )
        self._source_help.setWordWrap(True)
        layout.addWidget(self._source_help)
        self._settings_summary = QLabel()
        self._settings_summary.setTextFormat(Qt.TextFormat.RichText)
        self._settings_summary.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        self._settings_summary.setWordWrap(True)
        self._settings_summary.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._settings_summary)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    def _connect_changes(self):
        self._name.textChanged.connect(self._suggest_source)
        self._source.editTextChanged.connect(self._source_edited)
        self._source.activated.connect(self._source_edited)
        self._profile_combo.currentIndexChanged.connect(self._apply_profile)
        self._edit_mapping.toggled.connect(self._update_flow)
        for combo in (self._delimiter, self._encoding):
            combo.currentIndexChanged.connect(self._file_settings_changed)
        self._delimiter.editTextChanged.connect(self._file_settings_changed)
        for combo in (
            self._date_format,
            self._decimal,
            self._thousands,
            self._amount_model,
            self._positive,
            self._unmapped,
        ):
            combo.currentIndexChanged.connect(self._mapping_changed)
        self._assume_settled.toggled.connect(self._mapping_changed)
        self._case_sensitive.toggled.connect(self._invalidate)
        self._status_table.itemChanged.connect(self._invalidate)

    @staticmethod
    def _select(combo, value, label=None):
        index = combo.findData(value)
        if index < 0:
            combo.addItem(label or str(value), value)
            index = combo.count() - 1
        combo.setCurrentIndex(index)

    def _apply_profile(self, *_args):
        self._original = self._profile_combo.currentData()
        p = self._original or qonto_compatibility_profile()
        self._profile_id = p.profile_id if self._original else uuid4()
        self._edit_mapping.setVisible(self._original is not None)
        self._edit_mapping.setChecked(False)
        self._source_manually_set = False
        self._updating_source = True
        self._name.setText(p.name if self._original else "")
        self._source.setCurrentText(p.import_source.value if self._original else "")
        self._source.setEnabled(self._original is None)
        self._source.setToolTip("")
        self._updating_source = False
        self._select(self._delimiter, p.delimiter)
        self._select(self._encoding, p.encoding)
        self._select(
            self._date_format,
            p.date_format,
            "Bestehendes Datumsformat: " + p.date_format,
        )
        self._select(self._decimal, p.decimal_separator)
        self._select(self._thousands, p.thousands_separator)
        self._select(self._amount_model, p.amount.model)
        self._select(self._positive, p.amount.positive_means)
        self._select(self._unmapped, p.status.unmapped)
        self._case_sensitive.setChecked(p.status.case_sensitive)
        self._assume_settled.setChecked(
            p.status.assume_settled if self._original else False
        )
        self._loaded_bindings = (
            {key: getattr(p.columns, key) for key in CsvColumns.__dataclass_fields__}
            if self._original
            else {}
        )
        if self._original:
            self._loaded_bindings.update(
                amount=p.amount.column,
                inflow=p.amount.inflow_column,
                outflow=p.amount.outflow_column,
                status=p.status.column,
            )
        self._status_defaults = dict(p.status.mapping) if self._original else {}
        self._qonto_notice.setText(
            "Das synthetische Qonto-Testprofil bestätigt keine Kompatibilität mit originalen Qonto-Exporten."
            if self._original and p.import_source.value == "qonto_csv"
            else ""
        )
        self._file_settings_changed()
        self._update_mapping_controls()
        self._update_flow()

    def _source_edited(self, *_args):
        if not self._updating_source:
            self._source_manually_set = True
            self._source.setToolTip("")

    def _suggest_source(self, name):
        if self._original or self._source_manually_set or self._updating_source:
            return
        text = (
            unicodedata.normalize("NFKD", name.casefold())
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        suggestion = re.sub(r"[^a-z0-9_.-]+", "_", text).strip("._-")
        if suggestion and not suggestion[0].isalpha():
            suggestion = "csv_" + suggestion
        suggestion = suggestion[:128]
        # Ein Vorschlag darf nicht unbemerkt einen vorhandenen Namensraum auswählen.
        collision = suggestion in {p.import_source.value for p in self._profiles}
        self._updating_source = True
        try:
            self._source.setCurrentText("" if collision else suggestion)
        finally:
            self._updating_source = False
        self._source.setToolTip(
            "Diese Quellenkennung ist bereits vorhanden. Wählen Sie die bestehende Quelle bewusst aus oder geben Sie eine neue Kennung ein."
            if collision
            else "Vorschlag aus dem Profilnamen; Sie können ihn vor dem Speichern bearbeiten."
        )

    def _update_file_name(self):
        self._file_name.setText(self._csv_path.name)
        self._file_name.setToolTip(str(self._csv_path))
        self._file_name.setCursorPosition(0)

    def _delimiter_value(self):
        index = self._delimiter.currentIndex()
        return (
            self._delimiter.itemData(index)
            if index >= 0
            and self._delimiter.currentText() == self._delimiter.itemText(index)
            else self._delimiter.currentText()
        )

    def _file_settings_changed(self, *_args):
        self._header_settings = None
        self._headers = ()
        self._column_names.clear()
        self._column_label.setText("Kopfzeile bitte einlesen / aktualisieren.")
        self._invalidate()

    def _invalidate(self, *_args):
        self.transactions = ()
        self._checked_profile = None
        self._checked_bytes = None
        self._preview.setRowCount(0)
        self._details.setRowCount(0)
        self._detail_heading.setText("Wählen Sie einen Umsatz für die Details.")
        self._review_summary.clear()
        self.page(2).completeChanged.emit()

    def _binding_changed(self, key):
        combo = self._bindings[key]
        combo.setToolTip(combo.currentData() or "Keine Spalte zugeordnet")
        self._invalidate()
        if key == "status":
            self._populate_status()

    def _mapping_changed(self, *_args):
        self._update_mapping_controls()
        self._invalidate()

    def _update_mapping_controls(self):
        signed = self._amount_model.currentData() == "signed"
        for key in ("amount", "inflow", "outflow", "status"):
            visible = (
                (signed if key == "amount" else not signed)
                if key != "status"
                else not self._assume_settled.isChecked()
            )
            self._mapping_table.setRowHidden(list(_FIELDS).index(key), not visible)
        rows = sum(
            not self._mapping_table.isRowHidden(row) for row in range(len(_FIELDS))
        )
        self._mapping_table.setFixedHeight(
            rows * 48 + self._mapping_table.horizontalHeader().height() + 4
        )
        self._positive.setEnabled(signed)
        for widget in (self._status_table, self._case_sensitive, self._unmapped):
            widget.setEnabled(not self._assume_settled.isChecked())

    def _choose_file(self):
        name, _ = QFileDialog.getOpenFileName(
            self,
            "CSV-Datei auswählen",
            str(self._csv_path or ""),
            "CSV-Dateien (*.csv);;Alle Dateien (*)",
        )
        if name:
            self._csv_path = Path(name)
            self._update_file_name()
            self._file_settings_changed()
            self._read_headers()

    def _show_error(self, message=""):
        self._error.setPlainText(message)
        self._error.setVisible(bool(message))

    def _move_error(self, step):
        if step >= 0:
            self.page(step).layout().addWidget(self._error)

    def _read_headers(self):
        previous_settings = self._header_settings
        previous_headers = self._headers
        self._invalidate()
        self._headers = ()
        self._column_names.clear()
        try:
            if self._csv_path is None:
                raise ValueError("Bitte zuerst eine CSV-Datei auswählen.")
            delimiter = self._delimiter_value()
            if (
                not isinstance(delimiter, str)
                or len(delimiter) != 1
                or delimiter in '\r\n\0"'
            ):
                raise ValueError(
                    "Bitte ein einzelnes gültiges Spaltentrennzeichen wählen."
                )
            with self._csv_path.open(
                encoding=self._encoding.currentData(), newline=""
            ) as stream:
                reader = csv.reader(stream, delimiter=delimiter, strict=True)
                headers = next(reader, None)
                if (
                    not headers
                    or any(not h.strip() for h in headers)
                    or len(headers) != len(set(headers))
                ):
                    raise ValueError(
                        "Zeile 1: Kopfzeile fehlt oder enthält leere bzw. doppelte Spaltennamen."
                    )
                self._sample_rows = []
                for index, row in enumerate(reader):
                    if index >= 100:
                        break
                    if len(row) == len(headers):
                        self._sample_rows.append(dict(zip(headers, row, strict=True)))
            self._headers = tuple(headers)
            self._header_settings = (
                self._csv_path,
                delimiter,
                self._encoding.currentData(),
            )
            self._column_names.addItems(headers)
            self._column_label.setText(
                f"{len(headers)} Spalten erkannt. Die vollständigen Namen sind unten sichtbar."
            )
            if (
                previous_settings != self._header_settings
                or previous_headers != self._headers
            ):
                self._populate_bindings()
            self._show_error()
            return True
        except (
            OSError,
            UnicodeError,
            LookupError,
            csv.Error,
            TypeError,
            ValueError,
        ) as exc:
            self._header_settings = None
            self._column_label.setText("Die Kopfzeile konnte nicht gelesen werden.")
            self._show_error(f"CSV-Datei konnte nicht gelesen werden: {exc}")
            return False

    def _populate_bindings(self):
        for key, (_label, _explanation, aliases, mandatory) in _FIELDS.items():
            combo = self._bindings[key]
            old = self._loaded_bindings.get(key)
            selected = old.column if old else None
            if not self._original:
                matches = [
                    h
                    for h in self._headers
                    if h.casefold() in {a.casefold() for a in aliases}
                ]
                selected = matches[0] if len(matches) == 1 else None
            self._required[key] = old.required if old else mandatory
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(
                "Bitte zuordnen" if mandatory else "Nicht übernehmen (optional)", None
            )
            for header in self._headers:
                combo.addItem(header, header)
            if selected and combo.findData(selected) < 0:
                combo.addItem(selected + " – fehlt in der Datei", selected)
            combo.setCurrentIndex(max(0, combo.findData(selected)))
            combo.blockSignals(False)
            combo.setToolTip(selected or "Keine Spalte zugeordnet")
            popup_width = (
                max(
                    (combo.fontMetrics().horizontalAdvance(h) for h in self._headers),
                    default=300,
                )
                + 60
            )
            combo.view().setMinimumWidth(
                min(
                    max(400, popup_width),
                    self.screen().availableGeometry().width() - 40,
                )
            )
        self._populate_status()
        self._update_mapping_controls()

    def _add_status(self, key="", target=None):
        row = self._status_table.rowCount()
        self._status_table.insertRow(row)
        self._status_table.setItem(row, 0, QTableWidgetItem(key))
        combo = self._combo(
            [
                ("Bitte zuordnen", None),
                ("Abgewickelt – buchbar", "ready"),
                ("Vorgemerkt / nicht buchbar", "not_settled"),
            ]
        )
        combo.setCurrentIndex(max(0, combo.findData(target)))
        combo.currentIndexChanged.connect(self._invalidate)
        self._status_table.setCellWidget(row, 1, combo)
        self._invalidate()

    def _remove_status(self):
        self._status_table.removeRow(self._status_table.currentRow())
        self._invalidate()

    def _populate_status(self):
        self._status_table.setRowCount(0)
        column = self._bindings["status"].currentData()
        observed = list(
            dict.fromkeys(
                row.get(column, "").strip()
                for row in self._sample_rows
                if row.get(column, "").strip()
            )
        )
        defaults = self._status_defaults
        normalize = (
            (lambda text: text) if self._case_sensitive.isChecked() else str.casefold
        )
        keys = list(defaults)
        seen = {normalize(key) for key in keys}
        for key in observed:
            if normalize(key) not in seen:
                keys.append(key)
                seen.add(normalize(key))
        for key in keys:
            target = defaults.get(key)
            if target is None and not self._original:
                target = {
                    "gebucht": "ready",
                    "completed": "ready",
                    "vorgemerkt": "not_settled",
                    "pending": "not_settled",
                }.get(key.casefold())
            if target is None and self._unmapped.currentData() == "not_settled":
                target = "not_settled"
            self._add_status(key, target)

    def _binding(self, key):
        name = self._bindings[key].currentData()
        return CsvColumn(name, self._required[key]) if name else None

    def _build_profile(self, final=False):
        required = ["external_transaction_id", "booking_date", "currency"]
        required += (
            ["amount"]
            if self._amount_model.currentData() == "signed"
            else ["inflow", "outflow"]
        )
        if not self._assume_settled.isChecked():
            required.append("status")
        missing = []
        for key, combo in self._bindings.items():
            absent = key in required and not combo.currentData()
            combo.setStyleSheet("border: 1px solid #9b1c1c;" if absent else "")
            if absent:
                missing.append(_FIELDS[key][0])
        if missing:
            raise ValueError("Bitte CSV-Spalten zuordnen: " + ", ".join(missing))
        if self._amount_model.currentData() == "signed":
            amount = CsvAmount(
                "signed", self._binding("amount"), self._positive.currentData()
            )
        else:
            amount = CsvAmount(
                "separate",
                inflow_column=self._binding("inflow"),
                outflow_column=self._binding("outflow"),
            )
        if self._assume_settled.isChecked():
            status = CsvStatus(assume_settled=True)
        else:
            mapping = []
            for row in range(self._status_table.rowCount()):
                key = self._status_table.item(row, 0).text().strip()
                target = self._status_table.cellWidget(row, 1).currentData()
                if not key or target is None:
                    raise ValueError(
                        "Bitte jeden aufgeführten Statuswert einer Bedeutung zuordnen oder die betreffende Zeile entfernen."
                    )
                mapping.append((key, target))
            status = CsvStatus(
                self._binding("status"),
                tuple(mapping),
                self._case_sensitive.isChecked(),
                self._unmapped.currentData(),
            )
        if self._original:
            source = self._original.import_source
        else:
            try:
                source = BankImportSource(
                    self._source.currentText().strip() if final else "csv_preview"
                )
            except ValueError as exc:
                raise ValueError(
                    "Ungültige Quellenkennung. Verwenden Sie 1 bis 128 Zeichen: "
                    "Kleinbuchstaben a–z, Ziffern, Punkt, Bindestrich oder Unterstrich. "
                    "Die Kennung muss mit einem Kleinbuchstaben beginnen, z. B. test_development."
                ) from exc
        name = (
            self._name.text().strip()
            if final
            else (self._original.name if self._original else "Vorschau")
        )
        if final and not name:
            raise ValueError("Bitte einen verständlichen Profilnamen eingeben.")
        profile = CsvImportProfile(
            self._profile_id,
            name,
            source,
            self._delimiter_value(),
            self._encoding.currentData(),
            self._date_format.currentData(),
            self._decimal.currentData(),
            self._thousands.currentData(),
            CsvColumns(
                **{key: self._binding(key) for key in CsvColumns.__dataclass_fields__}
            ),
            amount,
            status,
        )
        missing_headers = [
            b.column
            for b in profile.bindings()
            if b.required and b.column not in self._headers
        ]
        if missing_headers:
            raise ValueError(
                "Diese zugeordneten Spalten fehlen in der Datei: "
                + ", ".join(missing_headers)
            )
        return profile

    def _will_save_profile(self):
        return self._original is None or self._persist_profile

    def _direct_import(self):
        return not self._will_save_profile() and not self._edit_mapping.isChecked()

    def _update_flow(self, *_args):
        save = self._will_save_profile()
        self.page(0).setFinalPage(self._direct_import())
        self.page(2).setFinalPage(not save)
        self.setButtonText(
            QWizard.WizardButton.FinishButton,
            "Profil speichern und zum Bankimport" if save else "Zum Bankimport",
        )
        total = 4 if save else 3
        for step, title in enumerate(
            ("CSV-Datei auswählen", "CSV-Spalten zuordnen", "Bankumsätze prüfen")
        ):
            self.page(step).setTitle(
                title
                if step == 0 and self._direct_import()
                else f"Schritt {step + 1} von {total} – {title}"
            )
        self.page(0).completeChanged.emit()

    def nextId(self):
        if self.currentId() == 0 and self._direct_import():
            return -1
        if self.currentId() == 2 and not self._will_save_profile():
            return -1
        return super().nextId()

    def _enter_step(self, step):
        self._show_error()
        if step == 2:
            self._interpret()
        elif step == 3:
            p = self._checked_profile
            if p:
                rows = [
                    ("Datei", self._csv_path.name),
                    (
                        "Geprüft",
                        f"{len(self.transactions)} Umsätze; keine Buchung ausgeführt.",
                    ),
                    (
                        "CSV",
                        f"{self._delimiter.currentText()}; {self._encoding.currentText()}",
                    ),
                    (
                        "Datum / Zahlen",
                        f"{self._date_format.currentText()}; {self._decimal.currentText()}; Tausender: {self._thousands.currentText()}",
                    ),
                    (
                        "Beträge",
                        self._amount_model.currentText()
                        + (
                            "; " + self._positive.currentText()
                            if p.amount.model == "signed"
                            else "; getrennte Eingangs- und Ausgangsspalten"
                        ),
                    ),
                ]
                for key, (label, *_rest) in _FIELDS.items():
                    binding = self._binding(key)
                    if binding and (
                        key not in ("amount", "inflow", "outflow", "status")
                        or key
                        in (
                            ("amount",)
                            if p.amount.model == "signed"
                            else ("inflow", "outflow")
                        )
                        or (key == "status" and p.status.column)
                    ):
                        rows.append((label, binding.column))
                rows.append(
                    (
                        "Status",
                        "Alle Umsätze ausdrücklich als abgewickelt bestätigt."
                        if p.status.assume_settled
                        else "; ".join(
                            f"{key} → {'buchbar' if target == 'ready' else 'nicht buchbar'}"
                            for key, target in p.status.mapping
                        ),
                    )
                )
                self._settings_summary.setText(
                    '<table cellspacing="0" cellpadding="1">'
                    + "".join(
                        f'<tr><td valign="top"><b>{escape(label)}</b></td>'
                        f"<td>{escape(value)}</td></tr>"
                        for label, value in rows
                    )
                    + "</table>"
                )

    def _validate_step(self, step):
        self._show_error()
        try:
            if step == 0:
                if not self._read_headers():
                    return False
                if self._direct_import():
                    if not self._interpret(self._original):
                        self._show_error(
                            self._error.toPlainText()
                            + "\nAktivieren Sie „Spaltenzuordnung und Formate vor der Prüfung bearbeiten“, um die Zuordnung nur für diesen Import zu korrigieren."
                        )
                        return False
                    return self._finish_import()
                return True
            if step == 1:
                self._build_profile()
            elif step == 2:
                if not self.transactions:
                    raise ValueError(
                        "Die Datei muss zuerst fehlerfrei interpretiert werden. Bitte die Zuordnung im vorherigen Schritt korrigieren."
                    )
                if not self._will_save_profile():
                    return self._finish_import()
            elif step == 3:
                return self._save_profile()
            return True
        except (ValueError, OSError) as exc:
            self._show_error(str(exc))
            return False

    def _interpret(self, profile=None):
        self._invalidate()
        try:
            profile = profile if profile is not None else self._build_profile()
            before = self._csv_path.read_bytes()
            transactions = ProfileCsvImporter(profile).load(self._csv_path)
            if self._csv_path.read_bytes() != before:
                raise ValueError(
                    "Die CSV-Datei wurde während der Prüfung geändert. Bitte erneut prüfen."
                )
            self._checked_profile = profile
            self._checked_bytes = before
            self.transactions = transactions
            ready = sum(
                t.import_validation_status is TransactionImportStatus.READY
                for t in transactions
            )
            self._review_summary.setText(
                f"{len(transactions)} Transaktionen: {ready} buchbar, {len(transactions) - ready} vorgemerkt / nicht buchbar. Noch keine Buchung ausgeführt."
            )
            self._preview.setRowCount(len(transactions))
            self._preview.setMaximumHeight(
                min(
                    320,
                    max(
                        150,
                        len(transactions)
                        * self._preview.verticalHeader().defaultSectionSize()
                        + self._preview.horizontalHeader().height()
                        + 4,
                    ),
                )
            )
            for row, t in enumerate(transactions):
                is_ready = t.import_validation_status is TransactionImportStatus.READY
                values = (
                    t.booking_date.strftime("%d.%m.%Y"),
                    t.counterparty or "",
                    t.reference or "",
                    ("+" if t.amount > 0 else "") + format_german_amount(t.amount),
                    "Abgewickelt – buchbar"
                    if is_ready
                    else "Vorgemerkt / nicht buchbar",
                )
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setToolTip(value)
                    if column == 4:
                        item.setForeground(QColor("#176b35" if is_ready else "#925b00"))
                    self._preview.setItem(row, column, item)
            self._preview.selectRow(0)
            self._show_error()
        except (BankCsvImportError, ValueError, OSError) as exc:
            self._review_summary.setText(
                "Die Datei enthält Fehler. Es werden keine Buchungsvorschläge freigegeben. Gehen Sie zur Zuordnung zurück."
            )
            self._show_error(str(exc))
        self.page(2).completeChanged.emit()
        return bool(self.transactions)

    def _show_details(self, row, *_args):
        if row < 0 or row >= len(self.transactions):
            return
        t = self.transactions[row]
        self._detail_heading.setText(
            f"Externe Transaktionskennung: {t.external_transaction_id} · CSV-Zeile {t.source_record.line_number}"
        )
        profile = self._checked_profile
        interpreted = {}
        for key in CsvColumns.__dataclass_fields__:
            binding = getattr(profile.columns, key)
            if binding:
                value = getattr(t, key)
                interpreted[binding.column] = str(value or "")
        for binding in (
            profile.amount.column,
            profile.amount.inflow_column,
            profile.amount.outflow_column,
        ):
            if binding:
                interpreted[binding.column] = (
                    "+" if t.amount > 0 else ""
                ) + format_german_amount(t.amount)
        if profile.status.column:
            interpreted[profile.status.column.column] = (
                "Abgewickelt – buchbar"
                if t.import_validation_status is TransactionImportStatus.READY
                else "Vorgemerkt / nicht buchbar"
            )
        self._details.setRowCount(len(t.source_record.headers))
        for index, (header, raw) in enumerate(
            zip(t.source_record.headers, t.source_record.values, strict=True)
        ):
            for column, value in enumerate(
                (header, raw, interpreted.get(header, "Nicht übernommen"))
            ):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self._details.setItem(index, column, item)

    def _validate_checked_import(self, profile):
        if not self.transactions or self._checked_profile is None:
            raise ValueError("Bitte die Umsätze vor der Übergabe erneut prüfen.")
        if self._csv_path.read_bytes() != self._checked_bytes:
            self._invalidate()
            raise ValueError(
                "Die CSV-Datei wurde seit der Vorschau geändert. Bitte zurückgehen und erneut prüfen."
            )
        if (
            replace(
                profile,
                name=self._checked_profile.name,
                import_source=self._checked_profile.import_source,
            )
            != self._checked_profile
        ):
            self._invalidate()
            raise ValueError(
                "Die Einstellungen wurden seit der Vorschau geändert. Bitte erneut prüfen."
            )

    def _confirm_id_mapping(self, profile):
        previous = (
            (self._original,)
            if self._original
            else tuple(
                p for p in self._profiles if p.import_source == profile.import_source
            )
        )
        if any(
            profile.columns.external_transaction_id != p.columns.external_transaction_id
            for p in previous
        ):
            answer = QMessageBox.warning(
                self,
                "Transaktions-ID-Zuordnung geändert",
                "Eine andere ID-Spalte kann für dieselben Umsätze andere Kennungen liefern. Bereits importierte Umsätze könnten dadurch erneut buchbar werden. Trotzdem fortfahren?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return answer == QMessageBox.StandardButton.Yes
        return True

    def _finish_import(self):
        # Nur die aktuelle Sitzung erhält die geprüfte Zuordnung; kein Store.save().
        profile = self._checked_profile
        self._validate_checked_import(profile)
        if not self._confirm_id_mapping(profile):
            return False
        self.profile = profile
        return True

    def _save_profile(self):
        profile = self._build_profile(final=True)
        self._validate_checked_import(profile)
        latest = self._store.load()
        if latest != self._profiles:
            raise CsvImportProfileError(
                "Profile wurden inzwischen geändert. Bitte den Assistenten erneut öffnen."
            )
        if not self._confirm_id_mapping(profile):
            return False
        if not self._original and profile.import_source not in {
            p.import_source for p in latest
        }:
            answer = QMessageBox.warning(
                self,
                "Neue Importquelle bestätigen",
                f"Die neue Kennung „{profile.import_source}“ hat eine eigene Duplikatprüfung. Für bereits importierte Daten derselben Quelle muss die bisherige Kennung verwendet werden. Neue Quelle ausdrücklich bestätigen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False
        updated = tuple(p for p in latest if p.profile_id != profile.profile_id) + (
            profile,
        )
        self._store.save(updated)
        self.profile = profile
        self.transactions = tuple(
            replace(t, import_source=profile.import_source) for t in self.transactions
        )
        return True

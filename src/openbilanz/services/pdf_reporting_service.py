"""PDF-Ausgabe für Buchhaltungsberichte."""

from collections.abc import Callable, Mapping, Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.money import ZERO
from openbilanz.reporting.account_activity_report import (
    AccountActivityReport,
)
from openbilanz.services.e_bilanz_preparation_service import (
    EBilanzPreparationResult,
)
from openbilanz.reporting.journal_report import JournalReport
from openbilanz.reporting.trial_balance_report import TrialBalanceReport


class PdfReportingService:
    """Exportiert vorhandene Buchhaltungsberichte als PDF."""

    def export_balance_sheet(
        self,
        *,
        balance_sheet: BalanceSheet,
        company_name: str,
        fiscal_year_name: str,
        target: Path,
    ) -> Path:
        """Exportiert eine Bilanz."""

        rows: list[list[str]] = [
            ["Position", "Aktiva", "Passiva"],
        ]

        self._append_balance_sheet_rows(
            rows=rows,
            position=balance_sheet.assets,
            balance_sheet=balance_sheet,
            side="assets",
        )
        self._append_balance_sheet_rows(
            rows=rows,
            position=balance_sheet.liabilities,
            balance_sheet=balance_sheet,
            side="liabilities",
        )

        rows.append(
            [
                "Summe",
                self._format_amount(
                    balance_sheet.amount_for(
                        balance_sheet.assets
                    )
                ),
                self._format_amount(
                    balance_sheet.amount_for(
                        balance_sheet.liabilities
                    )
                ),
            ]
        )

        return self._build_pdf(
            target=target,
            title="Bilanz nach § 266 HGB",
            company_name=company_name,
            period_text=(
                f"Geschäftsjahr: {fiscal_year_name}"
            ),
            rows=rows,
            column_widths=(
                110 * mm,
                35 * mm,
                35 * mm,
            ),
        )

    def export_income_statement(
        self,
        *,
        income_statement: IncomeStatement,
        net_income: Decimal,
        company_name: str,
        fiscal_year_name: str,
        target: Path,
    ) -> Path:
        """Exportiert eine Gewinn- und Verlustrechnung."""

        rows: list[list[str]] = [
            ["Position", "Betrag"],
        ]

        for position in (
            income_statement.income_statement.children
        ):
            self._append_statement_rows(
                rows=rows,
                position=position,
                amount_for=income_statement.amount_for,
            )

        if net_income > ZERO:
            result_name = "Jahresüberschuss"
        elif net_income < ZERO:
            result_name = "Jahresfehlbetrag"
        else:
            result_name = "Ergebnis"

        rows.append(
            [
                result_name,
                self._format_amount(net_income),
            ]
        )

        return self._build_pdf(
            target=target,
            title=(
                "Gewinn- und Verlustrechnung "
                "nach § 275 HGB"
            ),
            company_name=company_name,
            period_text=(
                f"Geschäftsjahr: {fiscal_year_name}"
            ),
            rows=rows,
            column_widths=(
                145 * mm,
                35 * mm,
            ),
        )

    def export_trial_balance(
        self,
        *,
        report: TrialBalanceReport,
        account_names: Mapping[str, str],
        company_name: str,
        target: Path,
    ) -> Path:
        """Exportiert eine Summen- und Saldenliste."""

        rows: list[list[str]] = [
            [
                "Konto",
                "Bezeichnung",
                "AB Soll",
                "AB Haben",
                "Umsatz Soll",
                "Umsatz Haben",
                "Saldo Soll",
                "Saldo Haben",
            ],
        ]

        for row in report.rows:
            rows.append(
                [
                    row.account_number,
                    account_names.get(
                        row.account_number,
                        "",
                    ),
                    self._format_amount(
                        row.opening_debit
                    ),
                    self._format_amount(
                        row.opening_credit
                    ),
                    self._format_amount(
                        row.debit_turnover
                    ),
                    self._format_amount(
                        row.credit_turnover
                    ),
                    self._format_amount(
                        row.closing_debit
                    ),
                    self._format_amount(
                        row.closing_credit
                    ),
                ]
            )

        rows.append(
            [
                "",
                "Summe",
                self._format_amount(
                    report.opening_debit_total
                ),
                self._format_amount(
                    report.opening_credit_total
                ),
                self._format_amount(
                    report.debit_turnover_total
                ),
                self._format_amount(
                    report.credit_turnover_total
                ),
                self._format_amount(
                    report.closing_debit_total
                ),
                self._format_amount(
                    report.closing_credit_total
                ),
            ]
        )

        return self._build_pdf(
            target=target,
            title="Summen- und Saldenliste",
            company_name=company_name,
            period_text=self._format_period(
                report.start_date,
                report.end_date,
            ),
            rows=rows,
            column_widths=(
                20 * mm,
                48 * mm,
                25 * mm,
                25 * mm,
                28 * mm,
                28 * mm,
                25 * mm,
                25 * mm,
            ),
            landscape_page=True,
        )

    def export_account_activity(
        self,
        *,
        reports: Sequence[AccountActivityReport],
        account_names: Mapping[str, str],
        company_name: str,
        start_date: date,
        end_date: date,
        target: Path,
    ) -> Path:
        """Exportiert eine Kontenauswertung."""

        rows: list[list[str]] = [
            [
                "Datum",
                "Beleg",
                "Konto",
                "Bezeichnung / Buchungstext",
                "Soll",
                "Haben",
                "Saldo",
            ],
        ]

        for report in reports:
            account_name = account_names.get(
                report.account_number,
                "",
            )

            for line in report.lines:
                description = line.description

                if account_name:
                    description = (
                        f"{account_name} – {description}"
                        if description
                        else account_name
                    )

                rows.append(
                    [
                        line.booking_date.strftime(
                            "%d.%m.%Y"
                        ),
                        line.voucher_no,
                        report.account_number,
                        description,
                        self._format_amount(
                            line.debit
                        ),
                        self._format_amount(
                            line.credit
                        ),
                        self._format_amount(
                            line.running_balance
                        ),
                    ]
                )

        return self._build_pdf(
            target=target,
            title="Kontenauswertung",
            company_name=company_name,
            period_text=self._format_period(
                start_date,
                end_date,
            ),
            rows=rows,
            column_widths=(
                24 * mm,
                24 * mm,
                20 * mm,
                90 * mm,
                28 * mm,
                28 * mm,
                30 * mm,
            ),
            landscape_page=True,
        )

    def export_e_bilanz(
        self,
        *,
        preparation: EBilanzPreparationResult,
        company_name: str,
        fiscal_year_name: str,
        target: Path,
    ) -> Path:
        """Exportiert die aufbereiteten E-Bilanz-Abschlusswerte als PDF."""

        target = Path(target)

        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")

        document = BaseDocTemplate(
            str(target),
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=(
                "E-Bilanz – Bilanz und "
                "Gewinn- und Verlustrechnung"
            ),
            author="SimpleOB",
        )

        frame = Frame(
            document.leftMargin,
            document.bottomMargin,
            document.width,
            document.height,
            id="e-bilanz",
        )

        document.addPageTemplates(
            [
                PageTemplate(
                    id="e-bilanz",
                    frames=(frame,),
                    onPage=self._draw_page_footer,
                )
            ]
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "EBilanzTitle",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            spaceAfter=6,
        )

        section_style = ParagraphStyle(
            "EBilanzSection",
            parent=styles["Heading2"],
            spaceBefore=8,
            spaceAfter=5,
        )

        story = [
            Paragraph(
                company_name,
                styles["Heading2"],
            ),
            Paragraph(
                (
                    "E-Bilanz – Bilanz und "
                    "Gewinn- und Verlustrechnung"
                ),
                title_style,
            ),
            Paragraph(
                "Taxonomie 6.9",
                title_style,
            ),
            Paragraph(
                f"Geschäftsjahr: {fiscal_year_name}",
                styles["Normal"],
            ),
            Paragraph(
                f"Erstellt am {date.today():%d.%m.%Y}",
                styles["Normal"],
            ),
            Spacer(
                1,
                8 * mm,
            ),
        ]

        balance_rows: list[list[str]] = [
            ["Position", "Aktiva", "Passiva"],
        ]

        self._append_balance_sheet_rows(
            rows=balance_rows,
            position=preparation.balance_sheet.assets,
            balance_sheet=preparation.balance_sheet,
            side="assets",
        )

        self._append_balance_sheet_rows(
            rows=balance_rows,
            position=preparation.balance_sheet.liabilities,
            balance_sheet=preparation.balance_sheet,
            side="liabilities",
        )

        balance_rows.append(
            [
                "Summe",
                self._format_amount(
                    preparation.balance_sheet.amount_for(
                        preparation.balance_sheet.assets
                    )
                ),
                self._format_amount(
                    preparation.balance_sheet.amount_for(
                        preparation.balance_sheet.liabilities
                    )
                ),
            ]
        )

        story.append(
            Paragraph(
                "Bilanz",
                section_style,
            )
        )

        balance_table = Table(
            balance_rows,
            colWidths=(
                110 * mm,
                35 * mm,
                35 * mm,
            ),
            repeatRows=1,
            hAlign="LEFT",
        )

        balance_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.lightgrey,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTNAME",
                        (0, -1),
                        (-1, -1),
                        "Helvetica-Bold",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.25,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "ALIGN",
                        (1, 1),
                        (-1, -1),
                        "RIGHT",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                ]
            )
        )

        story.append(balance_table)
        story.append(
            Spacer(
                1,
                8 * mm,
            )
        )

        income_rows: list[list[str]] = [
            ["Position", "Betrag"],
        ]

        for position in (
            preparation.income_statement
            .income_statement.children
        ):
            self._append_statement_rows(
                rows=income_rows,
                position=position,
                amount_for=(
                    preparation.income_statement.amount_for
                ),
            )

        income_result = preparation.net_income

        income_rows.append(
            [
                (
                    "Jahresüberschuss"
                    if income_result >= ZERO
                    else "Jahresfehlbetrag"
                ),
                self._format_amount(
                    abs(income_result)
                ),
            ]
        )

        story.append(
            Paragraph(
                "Gewinn- und Verlustrechnung",
                section_style,
            )
        )

        income_table = Table(
            income_rows,
            colWidths=(
                145 * mm,
                35 * mm,
            ),
            repeatRows=1,
            hAlign="LEFT",
        )

        income_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.lightgrey,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTNAME",
                        (0, -1),
                        (-1, -1),
                        "Helvetica-Bold",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.25,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "ALIGN",
                        (1, 1),
                        (-1, -1),
                        "RIGHT",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                ]
            )
        )

        story.append(income_table)

        document.build(story)

        return target

    def _build_pdf(
        self,
        *,
        target: Path,
        title: str,
        company_name: str,
        period_text: str,
        rows: list[list[str]],
        column_widths: tuple[float, ...],
        landscape_page: bool = False,
    ) -> Path:
        """Schreibt einen tabellarischen Bericht als PDF."""

        target = Path(target)

        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")

        page_size = (
            landscape(A4)
            if landscape_page
            else A4
        )

        document = BaseDocTemplate(
            str(target),
            pagesize=page_size,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=title,
            author="OpenBilanz",
        )

        frame = Frame(
            document.leftMargin,
            document.bottomMargin,
            document.width,
            document.height,
            id="report",
        )

        document.addPageTemplates(
            [
                PageTemplate(
                    id="report",
                    frames=(frame,),
                    onPage=self._draw_page_footer,
                )
            ]
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            spaceAfter=6,
        )

        story = [
            Paragraph(
                company_name,
                styles["Heading2"],
            ),
            Paragraph(
                title,
                title_style,
            ),
            Paragraph(
                period_text,
                styles["Normal"],
            ),
            Paragraph(
                f"Erstellt am {date.today():%d.%m.%Y}",
                styles["Normal"],
            ),
            Spacer(
                1,
                8 * mm,
            ),
        ]

        table = Table(
            rows,
            colWidths=column_widths,
            repeatRows=1,
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.lightgrey,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTNAME",
                        (0, -1),
                        (-1, -1),
                        "Helvetica-Bold",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.25,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "ALIGN",
                        (1, 1),
                        (-1, -1),
                        "RIGHT",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, 0),
                        5,
                    ),
                ]
            )
        )

        story.append(table)

        document.build(story)

        return target

    def _append_balance_sheet_rows(
        self,
        *,
        rows: list[list[str]],
        position: FinancialStatementPosition,
        balance_sheet: BalanceSheet,
        side: str,
        depth: int = 0,
    ) -> None:
        """Fügt belegte Bilanzpositionen rekursiv hinzu."""

        amount = balance_sheet.amount_for(
            position
        )

        if amount == ZERO:
            return

        label = (
            f"{'  ' * depth}"
            f"{position.name}"
        )

        if side == "assets":
            rows.append(
                [
                    label,
                    self._format_amount(amount),
                    "",
                ]
            )
        else:
            rows.append(
                [
                    label,
                    "",
                    self._format_amount(amount),
                ]
            )

        for child in position.children:
            self._append_balance_sheet_rows(
                rows=rows,
                position=child,
                balance_sheet=balance_sheet,
                side=side,
                depth=depth + 1,
            )

    def _append_statement_rows(
        self,
        *,
        rows: list[list[str]],
        position: FinancialStatementPosition,
        amount_for: Callable[
            [FinancialStatementPosition],
            Decimal,
        ],
        depth: int = 0,
    ) -> None:
        """Fügt belegte GuV-Positionen rekursiv hinzu."""

        amount = amount_for(position)

        if amount == ZERO:
            return

        rows.append(
            [
                (
                    f"{'  ' * depth}"
                    f"{position.name}"
                ),
                self._format_amount(amount),
            ]
        )

        for child in position.children:
            self._append_statement_rows(
                rows=rows,
                position=child,
                amount_for=amount_for,
                depth=depth + 1,
            )

    @staticmethod
    def _draw_page_footer(
        canvas: object,
        document: BaseDocTemplate,
    ) -> None:
        """Zeichnet die Seitennummer."""

        canvas.saveState()
        canvas.setFont(
            "Helvetica",
            8,
        )
        canvas.drawRightString(
            document.pagesize[0] - 15 * mm,
            10 * mm,
            f"Seite {document.page}",
        )
        canvas.restoreState()

    @staticmethod
    def _format_period(
        start_date: date,
        end_date: date,
    ) -> str:
        """Formatiert einen Berichtszeitraum."""

        return (
            f"Zeitraum: {start_date:%d.%m.%Y} – "
            f"{end_date:%d.%m.%Y}"
        )

    @staticmethod
    def _format_amount(
        amount: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag deutsch."""

        formatted = f"{amount:,.2f}"

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def export_journal(
        self,
        *,
        report: JournalReport,
        account_names: Mapping[str, str],
        company_name: str,
        target: Path,
    ) -> Path:
        """Exportiert ein Journal als PDF."""

        rows: list[list[str]] = [
            [
                "Nr.",
                "Datum",
                "Beleg",
                "Buchungstext",
                "Konto",
                "Bezeichnung",
                "S/H",
                "Betrag",
            ],
        ]

        for line in report.lines:
            rows.append(
                [
                    str(line.booking_number),
                    line.booking_date.strftime("%d.%m.%Y"),
                    line.voucher_no,
                    line.description,
                    line.account_number,
                    account_names.get(
                        line.account_number,
                        "",
                    ),
                    (
                        "S"
                        if line.side is EntrySide.DEBIT
                        else "H"
                    ),
                    self._format_amount(line.amount),
                ]
            )

        return self._build_pdf(
            target=target,
            title="Journal",
            company_name=company_name,
            period_text=self._format_period(
                report.start_date,
                report.end_date,
            ),
            rows=rows,
            column_widths=(
                12 * mm,
                24 * mm,
                24 * mm,
                60 * mm,
                20 * mm,
                60 * mm,
                15 * mm,
                30 * mm,
            ),
            landscape_page=True,
        )

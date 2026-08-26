
"""Fachliches GCD-Berichtsprofil für den unterstützten Standardfall."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GcdReportProfile:
    """Taxonomische Festlegungen für den UG-/GmbH-Standardfall."""

    report_status: str
    revision_status: str
    statement_type: str
    accounting_standard: str
    special_accounting_standard: str
    income_statement_format: str
    consolidation_range: str
    income_classification: str
    report_elements: tuple[str, ...]

    @classmethod
    def standard(cls) -> "GcdReportProfile":
        """Liefert das Standardprofil für UG/GmbH."""

        return cls(
            report_status=(
                "genInfo.report.id.reportStatus."
                "reportStatus.E"
            ),
            revision_status=(
                "genInfo.report.id.revisionStatus."
                "revisionStatus.E"
            ),
            statement_type=(
                "genInfo.report.id.statementType."
                "statementType.E"
            ),
            accounting_standard=(
                "genInfo.report.id.accountingStandard."
                "accountingStandard.HGBM"
            ),
            special_accounting_standard=(
                "genInfo.report.id.specialAccountingStandard.K"
            ),
            income_statement_format=(
                "genInfo.report.id.incomeStatementFormat."
                "incomeStatementFormat.GKV"
            ),
            consolidation_range=(
                "genInfo.report.id.consolidationRange."
                "consolidationRange.EA"
            ),
            income_classification=(
                "genInfo.company.id.incomeClassification.trade"
            ),
            report_elements=(
                "genInfo.report.id.reportElement.reportElements.B",
                "genInfo.report.id.reportElement.reportElements.GuV",
                "genInfo.report.id.reportElement.reportElements.BAL",
            ),
        )

    def legal_status_for(
        self,
        legal_form: str,
    ) -> str:
        """Liefert das GCD-Concept für die unterstützte Rechtsform."""

        if legal_form == "UG (haftungsbeschränkt)":
            return (
                "genInfo.company.id.legalStatus."
                "legalStatus.UG"
            )

        if legal_form == "GmbH":
            return (
                "genInfo.company.id.legalStatus."
                "legalStatus.GMBH"
            )

        raise ValueError(
            "unsupported legal form: "
            f"{legal_form}"
        )

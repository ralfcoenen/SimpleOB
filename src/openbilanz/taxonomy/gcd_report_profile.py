
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
            ),
        )

    def with_report_element(
        self,
        concept_name: str,
    ) -> "GcdReportProfile":
        """Liefert das Profil mit einem zusätzlichen Report-Element."""

        if not isinstance(concept_name, str):
            raise TypeError(
                "concept_name must be a string"
            )

        if not concept_name.strip():
            raise ValueError(
                "concept_name must not be empty"
            )

        if concept_name in self.report_elements:
            return self

        return GcdReportProfile(
            report_status=self.report_status,
            revision_status=self.revision_status,
            statement_type=self.statement_type,
            accounting_standard=self.accounting_standard,
            special_accounting_standard=(
                self.special_accounting_standard
            ),
            income_statement_format=(
                self.income_statement_format
            ),
            consolidation_range=self.consolidation_range,
            income_classification=self.income_classification,
            report_elements=(
                self.report_elements
                + (concept_name,)
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

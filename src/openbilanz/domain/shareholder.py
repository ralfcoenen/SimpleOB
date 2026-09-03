"""Gesellschafter eines Unternehmens."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from openbilanz.domain.tax_number_normalizer import (
    TaxNumberNormalizer,
)


@dataclass(frozen=True, slots=True)
class Shareholder:
    """Ein Gesellschafter eines Unternehmens."""

    company_id: UUID
    shareholder_number: str
    name: str
    first_name: str = ""
    legal_status: str = ""
    share_numerator: str = ""
    share_denominator: str = ""
    tax_number: str = ""
    tax_number_federal_state: str = ""
    tax_id: str = ""
    wid: str = ""
    shareholder_id: UUID = field(
        default_factory=uuid4
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.company_id,
            UUID,
        ):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(
            self.shareholder_id,
            UUID,
        ):
            raise TypeError(
                "shareholder_id must be a UUID"
            )

        shareholder_number = self._normalize_required_text(
            self.shareholder_number,
            field_name="shareholder_number",
        )

        name = self._normalize_required_text(
            self.name,
            field_name="name",
        )

        first_name = self._normalize_optional_text(
            self.first_name,
            field_name="first_name",
        )

        legal_status = self._normalize_required_text(
            self.legal_status,
            field_name="legal_status",
        )

        share_numerator = self._normalize_required_text(
            self.share_numerator,
            field_name="share_numerator",
        )

        share_denominator = self._normalize_required_text(
            self.share_denominator,
            field_name="share_denominator",
        )

        tax_number = self._normalize_optional_text(
            self.tax_number,
            field_name="tax_number",
        )

        tax_number_federal_state = (
            self._normalize_optional_text(
                self.tax_number_federal_state,
                field_name="tax_number_federal_state",
            ).upper()
        )

        tax_id = self._normalize_optional_text(
            self.tax_id,
            field_name="tax_id",
        )

        wid = self._normalize_optional_text(
            self.wid,
            field_name="wid",
        )

        if not share_numerator.isdigit():
            raise ValueError(
                "share_numerator must contain digits only"
            )

        if not share_denominator.isdigit():
            raise ValueError(
                "share_denominator must contain digits only"
            )

        if int(share_denominator) <= 0:
            raise ValueError(
                "share_denominator must be greater than zero"
            )

        tax_number = self._normalize_tax_number(
            tax_number=tax_number,
            federal_state=tax_number_federal_state,
        )

        object.__setattr__(
            self,
            "shareholder_number",
            shareholder_number,
        )
        object.__setattr__(
            self,
            "name",
            name,
        )
        object.__setattr__(
            self,
            "first_name",
            first_name,
        )
        object.__setattr__(
            self,
            "legal_status",
            legal_status,
        )
        object.__setattr__(
            self,
            "share_numerator",
            share_numerator,
        )
        object.__setattr__(
            self,
            "share_denominator",
            share_denominator,
        )
        object.__setattr__(
            self,
            "tax_number",
            tax_number,
        )
        object.__setattr__(
            self,
            "tax_number_federal_state",
            tax_number_federal_state,
        )
        object.__setattr__(
            self,
            "tax_id",
            tax_id,
        )
        object.__setattr__(
            self,
            "wid",
            wid,
        )

    @staticmethod
    def _normalize_required_text(
        value: str,
        *,
        field_name: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be blank"
            )

        return normalized

    @staticmethod
    def _normalize_optional_text(
        value: str,
        *,
        field_name: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string"
            )

        return value.strip()

    @staticmethod
    def _normalize_tax_number(
        *,
        tax_number: str,
        federal_state: str,
    ) -> str:
        if not tax_number:
            return ""

        if (
            len(tax_number) == 13
            and tax_number.isdigit()
        ):
            return tax_number

        if not federal_state:
            raise ValueError(
                "tax_number must contain exactly 13 digits"
            )

        return TaxNumberNormalizer().normalize(
            federal_state=federal_state,
            tax_number=tax_number,
        )

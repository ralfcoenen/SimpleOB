"""GCD-Gesellschafterdaten."""

from dataclasses import dataclass
from enum import Enum


class GcdShareholderLegalStatus(Enum):
    """Rechtsstellung eines Gesellschafters."""

    NATURAL_PERSON = "NPP"
    LEGAL_ENTITY = "NPB"
    PARTNERSHIP = "PG"
    PUBLIC_LAW_ENTITY = "KOER"


class GcdShareholderGroup(Enum):
    """Gesellschaftergruppe."""

    FULLY_LIABLE = "genPartnerFullyLiable"
    OTHER = "genPartnerOther"
    INDIRECT = "indirectPartner"
    LIMITED = "limPartner"


@dataclass(frozen=True, slots=True)
class GcdShareDivideKey:
    """Beteiligungsquote als Zähler und Nenner."""

    numerator: str
    denominator: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.numerator,
            str,
        ):
            raise TypeError(
                "numerator must be a string"
            )

        if (
            not self.numerator.isdigit()
            or not 1 <= len(self.numerator) <= 16
        ):
            raise ValueError(
                "numerator must contain 1 to 16 digits"
            )

        if not isinstance(
            self.denominator,
            str,
        ):
            raise TypeError(
                "denominator must be a string"
            )

        if (
            not self.denominator.isdigit()
            or not 1 <= len(self.denominator) <= 16
            or self.denominator.startswith("0")
        ):
            raise ValueError(
                "denominator must contain 1 to 16 digits "
                "and must not start with zero"
            )


@dataclass(frozen=True, slots=True)
class GcdShareholder:
    """Daten eines GCD-Gesellschafters."""

    name: str
    shareholder_id: str
    tax_number: str | None
    tax_id: str | None
    wid: str | None
    legal_status: GcdShareholderLegalStatus
    share_divide_key: GcdShareDivideKey
    first_name: str | None = None
    group: GcdShareholderGroup | None = None
    current_number: int | None = None
    signer_id: str | None = None
    economic_id: str | None = None
    special_balance_required: bool | None = None
    extension_required: bool | None = None
    id_not_assigned: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not self.name.strip():
            raise ValueError(
                "name must not be blank"
            )

        if not isinstance(
            self.shareholder_id,
            str,
        ):
            raise TypeError(
                "shareholder_id must be a string"
            )

        if not self.shareholder_id.strip():
            raise ValueError(
                "shareholder_id must not be blank"
            )

        if self.tax_number is not None:
            if not isinstance(
                self.tax_number,
                str,
            ):
                raise TypeError(
                    "tax_number must be a string or None"
                )

            if (
                len(self.tax_number) != 13
                or not self.tax_number.isdigit()
            ):
                raise ValueError(
                    "tax_number must contain exactly 13 digits"
                )

        if self.tax_id is not None:
            if not isinstance(
                self.tax_id,
                str,
            ):
                raise TypeError(
                    "tax_id must be a string or None"
                )

            if not self.tax_id.strip():
                raise ValueError(
                    "tax_id must not be blank"
                )

        if self.wid is not None:
            if not isinstance(
                self.wid,
                str,
            ):
                raise TypeError(
                    "wid must be a string or None"
                )

            if not self.wid.strip():
                raise ValueError(
                    "wid must not be blank"
                )

        if not isinstance(
            self.legal_status,
            GcdShareholderLegalStatus,
        ):
            raise TypeError(
                "legal_status must be a GcdShareholderLegalStatus"
            )

        if not isinstance(
            self.share_divide_key,
            GcdShareDivideKey,
        ):
            raise TypeError(
                "share_divide_key must be a GcdShareDivideKey"
            )

        if (
            self.group is not None
            and not isinstance(
                self.group,
                GcdShareholderGroup,
            )
        ):
            raise TypeError(
                "group must be a GcdShareholderGroup or None"
            )

        if self.current_number is not None:
            if (
                not isinstance(
                    self.current_number,
                    int,
                )
                or isinstance(
                    self.current_number,
                    bool,
                )
            ):
                raise TypeError(
                    "current_number must be an integer or None"
                )

            if self.current_number <= 0:
                raise ValueError(
                    "current_number must be positive"
                )

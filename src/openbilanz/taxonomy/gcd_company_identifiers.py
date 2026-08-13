"""Unternehmenskennungen für die GCD-Taxonomie."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GcdCompanyIdentifiers:
    """Enthält steuerliche Unternehmenskennungen."""

    tax_number_13: str
    tax_id: str | None = None
    tax_economic_id: str | None = None
    bf4: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.tax_number_13,
            str,
        ):
            raise TypeError(
                "tax_number_13 must be a string"
            )

        if (
            len(self.tax_number_13) != 13
            or not self.tax_number_13.isdigit()
        ):
            raise ValueError(
                "tax_number_13 must contain exactly 13 digits"
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

        if self.tax_economic_id is not None:
            if not isinstance(
                self.tax_economic_id,
                str,
            ):
                raise TypeError(
                    "tax_economic_id must be a string or None"
                )

            if not self.tax_economic_id.strip():
                raise ValueError(
                    "tax_economic_id must not be blank"
                )

        if self.bf4 is not None:
            if not isinstance(
                self.bf4,
                str,
            ):
                raise TypeError(
                    "bf4 must be a string or None"
                )

            if (
                len(self.bf4) != 4
                or not self.bf4.isdigit()
            ):
                raise ValueError(
                    "bf4 must contain exactly 4 digits"
                )

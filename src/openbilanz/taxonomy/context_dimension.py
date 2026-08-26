"""Explizite Dimension eines XBRL-Kontexts."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaxonomyContextDimension:
    """Verknüpft eine XBRL-Dimension mit ihrem Mitglied."""

    dimension: str
    member: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("dimension", self.dimension),
            ("member", self.member),
        ):
            if not isinstance(value, str):
                raise TypeError(
                    f"{field_name} must be a str"
                )

            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be blank"
                )

            if value != value.strip():
                raise ValueError(
                    f"{field_name} must not contain "
                    "surrounding whitespace"
                )

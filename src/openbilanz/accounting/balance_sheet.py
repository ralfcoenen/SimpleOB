from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BalancePosition:
    code: str
    name: str
    amount: Decimal | None = None
    children: tuple["BalancePosition", ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.children and self.amount is not None:
            raise ValueError(
                "A balance position with children must not have its own amount."
            )

        if not self.children and self.amount is None:
            raise ValueError(
                "A balance position without children must have an amount."
            )

    def total(self) -> Decimal:
        if self.children:
            return sum(
                (child.total() for child in self.children),
                start=Decimal("0.00"),
            )

        if self.amount is None:
            raise RuntimeError(
                "A leaf balance position must have an amount."
            )

        return self.amount


@dataclass(frozen=True, slots=True)
class BalanceSection:
    name: str
    positions: tuple[BalancePosition, ...] = field(default_factory=tuple)

    def total(self) -> Decimal:
        return sum(
            (position.total() for position in self.positions),
            start=Decimal("0.00"),
        )

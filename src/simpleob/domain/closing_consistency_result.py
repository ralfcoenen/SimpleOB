"""Ergebnis der Konsistenzprüfung eines Jahresabschlusses."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ClosingConsistencyResult:
    """Enthält das Ergebnis einer Abschlusskonsistenzprüfung."""

    errors: tuple[str, ...] = field(
        default_factory=tuple
    )

    @property
    def is_consistent(self) -> bool:
        """Prüft, ob keine Konsistenzfehler vorliegen."""

        return not self.errors


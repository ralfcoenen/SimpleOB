"""Übertragung fachlicher Buchungen in das Hauptbuch."""

from collections.abc import Iterator
from decimal import Decimal

from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.booking import Booking
from openbilanz.domain.journal import Journal

PostingPair = tuple[str, str, Decimal]


class PostingService:
    """
    Überträgt vollständige Buchungssätze in ein Ledger.

    Der Service ist zustandslos. Eine Buchung wird in elementare
    Soll-an-Haben-Buchungen zerlegt und anschließend über Ledger.post()
    verbucht.
    """

    def post_booking(
        self,
        *,
        booking: Booking,
        ledger: Ledger,
        journal: Journal | None = None,
    ) -> None:
        """
        Überträgt eine vollständige Buchung in das Hauptbuch.

        Splittbuchungen werden in mehrere elementare
        Soll-an-Haben-Buchungen zerlegt.

        Args:
            booking:
                Die zu übertragende Buchung.
            ledger:
                Das zu bebuchende Hauptbuch.

        Raises:
            TypeError:
                Wenn booking keine Booking oder ledger kein Ledger ist.
        """
        if not isinstance(booking, Booking):
            raise TypeError("booking muss eine Booking sein.")

        if not isinstance(ledger, Ledger):
            raise TypeError("ledger muss ein Ledger sein.")
        
        if journal is not None and not isinstance(journal, Journal):
            raise TypeError("journal muss ein Journal sein.")
        
        if journal is not None:
            journal.add(booking)

        for debit_account, credit_account, amount in self._pair_lines(booking):
            ledger.post(
                debit_account=debit_account,
                credit_account=credit_account,
                amount=amount,
            )

    @staticmethod
    def _pair_lines(
        booking: Booking,
    ) -> Iterator[PostingPair]:
        """
        Zerlegt eine Buchung in elementare Soll-an-Haben-Paare.

        Die ursprünglichen BookingLine-Objekte werden nicht verändert.
        Für die Verarbeitung werden ausschließlich lokale Restbeträge
        verwendet.

        Args:
            booking:
                Die zu zerlegende Buchung.

        Yields:
            Tupel aus Sollkonto, Habenkonto und Buchungsbetrag.
        """
        debit_lines = [[line.account_number, line.amount] for line in booking.debit_lines]
        credit_lines = [[line.account_number, line.amount] for line in booking.credit_lines]

        debit_index = 0
        credit_index = 0

        while debit_index < len(debit_lines) and credit_index < len(credit_lines):
            debit_account = debit_lines[debit_index][0]
            debit_remaining = debit_lines[debit_index][1]

            credit_account = credit_lines[credit_index][0]
            credit_remaining = credit_lines[credit_index][1]

            amount = min(debit_remaining, credit_remaining)

            yield debit_account, credit_account, amount

            debit_remaining -= amount
            credit_remaining -= amount

            debit_lines[debit_index][1] = debit_remaining
            credit_lines[credit_index][1] = credit_remaining

            if debit_remaining == Decimal("0.00"):
                debit_index += 1

            if credit_remaining == Decimal("0.00"):
                credit_index += 1

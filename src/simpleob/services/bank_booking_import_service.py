"""Atomare Übernahme bestätigter Bankbuchungsvorschläge."""

from sqlalchemy.exc import IntegrityError

from simpleob.database.bank_transaction_booking_repository import (
    BankTransactionBookingRepository,
)
from simpleob.database.booking_repository import BookingRepository
from simpleob.domain.bank_booking_proposal import BankBookingProposal
from simpleob.domain.booking import Booking
from simpleob.domain.company import Company
from simpleob.domain.errors import DuplicateBankTransactionError
from simpleob.domain.fiscal_year import FiscalYear


class BankBookingImportService:
    """Speichert Buchung und externe Transaktionszuordnung gemeinsam."""

    def __init__(
        self,
        *,
        booking_repository: BookingRepository,
        transaction_booking_repository: BankTransactionBookingRepository,
    ) -> None:
        self._booking_repository = booking_repository
        self._transaction_booking_repository = transaction_booking_repository

    def confirm_and_post(
        self,
        proposal: BankBookingProposal,
        *,
        company: Company,
        fiscal_year: FiscalYear,
        bank_account_numbers: frozenset[str],
        confirmed: bool,
    ) -> Booking:
        """Validiert und übernimmt einen ausdrücklich bestätigten Vorschlag."""
        if confirmed is not True:
            raise ValueError("Die Buchungsübernahme wurde nicht ausdrücklich bestätigt.")
        if not isinstance(proposal, BankBookingProposal):
            raise TypeError("proposal muss eine BankBookingProposal sein.")
        if not isinstance(company, Company):
            raise TypeError("company muss eine Company sein.")
        if not isinstance(fiscal_year, FiscalYear):
            raise TypeError("fiscal_year muss ein FiscalYear sein.")
        if not isinstance(bank_account_numbers, frozenset):
            raise TypeError("bank_account_numbers muss eine frozenset sein.")

        validation_errors = proposal.validation_errors
        if validation_errors:
            raise ValueError(
                "Buchungsvorschlag ist ungültig: "
                + " ".join(validation_errors)
            )
        if proposal.bank_account_number not in bank_account_numbers:
            raise ValueError(
                "Das ausgewählte Bankkonto ist für den Mandanten nicht als Bankkonto konfiguriert."
            )

        transaction = proposal.transaction

        try:
            booking = proposal.to_booking()
            existing_booking_id = self._transaction_booking_repository.booking_id_for(
                company_id=company.company_id,
                import_source=transaction.import_source,
                external_transaction_id=transaction.external_transaction_id,
            )
            if existing_booking_id is not None:
                raise DuplicateBankTransactionError(
                    "Diese Banktransaktion wurde bereits übernommen "
                    f"(Buchung {existing_booking_id})."
                )

            # Beide Repositories teilen dieselbe Session. Erst der gemeinsame
            # Commit macht Buchung und Importreferenz dauerhaft sichtbar.
            self._booking_repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
                validate_accounts=True,
                required_bank_account_number=proposal.bank_account_number,
            )
            self._transaction_booking_repository.add(
                company_id=company.company_id,
                import_source=transaction.import_source,
                external_transaction_id=transaction.external_transaction_id,
                booking_id=booking.booking_id,
                commit=False,
            )
            self._booking_repository.commit()
        except IntegrityError as exc:
            self._booking_repository.rollback()
            existing_booking_id = self._transaction_booking_repository.booking_id_for(
                company_id=company.company_id,
                import_source=transaction.import_source,
                external_transaction_id=transaction.external_transaction_id,
            )
            if existing_booking_id is not None:
                raise DuplicateBankTransactionError(
                    "Diese Banktransaktion wurde parallel bereits übernommen "
                    f"(Buchung {existing_booking_id})."
                ) from exc
            raise
        except Exception:
            self._booking_repository.rollback()
            raise

        return booking

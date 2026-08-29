"""Zeitliche Zuordnung von USt-Details zur USt-Voranmeldung."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.vat_booking_detail_repository import (
    VatBookingDetailRepository,
)
from openbilanz.database.vat_input_timing_repository import (
    VatInputTimingRepository,
)
from openbilanz.database.vat_revenue_repository import VatRevenueRepository
from openbilanz.domain.money import ZERO
from openbilanz.domain.vat_booking_detail import VatBookingDetail
from openbilanz.domain.vat_booking_direction import VatBookingDirection
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue import VatRevenue
from openbilanz.domain.vat_taxation_method import VatTaxationMethod

_CENT = Decimal("0.01")


class VatAdvanceReturnTimingService:
    """Ermittelt die im Voranmeldungszeitraum relevanten USt-Details."""

    def __init__(
        self,
        *,
        booking_repository: BookingRepository,
        vat_booking_detail_repository: VatBookingDetailRepository,
        vat_revenue_repository: VatRevenueRepository,
        vat_input_timing_repository: VatInputTimingRepository,
    ) -> None:
        self._booking_repository = booking_repository
        self._vat_booking_detail_repository = (
            vat_booking_detail_repository
        )
        self._vat_revenue_repository = (
            vat_revenue_repository
        )
        self._vat_input_timing_repository = (
            vat_input_timing_repository
        )

    def details_for_period(
        self,
        *,
        company_id,
        taxation_method: VatTaxationMethod,
        start_date: date,
        end_date: date,
    ) -> tuple[VatBookingDetail, ...]:
        """Liefert die für den USt-VA-Zeitraum relevanten Details."""

        if not isinstance(
            taxation_method,
            VatTaxationMethod,
        ):
            raise TypeError(
                "taxation_method must be a VatTaxationMethod"
            )

        if not isinstance(start_date, date):
            raise TypeError(
                "start_date must be a date"
            )

        if not isinstance(end_date, date):
            raise TypeError(
                "end_date must be a date"
            )

        if end_date < start_date:
            raise ValueError(
                "end_date must not be before start_date"
            )

        input_details = self._input_details_for_period(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
        )

        if taxation_method is VatTaxationMethod.AGREED:
            output_details = (
                self._agreed_output_details_for_period(
                    company_id=company_id,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        else:
            output_details = (
                self._received_output_details_for_period(
                    company_id=company_id,
                    start_date=start_date,
                    end_date=end_date,
                )
            )

        return output_details + input_details

    def _input_details_for_period(
        self,
        *,
        company_id,
        start_date: date,
        end_date: date,
    ) -> tuple[VatBookingDetail, ...]:
        """Ordnet Vorsteuer nach Leistungs- und Rechnungseingangsdatum zu."""

        timings = (
            self._vat_input_timing_repository
            .list_for_company_in_date_range(
                company_id=company_id,
                start_date=start_date,
                end_date=end_date,
            )
        )

        return tuple(
            detail
            for timing in timings
            for detail in (
                self._vat_booking_detail_repository
                .list_for_booking(
                    timing.booking_id
                )
            )
            if detail.direction is VatBookingDirection.INPUT
        )


    def _agreed_output_details_for_period(
        self,
        *,
        company_id,
        start_date: date,
        end_date: date,
    ) -> tuple[VatBookingDetail, ...]:
        """Ordnet Ausgangsumsätze nach Leistungsdatum zu."""

        revenues = (
            self._vat_revenue_repository
            .list_revenues_for_company_in_date_range(
                company_id=company_id,
                start_date=start_date,
                end_date=end_date,
            )
        )

        return tuple(
            detail
            for revenue in revenues
            for detail in (
                self._vat_booking_detail_repository
                .list_for_booking(
                    revenue.booking_id
                )
            )
            if detail.direction is VatBookingDirection.OUTPUT
        )

    def _received_output_details_for_period(
        self,
        *,
        company_id,
        start_date: date,
        end_date: date,
    ) -> tuple[VatBookingDetail, ...]:
        """Ordnet Ausgangsumsätze nach Zahlungseingang zu."""

        revenues = (
            self._vat_revenue_repository
            .list_revenues_for_company(
                company_id=company_id
            )
        )

        result: list[VatBookingDetail] = []

        for revenue in revenues:
            output_details = tuple(
                detail
                for detail in (
                    self._vat_booking_detail_repository
                    .list_for_booking(
                        revenue.booking_id
                    )
                )
                if (
                    detail.direction
                    is VatBookingDirection.OUTPUT
                )
            )

            if not output_details:
                continue

            if (
                revenue.payment_kind
                is VatPaymentKind.IMMEDIATE
            ):
                booking = self._booking_repository.get(
                    revenue.booking_id
                )

                if booking is None:
                    raise RuntimeError(
                        "Die Umsatzbuchung ist nicht vorhanden."
                    )

                if (
                    start_date
                    <= booking.booking_date
                    <= end_date
                ):
                    result.extend(output_details)

                continue

            result.extend(
                self._received_receivable_details_for_period(
                    revenue=revenue,
                    output_details=output_details,
                    start_date=start_date,
                    end_date=end_date,
                )
            )

        return tuple(result)

    def _received_receivable_details_for_period(
        self,
        *,
        revenue: VatRevenue,
        output_details: tuple[
            VatBookingDetail,
            ...,
        ],
        start_date: date,
        end_date: date,
    ) -> tuple[VatBookingDetail, ...]:
        """Verteilt Teilzahlungen proportional auf die USt-Details."""

        allocations = (
            self._vat_revenue_repository
            .list_allocations_for_revenue(
                revenue.revenue_id
            )
        )

        dated_allocations = []

        for allocation in allocations:
            payment_booking = (
                self._booking_repository.get(
                    allocation.payment_booking_id
                )
            )

            if payment_booking is None:
                raise RuntimeError(
                    "Die Zahlungsbuchung ist nicht vorhanden."
                )

            dated_allocations.append(
                (
                    payment_booking.booking_date,
                    allocation,
                )
            )

        dated_allocations.sort(
            key=lambda item: (
                item[0],
                str(item[1].allocation_id),
            )
        )

        cumulative_gross = ZERO

        previous_allocated: dict[
            tuple[str, int],
            tuple[Decimal, Decimal],
        ] = {
            (
                str(detail.booking_id),
                index,
            ): (
                ZERO,
                ZERO,
            )
            for index, detail
            in enumerate(output_details)
        }

        result: list[VatBookingDetail] = []

        for payment_date, allocation in dated_allocations:
            cumulative_gross += allocation.amount

            if cumulative_gross > revenue.gross_amount:
                raise ValueError(
                    "Die Zahlungszuordnungen überschreiten "
                    "den Ausgangsumsatz."
                )

            ratio = (
                cumulative_gross
                / revenue.gross_amount
            )

            for index, detail in enumerate(
                output_details
            ):
                key = (
                    str(detail.booking_id),
                    index,
                )

                previous_net, previous_tax = (
                    previous_allocated[key]
                )

                cumulative_net = self._round_money(
                    detail.net_amount * ratio
                )
                cumulative_tax = self._round_money(
                    detail.tax_amount * ratio
                )

                allocated_net = (
                    cumulative_net
                    - previous_net
                )
                allocated_tax = (
                    cumulative_tax
                    - previous_tax
                )

                previous_allocated[key] = (
                    cumulative_net,
                    cumulative_tax,
                )

                if not (
                    start_date
                    <= payment_date
                    <= end_date
                ):
                    continue

                if (
                    allocated_net == ZERO
                    and allocated_tax == ZERO
                ):
                    continue

                result.append(
                    VatBookingDetail(
                        booking_id=detail.booking_id,
                        account_number=(
                            detail.account_number
                        ),
                        net_amount=allocated_net,
                        tax_amount=allocated_tax,
                        tax_rate=detail.tax_rate,
                        direction=(
                            VatBookingDirection.OUTPUT
                        ),
                    )
                )

        return tuple(result)

    @staticmethod
    def _round_money(
        amount: Decimal,
    ) -> Decimal:
        """Rundet einen Geldbetrag kaufmännisch auf Cent."""

        return amount.quantize(
            _CENT,
            rounding=ROUND_HALF_UP,
        )

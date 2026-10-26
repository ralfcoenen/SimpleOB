"""Persistenz für mandantenbezogene Geschäftspartner."""

from uuid import UUID

from sqlalchemy.orm import Session

from simpleob.database.models import Geschaeftspartner, Mandant
from simpleob.domain.business_partner import BusinessPartner


class BusinessPartnerRepository:
    """Lädt und speichert Geschäftspartner innerhalb eines Mandanten."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        partner: BusinessPartner,
        *,
        commit: bool = True,
    ) -> None:
        if not isinstance(partner, BusinessPartner):
            raise TypeError("partner must be a BusinessPartner")

        company = self._find_company(partner.company_id)
        if company is None:
            raise ValueError("Das Unternehmen ist nicht vorhanden.")

        existing = (
            self._session.query(Geschaeftspartner)
            .filter(
                Geschaeftspartner.mandant_id == company.id,
                Geschaeftspartner.partner_id == str(partner.partner_id),
            )
            .one_or_none()
        )
        if existing is not None:
            raise ValueError("Der Geschäftspartner ist bereits vorhanden.")

        self._session.add(
            Geschaeftspartner(
                partner_id=str(partner.partner_id),
                mandant_id=company.id,
                name=partner.name,
                is_customer=partner.is_customer,
                is_supplier=partner.is_supplier,
                is_active=partner.is_active,
            )
        )
        if commit:
            self._session.commit()

    def get(
        self,
        *,
        company_id: UUID,
        partner_id: UUID,
    ) -> BusinessPartner | None:
        company = self._find_company(company_id)
        if company is None:
            return None
        model = (
            self._session.query(Geschaeftspartner)
            .filter(
                Geschaeftspartner.mandant_id == company.id,
                Geschaeftspartner.partner_id == str(partner_id),
            )
            .one_or_none()
        )
        return self._to_domain(company_id, model) if model else None

    def list_for_company(
        self,
        company_id: UUID,
        *,
        customers_only: bool = False,
        suppliers_only: bool = False,
        active_only: bool = True,
    ) -> tuple[BusinessPartner, ...]:
        company = self._find_company(company_id)
        if company is None:
            return ()
        query = self._session.query(Geschaeftspartner).filter(
            Geschaeftspartner.mandant_id == company.id
        )
        if customers_only:
            query = query.filter(Geschaeftspartner.is_customer.is_(True))
        if suppliers_only:
            query = query.filter(Geschaeftspartner.is_supplier.is_(True))
        if active_only:
            query = query.filter(Geschaeftspartner.is_active.is_(True))
        return tuple(
            self._to_domain(company_id, model)
            for model in query.order_by(Geschaeftspartner.name).all()
        )

    def _find_company(self, company_id: UUID) -> Mandant | None:
        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")
        return (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )

    @staticmethod
    def _to_domain(
        company_id: UUID,
        model: Geschaeftspartner,
    ) -> BusinessPartner:
        return BusinessPartner(
            company_id=company_id,
            partner_id=UUID(model.partner_id),
            name=model.name,
            is_customer=model.is_customer,
            is_supplier=model.is_supplier,
            is_active=model.is_active,
        )

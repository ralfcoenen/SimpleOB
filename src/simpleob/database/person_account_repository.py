"""Atomare Verwaltung mandantenspezifischer Personenkonten."""

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.models import (
    Geschaeftspartner,
    Konto,
    Mandant,
    PersonenkontoZuordnung,
)
from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.person_account import PersonAccount
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount


class PersonAccountRepository:
    """Speichert Konto, Geschäftspartner und Rollenverknüpfung gemeinsam."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._partners = BusinessPartnerRepository(session)
        self._accounts = ChartOfAccountsRepository(session)

    @staticmethod
    def validate_account_number(number: str, role: PersonAccountRole) -> str:
        if not isinstance(role, PersonAccountRole):
            raise TypeError("role must be a PersonAccountRole")
        if not isinstance(number, str) or len(number) != 5 or not number.isascii() or not number.isdecimal():
            raise ValueError("Die Kontonummer muss aus genau fünf Ziffern bestehen.")
        lower, upper = role.number_range
        if not lower <= int(number) <= upper:
            label = "Debitor" if role is PersonAccountRole.DEBITOR else "Kreditor"
            raise ValueError(f"Die Kontonummer liegt außerhalb des Nummernkreises für {label}.")
        return number

    def suggest_account_number(
        self, *, company_id: UUID, role: PersonAccountRole
    ) -> str:
        lower, upper = role.number_range
        company = self._company(company_id)
        occupied = {
            row[0]
            for row in self._session.query(Konto.account_number)
            .filter(Konto.mandant_id == company.id)
            .all()
        }
        for candidate in range(lower, upper + 1):
            number = str(candidate)
            if number not in occupied:
                return number
        raise ValueError("Der Nummernkreis ist vollständig belegt.")

    def available_partners(
        self, *, company_id: UUID, role: PersonAccountRole
    ) -> tuple[BusinessPartner, ...]:
        company = self._company(company_id)
        used_ids = {
            row[0]
            for row in self._session.query(PersonenkontoZuordnung.partner_id)
            .filter(
                PersonenkontoZuordnung.mandant_id == company.id,
                PersonenkontoZuordnung.role == role.value,
            )
            .all()
        }
        return tuple(
            partner
            for partner in self._partners.list_for_company(company_id)
            if str(partner.partner_id) not in used_ids
            and (
                partner.is_customer
                if role is PersonAccountRole.DEBITOR
                else partner.is_supplier
            )
        )

    def partners_for_company(self, *, company_id: UUID) -> tuple[BusinessPartner, ...]:
        """Liefert alle aktiven Partner als Kandidaten für eine Kontoergänzung."""
        return self._partners.list_for_company(company_id)

    def accounts_for_partner(
        self, *, company_id: UUID, partner_id: UUID
    ) -> tuple[PersonAccount, ...]:
        """Lädt die bestehenden Personenkonten eines Geschäftspartners."""
        company = self._company(company_id)
        account_numbers = tuple(
            row[0]
            for row in self._session.query(PersonenkontoZuordnung.account_number)
            .filter(
                PersonenkontoZuordnung.mandant_id == company.id,
                PersonenkontoZuordnung.partner_id == str(partner_id),
            )
            .order_by(PersonenkontoZuordnung.role)
            .all()
        )
        return tuple(
            person_account
            for number in account_numbers
            if (
                person_account := self.get(
                    company_id=company_id, account_number=number
                )
            )
            is not None
        )

    def create(
        self,
        *,
        company_id: UUID,
        role: PersonAccountRole,
        name: str,
        account_number: str | None = None,
        partner_id: UUID | None = None,
    ) -> PersonAccount:
        """Legt ein Personenkonto an, ohne einem Partner eine Rolle hinzuzufügen."""
        created = self._create_accounts(
            company_id=company_id,
            account_numbers={role: account_number},
            name=name,
            partner_id=partner_id,
            allow_role_additions=False,
        )
        return created[0]

    def create_many(
        self,
        *,
        company_id: UUID,
        account_numbers: Mapping[PersonAccountRole, str | None],
        name: str,
        partner_id: UUID | None = None,
    ) -> tuple[PersonAccount, ...]:
        """Legt ein oder zwei Rollen eines Partners in einer Transaktion an.

        Bei vorhandenen Partnern werden ausdrücklich ausgewählte, noch fehlende
        Rollenflags gemeinsam mit den Personenkonten gespeichert.
        """
        return self._create_accounts(
            company_id=company_id,
            account_numbers=account_numbers,
            name=name,
            partner_id=partner_id,
            allow_role_additions=True,
        )

    def _create_accounts(
        self,
        *,
        company_id: UUID,
        account_numbers: Mapping[PersonAccountRole, str | None],
        name: str,
        partner_id: UUID | None,
        allow_role_additions: bool,
    ) -> tuple[PersonAccount, ...]:
        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")
        if not isinstance(account_numbers, Mapping) or not account_numbers:
            raise ValueError("Mindestens eine Personenkonto-Rolle muss ausgewählt sein.")
        if any(not isinstance(role, PersonAccountRole) for role in account_numbers):
            raise TypeError("account_numbers keys must be PersonAccountRole values")
        if partner_id is not None and not isinstance(partner_id, UUID):
            raise TypeError("partner_id must be a UUID or None")
        try:
            company = self._accounts._lock_company(company_id)
            roles = tuple(
                role
                for role in (PersonAccountRole.DEBITOR, PersonAccountRole.KREDITOR)
                if role in account_numbers
            )
            numbers: dict[PersonAccountRole, str] = {}
            for role in roles:
                requested_number = account_numbers[role]
                number = (
                    self.suggest_account_number(company_id=company_id, role=role)
                    if requested_number is None
                    else self.validate_account_number(requested_number, role)
                )
                # Explicit and suggested numbers receive the same role validation.
                numbers[role] = self.validate_account_number(number, role)
            if len(set(numbers.values())) != len(numbers):
                raise ValueError("Die Kontonummern müssen unterschiedlich sein.")

            if partner_id is None:
                partner = BusinessPartner(
                    company_id=company_id,
                    name=name,
                    is_customer=PersonAccountRole.DEBITOR in roles,
                    is_supplier=PersonAccountRole.KREDITOR in roles,
                )
                self._partners.add(partner, commit=False)
            else:
                partner = self._partners.get(company_id=company_id, partner_id=partner_id)
                if partner is None or not partner.is_active:
                    raise ValueError("Der ausgewählte Geschäftspartner ist nicht aktiv oder gehört nicht zu diesem Mandanten.")
                existing_roles = {
                    PersonAccountRole(row[0])
                    for row in self._session.query(PersonenkontoZuordnung.role)
                    .filter(
                        PersonenkontoZuordnung.mandant_id == company.id,
                        PersonenkontoZuordnung.partner_id == str(partner.partner_id),
                    )
                    .all()
                }
                duplicate_roles = existing_roles.intersection(roles)
                if duplicate_roles:
                    labels = tuple(
                        "Debitor" if role is PersonAccountRole.DEBITOR else "Kreditor"
                        for role in roles
                        if role in duplicate_roles
                    )
                    if len(labels) == 1:
                        raise ValueError(
                            f"Der Geschäftspartner besitzt bereits ein {labels[0]}enkonto."
                        )
                    raise ValueError(
                        "Der Geschäftspartner besitzt bereits Personenkonten als "
                        f"{labels[0]} und {labels[1]}."
                    )

                added_debtor = PersonAccountRole.DEBITOR in roles
                added_creditor = PersonAccountRole.KREDITOR in roles
                missing_role = (
                    added_debtor and not partner.is_customer
                ) or (added_creditor and not partner.is_supplier)
                if missing_role and not allow_role_additions:
                    missing_role_label = (
                        "Debitoren"
                        if added_debtor and not partner.is_customer
                        else "Kreditoren"
                    )
                    raise ValueError(f"Der Geschäftspartner hat keine {missing_role_label}rolle.")

                partner = BusinessPartner(
                    company_id=partner.company_id,
                    partner_id=partner.partner_id,
                    name=partner.name,
                    is_customer=partner.is_customer or added_debtor,
                    is_supplier=partner.is_supplier or added_creditor,
                    is_active=partner.is_active,
                )
                partner_model = (
                    self._session.query(Geschaeftspartner)
                    .filter(
                        Geschaeftspartner.mandant_id == company.id,
                        Geschaeftspartner.partner_id == str(partner.partner_id),
                    )
                    .one()
                )
                partner_model.is_customer = partner.is_customer
                partner_model.is_supplier = partner.is_supplier

            created: list[PersonAccount] = []
            for role in roles:
                account_type = (
                    AccountType.ASSET
                    if role is PersonAccountRole.DEBITOR
                    else AccountType.LIABILITY
                )
                account = Account(
                    template=TemplateAccount(numbers[role], partner.name, account_type),
                    person_account_role=role,
                )
                # Personenkonten haben absichtlich keine individuelle HGB-Regel.
                self._accounts.add_account(
                    company_id=company_id,
                    account=account,
                    mapping_rule=None,
                    commit=False,
                )
                self._session.add(
                    PersonenkontoZuordnung(
                        mandant_id=company.id,
                        account_number=numbers[role],
                        partner_id=str(partner.partner_id),
                        role=role.value,
                    )
                )
                created.append(
                    PersonAccount(account=account, partner=partner, role=role)
                )
            self._session.commit()
            return tuple(created)
        except IntegrityError as exc:
            self._session.rollback()
            raise ValueError(
                "Die Personenkontoanlage kollidiert mit einer bestehenden "
                "Konten- oder Partnerzuordnung. Bitte laden Sie den Nummernvorschlag neu."
            ) from exc
        except Exception:
            self._session.rollback()
            raise

    def get(self, *, company_id: UUID, account_number: str) -> PersonAccount | None:
        company = self._company(company_id)
        row = (
            self._session.query(PersonenkontoZuordnung, Konto, Geschaeftspartner)
            .join(Konto, (Konto.mandant_id == PersonenkontoZuordnung.mandant_id) & (Konto.account_number == PersonenkontoZuordnung.account_number))
            .join(Geschaeftspartner, (Geschaeftspartner.mandant_id == PersonenkontoZuordnung.mandant_id) & (Geschaeftspartner.partner_id == PersonenkontoZuordnung.partner_id))
            .filter(
                PersonenkontoZuordnung.mandant_id == company.id,
                PersonenkontoZuordnung.account_number == account_number,
            )
            .one_or_none()
        )
        if row is None:
            return None
        link, account_model, partner_model = row
        role = PersonAccountRole(link.role)
        partner = self._partners._to_domain(company_id, partner_model)
        account_type = AccountType[account_model.account_type]
        account = Account(
            template=TemplateAccount(account_model.account_number, account_model.name, account_type),
            is_active=account_model.is_active,
            person_account_role=role,
        )
        return PersonAccount(account=account, partner=partner, role=role)

    def list_for_company(self, *, company_id: UUID) -> tuple[PersonAccount, ...]:
        company = self._company(company_id)
        numbers = tuple(
            row[0]
            for row in self._session.query(PersonenkontoZuordnung.account_number)
            .filter(PersonenkontoZuordnung.mandant_id == company.id)
            .order_by(PersonenkontoZuordnung.account_number)
            .all()
        )
        return tuple(
            person_account
            for number in numbers
            if (person_account := self.get(company_id=company_id, account_number=number)) is not None
        )

    def update(
        self,
        *,
        company_id: UUID,
        account_number: str,
        name: str,
        is_active: bool,
    ) -> PersonAccount:
        """Ändert Partnernamen und den Aktivstatus eines Kontos atomar."""
        if not isinstance(is_active, bool):
            raise TypeError("is_active must be a bool")
        try:
            company = self._accounts._lock_company(company_id)
            current = self.get(company_id=company_id, account_number=account_number)
            if current is None:
                raise ValueError("Das Personenkonto wurde nicht gefunden.")
            partner = BusinessPartner(
                company_id=company_id,
                partner_id=current.partner.partner_id,
                name=name,
                is_customer=current.partner.is_customer,
                is_supplier=current.partner.is_supplier,
                is_active=current.partner.is_active,
            )
            partner_model = (
                self._session.query(Geschaeftspartner)
                .filter(
                    Geschaeftspartner.mandant_id == company.id,
                    Geschaeftspartner.partner_id == str(partner.partner_id),
                )
                .one()
            )
            partner_model.name = partner.name
            partner_model.is_customer = partner.is_customer
            partner_model.is_supplier = partner.is_supplier
            partner_model.is_active = partner.is_active
            linked_numbers = [
                row[0]
                for row in self._session.query(PersonenkontoZuordnung.account_number)
                .filter(
                    PersonenkontoZuordnung.mandant_id == company.id,
                    PersonenkontoZuordnung.partner_id == str(partner.partner_id),
                )
                .all()
            ]
            self._session.query(Konto).filter(
                Konto.mandant_id == company.id,
                Konto.account_number.in_(linked_numbers),
            ).update({Konto.name: partner.name}, synchronize_session=False)
            self._session.query(Konto).filter(
                Konto.mandant_id == company.id,
                Konto.account_number == account_number,
            ).update({Konto.is_active: is_active}, synchronize_session=False)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        updated = self.get(company_id=company_id, account_number=account_number)
        assert updated is not None
        return updated

    def import_transfer_records(
        self,
        *,
        company_id: UUID,
        partners: tuple[BusinessPartner, ...],
        person_accounts: tuple[tuple[str, UUID, PersonAccountRole], ...],
        commit: bool = False,
    ) -> None:
        """Speichert vorvalidierte Transferstammdaten in der Importtransaktion."""
        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")
        if not isinstance(partners, tuple) or not all(
            isinstance(partner, BusinessPartner) for partner in partners
        ):
            raise TypeError("partners must be a tuple of BusinessPartner objects")
        if not isinstance(person_accounts, tuple):
            raise TypeError("person_accounts must be a tuple")
        try:
            company = self._accounts._lock_company(company_id)
            partner_ids = {partner.partner_id for partner in partners}
            if len(partner_ids) != len(partners):
                raise ValueError("Der Transfer enthält doppelte Partner-IDs.")
            for partner in partners:
                if partner.company_id != company_id:
                    raise ValueError("Transferpartner gehört zu einem anderen Mandanten.")
                self._partners.add(partner, commit=False)

            seen_numbers: set[str] = set()
            seen_roles: set[tuple[UUID, PersonAccountRole]] = set()
            for number, partner_id, role in person_accounts:
                self.validate_account_number(number, role)
                if partner_id not in partner_ids:
                    raise ValueError("Personenkonto verweist auf einen unbekannten Transferpartner.")
                if number in seen_numbers or (partner_id, role) in seen_roles:
                    raise ValueError("Transfer enthält doppelte Personenkontenzuordnungen.")
                seen_numbers.add(number)
                seen_roles.add((partner_id, role))
                account = self._session.query(Konto).filter_by(
                    mandant_id=company.id, account_number=number
                ).one_or_none()
                partner = next(item for item in partners if item.partner_id == partner_id)
                expected_type = "ASSET" if role is PersonAccountRole.DEBITOR else "LIABILITY"
                if account is None or account.account_type != expected_type:
                    raise ValueError("Transfer-Personenkonto fehlt oder hat einen unpassenden Kontotyp.")
                if account.name != partner.name or account.debit_position_code is not None or account.credit_position_code is not None:
                    raise ValueError("Transfer-Personenkonto hat inkonsistente Stammdaten oder HGB-Zuordnungen.")
                self._session.add(
                    PersonenkontoZuordnung(
                        mandant_id=company.id,
                        account_number=number,
                        partner_id=str(partner_id),
                        role=role.value,
                    )
                )
            if commit:
                self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def _company(self, company_id: UUID) -> Mandant:
        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )
        if company is None:
            raise ValueError("Das Unternehmen ist nicht vorhanden.")
        return company

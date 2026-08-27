"""SQLAlchemy-Modelle für die Persistenz."""
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from openbilanz.database.database import Base


class Mandant(Base):
    """Persistierter Mandant."""

    __tablename__ = "mandanten"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    company_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    rechtsform: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    steuernummer: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    finanzamt: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    steuer_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    wirtschafts_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    bf4: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
    )

    strasse: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    hausnummer: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    plz: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    ort: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    land: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
    )
    bundesland: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
    )
    geschaeftstaetigkeit: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    wirtschaftsjahre: Mapped[list["Wirtschaftsjahr"]] = relationship(
        back_populates="mandant",
        cascade="all, delete-orphan",
    )

    anlagegueter: Mapped[list["Anlagegut"]] = relationship(
        back_populates="mandant",
        cascade="all, delete-orphan",
    )

    konten: Mapped[list["Konto"]] = relationship(
        back_populates="mandant",
        cascade="all, delete-orphan",
    )

    kontenrahmen_konfiguration: Mapped[
        "KontenrahmenKonfiguration | None"
    ] = relationship(
        back_populates="mandant",
        cascade="all, delete-orphan",
        uselist=False,
    )

    umsatzsteuer_konfiguration: Mapped[
        "UmsatzsteuerKonfiguration | None"
    ] = relationship(
        back_populates="mandant",
        cascade="all, delete-orphan",
        uselist=False,
    )

class Konto(Base):
    """Persistiertes Konto eines Mandanten."""

    __tablename__ = "konten"

    __table_args__ = (
        UniqueConstraint(
            "mandant_id",
            "account_number",
            name="uq_konten_mandant_account_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"),
        nullable=False,
    )

    account_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    account_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    debit_position_code: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    credit_position_code: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    mandant: Mapped[Mandant] = relationship(
        back_populates="konten",
    )


class KontenrahmenKonfiguration(Base):
    """Technische Kontenkonfiguration eines Mandanten."""

    __tablename__ = "kontenrahmen_konfiguration"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"),
        nullable=False,
        unique=True,
    )

    opening_balance_account: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    income_summary_account: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    profit_account: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    loss_account: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    retained_earnings_account: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    input_tax_7: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    input_tax_19: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    output_tax_7: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    output_tax_19: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    mandant: Mapped[Mandant] = relationship(
        back_populates="kontenrahmen_konfiguration",
    )

class UmsatzsteuerKonfiguration(Base):
    """Umsatzsteuerliche Konfiguration eines Mandanten."""

    __tablename__ = "umsatzsteuer_konfiguration"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"),
        nullable=False,
        unique=True,
    )

    taxation_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    mandant: Mapped[Mandant] = relationship(
        back_populates="umsatzsteuer_konfiguration",
    )

class Wirtschaftsjahr(Base):
    """Persistiertes Wirtschaftsjahr."""

    __tablename__ = "wirtschaftsjahre"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"),
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="OPEN",
    )

    mandant: Mapped[Mandant] = relationship(
        back_populates="wirtschaftsjahre",
    )

    buchungen: Mapped[list["Buchung"]] = relationship(
        back_populates="wirtschaftsjahr",
        cascade="all, delete-orphan",
    )

    anlageabschreibungen: Mapped[
            list["Anlageabschreibung"]
        ] = relationship(
            back_populates="wirtschaftsjahr",
        )

    anlagebewegungen: Mapped[
            list["Anlagebewegung"]
        ] = relationship(
            back_populates="wirtschaftsjahr",
        )

    opening_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("wirtschaftsjahre.id"),
        nullable=True,
    )

    opening_source: Mapped["Wirtschaftsjahr | None"] = relationship(
        remote_side="Wirtschaftsjahr.id",
        foreign_keys=[opening_source_id],
    )

class Buchung(Base):
    """Persistierte Buchung."""

    __tablename__ = "buchungen"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    booking_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
    )

    wirtschaftsjahr_id: Mapped[int] = mapped_column(
        ForeignKey("wirtschaftsjahre.id"),
        nullable=False,
    )

    booking_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    voucher_no: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    booking_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="REGULAR",
        server_default="REGULAR",
    )

    wirtschaftsjahr: Mapped[Wirtschaftsjahr] = relationship(
        back_populates="buchungen",
    )

    zeilen: Mapped[list["Buchungszeile"]] = relationship(
        back_populates="buchung",
        cascade="all, delete-orphan",
        order_by="Buchungszeile.position",
    )


class Buchungszeile(Base):
    """Persistierte Zeile einer Buchung."""

    __tablename__ = "buchungszeilen"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    buchung_id: Mapped[int] = mapped_column(
        ForeignKey("buchungen.id"),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    account_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    side: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    buchung: Mapped[Buchung] = relationship(
        back_populates="zeilen",
    )

class Anlagegut(Base):
    """Persistiertes Anlagegut."""

    __tablename__ = "anlagegueter"

    __table_args__ = (
        UniqueConstraint(
            "mandant_id",
            "asset_code",
            name="uq_anlagegueter_mandant_asset_code",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    fixed_asset_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
    )

    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"),
        nullable=False,
    )

    asset_code: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    position_code: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    acquisition_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    acquisition_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    depreciation_start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    useful_life_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    mandant: Mapped[Mandant] = relationship(
        back_populates="anlagegueter",
    )

    abschreibungen: Mapped[
        list["Anlageabschreibung"]
    ] = relationship(
        back_populates="anlagegut",
    )

    bewegungen: Mapped[
        list["Anlagebewegung"]
    ] = relationship(
        back_populates="anlagegut",
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    disposal_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    asset_account_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    depreciation_expense_account_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )


class Anlagebewegung(Base):
    """Persistierte buchungswirksame Anlagenbewegung."""

    __tablename__ = "anlagebewegungen"

    __table_args__ = (
        UniqueConstraint(
            "reversed_movement_id",
            name=(
                "uq_anlagebewegungen_"
                "reversed_movement_id"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    movement_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
    )

    anlagegut_id: Mapped[int] = mapped_column(
        ForeignKey("anlagegueter.id"),
        nullable=False,
    )

    wirtschaftsjahr_id: Mapped[int] = mapped_column(
        ForeignKey("wirtschaftsjahre.id"),
        nullable=False,
    )

    buchungszeile_id: Mapped[int] = mapped_column(
        ForeignKey("buchungszeilen.id"),
        unique=True,
        nullable=False,
    )

    movement_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    movement_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    reversed_movement_id: Mapped[int | None] = (
        mapped_column(
            ForeignKey("anlagebewegungen.id"),
            nullable=True,
        )
    )

    anlagegut: Mapped[Anlagegut] = relationship(
        back_populates="bewegungen",
    )

    wirtschaftsjahr: Mapped[Wirtschaftsjahr] = (
        relationship(
            back_populates="anlagebewegungen",
        )
    )

    buchungszeile: Mapped[Buchungszeile] = (
        relationship()
    )

    reversed_movement: Mapped[
        "Anlagebewegung | None"
    ] = relationship(
        remote_side=[id],
        foreign_keys=[reversed_movement_id],
    )



class Anlageabschreibung(Base):
    """Persistierte bestätigte Anlagenabschreibung."""

    __tablename__ = "anlageabschreibungen"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    depreciation_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
    )

    anlagegut_id: Mapped[int] = mapped_column(
        ForeignKey("anlagegueter.id"),
        nullable=False,
    )

    wirtschaftsjahr_id: Mapped[int] = mapped_column(
        ForeignKey("wirtschaftsjahre.id"),
        nullable=False,
    )

    buchungszeile_id: Mapped[int] = mapped_column(
        ForeignKey("buchungszeilen.id"),
        unique=True,
        nullable=False,
    )

    depreciation_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    anlagegut: Mapped[Anlagegut] = relationship(
        back_populates="abschreibungen",
    )

    wirtschaftsjahr: Mapped[Wirtschaftsjahr] = relationship(
        back_populates="anlageabschreibungen",
    )

    buchungszeile: Mapped[Buchungszeile] = relationship()

    depreciation_kind: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

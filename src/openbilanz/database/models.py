"""SQLAlchemy-Modelle für die Persistenz."""
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
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

    wirtschaftsjahre: Mapped[list["Wirtschaftsjahr"]] = relationship(
        back_populates="mandant",
        cascade="all, delete-orphan",
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
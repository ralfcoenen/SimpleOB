"""SQLAlchemy-Modelle für die Persistenz."""
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
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

    mandant: Mapped[Mandant] = relationship(
        back_populates="wirtschaftsjahre",
    )
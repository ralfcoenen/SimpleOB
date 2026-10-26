"""SQLAlchemy-Modelle für die Persistenz."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from simpleob.database.database import Base


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

    gesellschafter: Mapped[list["Gesellschafter"]] = relationship(
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


class KontenTaxonomieZuordnung(Base):
    """Taxonomiezuordnung eines Mandantenkontos."""

    __tablename__ = "konten_taxonomie_zuordnungen"

    __table_args__ = (
        UniqueConstraint(
            "mandant_id",
            "account_number",
            "taxonomy_version",
            name=(
                "uq_konten_taxonomie_"
                "mandant_account_version"
            ),
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

    taxonomy_version: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    concept_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
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

    profit_loss_carryforward_account: Mapped[str] = (
        mapped_column(
            String,
            nullable=False,
        )
    )

    statutory_reserve_account: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    other_revenue_reserves_account: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    distribution_liability_account: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    depreciation_expense_account: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    fixed_asset_disposal_gain_account: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    fixed_asset_disposal_loss_account: Mapped[str] = mapped_column(
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

class Kontenrolle(Base):
    """Fachliche Rollenbelegung eines Mandantenkontos."""

    __tablename__ = "kontenrollen"

    __table_args__ = (
        UniqueConstraint(
            "mandant_id",
            "account_number",
            name="uq_kontenrollen_mandant_account",
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

    role: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    account_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
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

    gewinnverwendungsbuchungen: Mapped[
        list["Gewinnverwendungsbuchung"]
    ] = relationship(
        back_populates="quell_wirtschaftsjahr",
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

    reversal_of_booking_id: Mapped[str | None] = mapped_column(
        String(36),
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


class Geschaeftspartner(Base):
    """Mandantenbezogener Debitor oder Kreditor."""

    __tablename__ = "geschaeftspartner"
    __table_args__ = (
        CheckConstraint(
            "is_customer OR is_supplier",
            name="ck_geschaeftspartner_mindestens_eine_rolle",
        ),
        UniqueConstraint(
            "mandant_id",
            "partner_id",
            name="uq_geschaeftspartner_mandant_partner",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_customer: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_supplier: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class Ausgangsrechnung(Base):
    """Gebuchte Ausgangsrechnung mit eindeutigem Hauptbuchbezug."""

    __tablename__ = "ausgangsrechnungen"
    __table_args__ = (
        ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_ausgangsrechnung_mandant_partner",
        ),
        UniqueConstraint(
            "mandant_id",
            "invoice_number",
            name="uq_ausgangsrechnung_mandant_nummer",
        ),
        CheckConstraint(
            "gross_amount > 0",
            name="ck_ausgangsrechnung_betrag_positiv",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False
    )
    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"), nullable=False
    )
    partner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )
    booking_id: Mapped[str] = mapped_column(
        ForeignKey("buchungen.booking_id"), unique=True, nullable=False
    )


class ForderungsOP(Base):
    """Unveränderlicher Ursprungsbetrag eines Forderungs-OPs."""

    __tablename__ = "forderungs_ops"
    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_forderungs_op_betrag_positiv",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_item_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False
    )
    invoice_id: Mapped[str] = mapped_column(
        ForeignKey("ausgangsrechnungen.invoice_id"), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )


class Eingangsrechnung(Base):
    """Gebuchte Eingangsrechnung mit eindeutigem Hauptbuchbezug."""

    __tablename__ = "eingangsrechnungen"
    __table_args__ = (
        ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_eingangsrechnung_mandant_partner",
        ),
        CheckConstraint(
            "gross_amount > 0",
            name="ck_eingangsrechnung_betrag_positiv",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False
    )
    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"), nullable=False
    )
    partner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )
    booking_id: Mapped[str] = mapped_column(
        ForeignKey("buchungen.booking_id"), unique=True, nullable=False
    )
    duplicate_reason: Mapped[str | None] = mapped_column(String, nullable=True)


class VerbindlichkeitsOP(Base):
    """Unveränderlicher Ursprungsbetrag eines Verbindlichkeits-OPs."""

    __tablename__ = "verbindlichkeits_ops"
    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_verbindlichkeits_op_betrag_positiv",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_item_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False
    )
    invoice_id: Mapped[str] = mapped_column(
        ForeignKey("eingangsrechnungen.invoice_id"), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class Gutschrift(Base):
    """Gebuchte Kunden- oder Lieferantengutschrift."""

    __tablename__ = "gutschriften"
    __table_args__ = (
        ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_gutschrift_mandant_partner",
        ),
        CheckConstraint(
            "credit_note_kind IN ('CUSTOMER', 'SUPPLIER')",
            name="ck_gutschrift_art",
        ),
        CheckConstraint(
            "NOT (original_receivable_invoice_id IS NOT NULL "
            "AND original_payable_invoice_id IS NOT NULL)",
            name="ck_gutschrift_nur_ein_rechnungsbezug",
        ),
        CheckConstraint(
            "(credit_note_kind = 'CUSTOMER' AND original_payable_invoice_id IS NULL) "
            "OR (credit_note_kind = 'SUPPLIER' AND original_receivable_invoice_id IS NULL)",
            name="ck_gutschrift_rechnungsbezug_art",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    credit_note_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False
    )
    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"), nullable=False
    )
    partner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    credit_note_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    note_number: Mapped[str] = mapped_column(String, nullable=False)
    note_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_receivable_invoice_id: Mapped[str | None] = mapped_column(
        ForeignKey("ausgangsrechnungen.invoice_id"), nullable=True
    )
    original_payable_invoice_id: Mapped[str | None] = mapped_column(
        ForeignKey("eingangsrechnungen.invoice_id"), nullable=True
    )
    booking_id: Mapped[str] = mapped_column(
        ForeignKey("buchungen.booking_id"), unique=True, nullable=False
    )
    duplicate_reason: Mapped[str | None] = mapped_column(String, nullable=True)


class GuthabenOP(Base):
    """Unveränderlicher Ursprungsbetrag eines Gutschriftenguthabens."""

    __tablename__ = "guthaben_ops"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_guthaben_op_betrag_positiv"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_item_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False
    )
    credit_note_id: Mapped[str] = mapped_column(
        ForeignKey("gutschriften.credit_note_id"), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class GuthabenOPEreignis(Base):
    """Unveränderliche Betragsänderung eines Guthaben-OPs."""

    __tablename__ = "guthaben_op_ereignisse"
    __table_args__ = (
        CheckConstraint(
            "amount_delta != 0",
            name="ck_guthaben_op_ereignis_betrag_ungleich_null",
        ),
        UniqueConstraint(
            "settlement_id",
            name="uq_guthaben_op_ereignisse_settlement",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    open_item_id: Mapped[str] = mapped_column(
        ForeignKey("guthaben_ops.open_item_id"), nullable=False
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_delta: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )
    settlement_id: Mapped[str | None] = mapped_column(
        ForeignKey("op_guthabenverrechnungen.settlement_id"), nullable=True
    )


class OPGuthabenverrechnung(Base):
    """Gemeinsamer Vorgang für die Verrechnung zweier OPs."""

    __tablename__ = "op_guthabenverrechnungen"
    __table_args__ = (
        ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_op_verrechnung_mandant_partner",
        ),
        CheckConstraint(
            "(direction = 'CUSTOMER' AND receivable_open_item_id IS NOT NULL "
            "AND payable_open_item_id IS NULL) OR "
            "(direction = 'SUPPLIER' AND receivable_open_item_id IS NULL "
            "AND payable_open_item_id IS NOT NULL)",
            name="ck_op_verrechnung_richtung_rechnungs_op",
        ),
        CheckConstraint(
            "direction IN ('CUSTOMER', 'SUPPLIER')",
            name="ck_op_verrechnung_richtung",
        ),
        CheckConstraint("amount > 0", name="ck_op_verrechnung_betrag_positiv"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    settlement_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"), nullable=False
    )
    partner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    receivable_open_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("forderungs_ops.open_item_id"), nullable=True
    )
    payable_open_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("verbindlichkeits_ops.open_item_id"), nullable=True
    )
    credit_open_item_id: Mapped[str] = mapped_column(
        ForeignKey("guthaben_ops.open_item_id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    settlement_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    booking_id: Mapped[str] = mapped_column(
        ForeignKey("buchungen.booking_id"), unique=True, nullable=False
    )


class RechnungsOPVerrechnungsereignis(Base):
    """Unveränderliches Verrechnungsereignis auf der Rechnungsseite."""

    __tablename__ = "rechnungs_op_verrechnungsereignisse"
    __table_args__ = (
        CheckConstraint(
            "(direction = 'CUSTOMER' AND receivable_open_item_id IS NOT NULL "
            "AND payable_open_item_id IS NULL) OR "
            "(direction = 'SUPPLIER' AND receivable_open_item_id IS NULL "
            "AND payable_open_item_id IS NOT NULL)",
            name="ck_rechnungs_op_verrechnung_richtung_op",
        ),
        CheckConstraint("amount > 0", name="ck_rechnungs_op_verrechnung_betrag_positiv"),
        UniqueConstraint("settlement_id", name="uq_rechnungs_op_verrechnung_settlement"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    settlement_id: Mapped[str] = mapped_column(
        ForeignKey("op_guthabenverrechnungen.settlement_id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    receivable_open_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("forderungs_ops.open_item_id"), nullable=True
    )
    payable_open_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("verbindlichkeits_ops.open_item_id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)


class Zahlung(Base):
    """Tatsächliche Zahlung mit Buchungs- und Erfassungszeitpunkt."""

    __tablename__ = "zahlungen"
    __table_args__ = (
        ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_zahlung_mandant_partner",
        ),
        CheckConstraint(
            "direction IN ('CUSTOMER_RECEIPT', 'SUPPLIER_PAYMENT')",
            name="ck_zahlung_richtung",
        ),
        CheckConstraint("amount > 0", name="ck_zahlung_betrag_positiv"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"), nullable=False
    )
    partner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    direction: Mapped[str] = mapped_column(String(24), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    booking_id: Mapped[str] = mapped_column(
        ForeignKey("buchungen.booking_id"), unique=True, nullable=False
    )


class RechnungsOPZahlungsereignis(Base):
    """Unveränderliche Zahlung-zu-Rechnungs-OP-Zuordnung."""

    __tablename__ = "rechnungs_op_zahlungsereignisse"
    __table_args__ = (
        CheckConstraint(
            "(direction = 'CUSTOMER_RECEIPT' AND receivable_open_item_id IS NOT NULL "
            "AND payable_open_item_id IS NULL) OR "
            "(direction = 'SUPPLIER_PAYMENT' AND receivable_open_item_id IS NULL "
            "AND payable_open_item_id IS NOT NULL)",
            name="ck_rechnungs_op_zahlung_richtung_op",
        ),
        CheckConstraint(
            "direction IN ('CUSTOMER_RECEIPT', 'SUPPLIER_PAYMENT')",
            name="ck_rechnungs_op_zahlung_richtung",
        ),
        CheckConstraint(
            "amount > 0", name="ck_rechnungs_op_zahlung_betrag_positiv"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    payment_id: Mapped[str] = mapped_column(
        ForeignKey("zahlungen.payment_id"), index=True, nullable=False
    )
    direction: Mapped[str] = mapped_column(String(24), nullable=False)
    receivable_open_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("forderungs_ops.open_item_id"), nullable=True
    )
    payable_open_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("verbindlichkeits_ops.open_item_id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)

class Gesellschafter(Base):
    """Persistierter Gesellschafter."""

    __tablename__ = "gesellschafter"

    __table_args__ = (
        UniqueConstraint(
            "mandant_id",
            "shareholder_number",
            name=(
                "uq_gesellschafter_mandant_"
                "shareholder_number"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    shareholder_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
    )

    mandant_id: Mapped[int] = mapped_column(
        ForeignKey("mandanten.id"),
        nullable=False,
    )

    shareholder_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="",
        server_default="",
    )

    legal_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    share_numerator: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    share_denominator: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    tax_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="",
        server_default="",
    )

    tax_number_federal_state: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="",
        server_default="",
    )

    tax_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="",
        server_default="",
    )

    wid: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="",
        server_default="",
    )

    mandant: Mapped[Mandant] = relationship(
        back_populates="gesellschafter",
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

    steuerliche_afa_abweichung: Mapped[
        "SteuerlicheAfaAbweichung | None"
        ] = relationship(
            back_populates="anlageabschreibung",
            cascade="all, delete-orphan",
            uselist=False,
        )

class SteuerlicheAfaAbweichung(Base):
    """Persistierte steuerlich abweichende AfA."""

    __tablename__ = "steuerliche_afa_abweichungen"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    anlageabschreibung_id: Mapped[int] = mapped_column(
        ForeignKey("anlageabschreibungen.id"),
        unique=True,
        nullable=False,
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    anlageabschreibung: Mapped["Anlageabschreibung"] = relationship(
        back_populates="steuerliche_afa_abweichung",
    )


class GewinnverwendungsJahresdaten(Base):
    """Persistierte Jahresdaten zur Ergebnisverwendung."""

    __tablename__ = "gewinnverwendungs_jahresdaten"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    wirtschaftsjahr_id: Mapped[int] = mapped_column(
        ForeignKey("wirtschaftsjahre.id"),
        unique=True,
        nullable=False,
    )

    statutory_reserve_addition: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    other_revenue_reserves_addition: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    statutory_reserve_release: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    other_revenue_reserves_release: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    distribution: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    profit_loss_carryforward: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    wirtschaftsjahr: Mapped[Wirtschaftsjahr] = relationship()


class Gewinnverwendungsbuchung(Base):
    """Persistierte bestätigte Umsetzung einer Ergebnisverwendung."""

    __tablename__ = "gewinnverwendungsbuchungen"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    posting_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
    )

    quell_wirtschaftsjahr_id: Mapped[int] = mapped_column(
        ForeignKey("wirtschaftsjahre.id"),
        nullable=False,
    )

    buchungszeile_id: Mapped[int] = mapped_column(
        ForeignKey("buchungszeilen.id"),
        unique=True,
        nullable=False,
    )

    posting_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    posting_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    quell_wirtschaftsjahr: Mapped[Wirtschaftsjahr] = relationship(
        back_populates="gewinnverwendungsbuchungen",
    )

    buchungszeile: Mapped[Buchungszeile] = relationship()


class Eigenkapitaleinlage(Base):
    """Kennzeichnung einer Buchungszeile als BVV-Einlage."""

    __tablename__ = "eigenkapitaleinlagen"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    buchungszeile_id: Mapped[int] = mapped_column(
        ForeignKey("buchungszeilen.id"),
        unique=True,
        nullable=False,
    )

    buchungszeile: Mapped[Buchungszeile] = relationship()

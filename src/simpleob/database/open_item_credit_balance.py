"""Gemeinsame Berechnung des verfügbaren Guthaben-OP-Betrags."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from simpleob.database.models import GuthabenOPEreignis, GuthabenOPRueckerstattung
from simpleob.domain.money import ZERO


def available_credit_amount(
    session: Session,
    *,
    open_item_id: UUID | str,
    original_amount: Decimal,
) -> Decimal:
    """Ursprungsbetrag abzüglich Verrechnungen und Rückerstattungen."""
    stored_id = str(open_item_id)
    event_total = (
        session.query(func.sum(GuthabenOPEreignis.amount_delta))
        .filter(GuthabenOPEreignis.open_item_id == stored_id)
        .scalar()
    )
    refund_total = (
        session.query(func.sum(GuthabenOPRueckerstattung.amount))
        .filter(GuthabenOPRueckerstattung.open_item_id == stored_id)
        .scalar()
    )
    amount = original_amount + (event_total or ZERO) - (refund_total or ZERO)
    if amount < ZERO:
        raise ValueError("Verrechnungen und Rückerstattungen reduzieren den Guthaben-OP unter null.")
    return amount

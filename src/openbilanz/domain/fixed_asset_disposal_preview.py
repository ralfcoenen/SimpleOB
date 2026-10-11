"""Vorschau eines Anlagenverkaufs."""

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.domain.depreciation_proposal import (
    DepreciationProposal,
)
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_disposal_calculation import (
    FixedAssetDisposalCalculation,
)


@dataclass(frozen=True, slots=True)
class FixedAssetDisposalPreview:
    """Enthält die fachliche Vorschau eines Anlagenverkaufs."""

    fixed_asset: FixedAsset
    previous_depreciation: Decimal
    depreciation_proposal: DepreciationProposal | None
    accumulated_depreciation: Decimal
    disposal_calculation: FixedAssetDisposalCalculation

    # Ursprüngliche Eingaben für die Aktualitätsprüfung.
    tax_rate: int
    counter_account_number: str

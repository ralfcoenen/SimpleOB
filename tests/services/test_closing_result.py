from dataclasses import is_dataclass
from decimal import Decimal

from openbilanz.services.closing_result import ClosingResult


def test_closing_result_contains_net_income() -> None:
    result = ClosingResult(
        net_income=Decimal("300.00"),
    )

    assert is_dataclass(result)
    assert result.net_income == Decimal("300.00")
    
    

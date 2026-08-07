import pytest

from openbilanz.importers.chart_of_accounts_importer import (
    ChartOfAccountsImporter,
)


def test_chart_of_accounts_importer_is_abstract() -> None:
    with pytest.raises(TypeError):
        ChartOfAccountsImporter()



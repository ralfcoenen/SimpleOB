from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from simpleob.core.config import ApplicationConfig
from simpleob.qt_main import _stage_new_company_chart_initialization
from simpleob.ui_qt import start_dialog as start_dialog_module
from simpleob.ui_qt.start_dialog import StartDialog


@pytest.fixture
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


@pytest.fixture
def config(tmp_path):
    return ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "simpleob.db",
        taxonomy_dir=tmp_path / "taxonomy",
        config_file=tmp_path / "config.toml",
    )


@pytest.mark.parametrize(
    ("case", "uses_standard_chart"),
    (
        ("unveränderter Standardkontenrahmen", True),
        ("individueller Kontenrahmen", False),
        ("bearbeiteter Standardkontenrahmen", False),
    ),
)
def test_chart_classification_reaches_initialization_service(
    monkeypatch,
    app,
    config,
    case,
    uses_standard_chart,
):
    bundle = SimpleNamespace(
        chart=object(),
        taxonomy_mappings={"1000": "concept"},
        control_accounts=object(),
        vat_accounts=object(),
        account_roles=object(),
        taxonomy_version="6.9",
    )
    context = SimpleNamespace(
        company=SimpleNamespace(company_id="company-1"),
        fiscal_year=object(),
    )

    class AcceptedNewCompanyDialog:
        def __init__(self, *_args, **_kwargs):
            self.result = context
            self.chart_bundle = bundle
            self.uses_standard_chart = uses_standard_chart

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        start_dialog_module,
        "NewCompanyDialog",
        AcceptedNewCompanyDialog,
    )

    repository = MagicMock()
    repository.list_companies.return_value = ()
    start_dialog = StartDialog(repository=repository, config=config)
    monkeypatch.setattr(start_dialog, "accept", MagicMock())

    start_dialog._create_new_company()

    assert start_dialog.chart_bundle is bundle, case
    assert start_dialog.uses_standard_chart is uses_standard_chart, case

    initialization_service = MagicMock()
    _stage_new_company_chart_initialization(
        company_repository=repository,
        chart_of_accounts_initialization_service=initialization_service,
        dialog=start_dialog,
    )

    assert initialization_service.initialize.call_args.kwargs[
        "use_standard_defaults"
    ] is uses_standard_chart, case

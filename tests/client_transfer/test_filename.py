"""Portable und eindeutige Namen für beide Sicherungswege."""

import re
from datetime import datetime
from unittest.mock import Mock

import pytest

from openbilanz.client_transfer import filename as module


def test_name_contains_company_local_time_and_random_id(monkeypatch):
    clock = Mock()
    clock.now.return_value = datetime(2026, 10, 18, 14, 7)
    monkeypatch.setattr(module, "datetime", clock)
    monkeypatch.setattr(module, "uuid4", lambda: Mock(hex="abcdef1234567890"))
    assert module.client_backup_filename("Müller & Söhne GmbH") == (
        "SimpleOB-Mandant-Müller & Söhne GmbH-20261018-1407-abcdef123456.simpleob"
    )
    clock.now.assert_called_once_with()


@pytest.mark.parametrize("name", ['../A<>:"/\\|?*\x00\n\x7f', "", " ... ", "CON"])
def test_name_is_a_safe_single_component(name):
    result = module.client_backup_filename(name)
    assert not re.search(r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]', result)
    assert re.fullmatch(
        r"SimpleOB-Mandant-.+-\d{8}-\d{4}-[0-9a-f]{12}\.simpleob", result
    )


@pytest.mark.parametrize("name", ["A" * 1000, "Ü" * 1000, "😀" * 1000])
def test_long_names_preserve_suffix_and_fit_filesystem_limit(name, tmp_path):
    result = module.client_backup_filename(name)
    assert len(result.encode("utf-8")) <= 255
    assert len(result.encode("utf-16-le")) // 2 <= 255
    assert result.endswith(".simpleob")
    (tmp_path / result).touch()


def test_random_names_differ():
    assert len({module.client_backup_filename("Mandant") for _ in range(100)}) == 100

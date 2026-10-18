"""Commitstatus auch ohne erreichbaren PostgreSQL-Testserver prüfen."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from openbilanz.services import client_deletion_service as module
from openbilanz.services.client_deletion_service import (
    ClientDeletionCommitUnknown,
    ClientDeletionService,
)


@pytest.mark.parametrize(
    "state,invalidated,unknown",
    [
        (None, True, True),
        ("08006", False, True),
        ("40003", False, True),
        ("57P01", False, True),
        ("40001", False, False),
        ("23503", False, False),
    ],
)
def test_commit_status_never_retries_and_only_rolls_back_confirmed_aborts(
    monkeypatch,
    tmp_path,
    state,
    invalidated,
    unknown,
):
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    connection = engine.connect.return_value.__enter__.return_value
    connection.execution_options.return_value = connection
    original = RuntimeError("Commit fehlgeschlagen")
    original.sqlstate = state
    error = OperationalError(None, None, original, connection_invalidated=invalidated)
    connection.commit.side_effect = error
    repository = MagicMock()
    repository.capture.return_value = {"mandanten": [{"name": "Mandant"}]}
    monkeypatch.setattr(module, "ClientDeletionRepository", lambda conn: repository)
    monkeypatch.setattr(module, "_transfer_repositories", lambda session: {})
    monkeypatch.setattr(module, "ClientTransferExporter", MagicMock())
    backup = MagicMock()
    monkeypatch.setattr(module, "write_verified_client_backup", backup)
    service = ClientDeletionService(engine=engine, position_provider=None)
    monkeypatch.setattr(service, "_verify_complete_restore", MagicMock())
    path = tmp_path / "commit.simpleob"
    with pytest.raises(ClientDeletionCommitUnknown if unknown else OperationalError):
        service.delete(company_id=uuid4(), expected_name="Mandant", backup_path=path)
    connection.commit.assert_called_once()
    backup.assert_called_once()
    repository.delete_captured.assert_called_once()
    if unknown:
        connection.rollback.assert_not_called()
        connection.invalidate.assert_called_once()
    else:
        connection.rollback.assert_called_once()
        connection.invalidate.assert_not_called()

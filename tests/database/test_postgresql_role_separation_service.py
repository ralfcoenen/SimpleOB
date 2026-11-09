from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.migration_service import PostgreSQLSchemaStatus
from simpleob.database.postgresql_existing_installation_inspector import (
    PostgreSQLExistingInstallationAssessment,
    PostgreSQLObjectOwner,
    PostgreSQLOwnershipAssessment,
)
from simpleob.database.postgresql_role_separation_service import (
    PostgreSQLRoleSeparationService,
)


@pytest.fixture
def config(tmp_path):
    return ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "unused.sqlite",
        taxonomy_dir=tmp_path,
        config_file=tmp_path / "config.toml",
        database_url_override=(
            "postgresql+psycopg://legacy_owner@localhost:5432/simpleob_books"
        ),
    )


def _assessment(
    *,
    ownership=PostgreSQLOwnershipAssessment.UNIFORM_OWNERSHIP,
    operating="legacy_owner",
    migration="legacy_owner",
    schema_status=PostgreSQLSchemaStatus.CURRENT,
    blockers=(),
):
    from simpleob.database import models

    tables = tuple(
        PostgreSQLObjectOwner(name, "table", "legacy_owner")
        for name in sorted(set(models.Base.metadata.tables) | {"alembic_version"})
    )
    return PostgreSQLExistingInstallationAssessment(
        database_name="simpleob_books",
        server_version_num=180004,
        operating_role=operating,
        database_owner="legacy_owner",
        schema_name="public",
        schema_owner="pg_database_owner",
        table_owners=tables,
        sequence_owners=(),
        alembic_version_owner="legacy_owner",
        alembic_version_privileges=(("SELECT", True),),
        role_privileges=(),
        default_privileges=(),
        current_revision="head",
        head_revision="head",
        schema_status=schema_status,
        ownership_assessment=ownership,
        migration_role_candidate=migration,
        blockers=tuple(blockers),
        notes=(),
    )


def _call(service, config, **overrides):
    arguments = dict(
        application_config=config,
        owner_credentials=PostgreSQLCredentials("owner-secret"),
        operating_username="simpleob_app",
        operating_credentials=PostgreSQLCredentials("app-secret"),
        create_operating_role=True,
        admin_username="db_admin",
        admin_credentials=PostgreSQLCredentials("admin-secret"),
        confirmed=True,
    )
    arguments.update(overrides)
    return service.separate_roles(**arguments)


def _patch_success(monkeypatch, *, final_assessment=None):
    first_inspector = Mock()
    first_inspector.inspect.side_effect = [_assessment(), _assessment()]
    final_inspector = Mock()
    final_inspector.inspect.return_value = final_assessment or _assessment(
        ownership=PostgreSQLOwnershipAssessment.SPLIT_ROLES_COMPATIBLE,
        operating="simpleob_app",
        migration="legacy_owner",
    )
    monkeypatch.setattr(
        "simpleob.database.postgresql_role_separation_service.PostgreSQLExistingInstallationInspector",
        Mock(side_effect=[first_inspector, final_inspector]),
    )
    monkeypatch.setattr(
        "simpleob.database.postgresql_role_separation_service.PostgreSQLRoleSeparationService._verify_exact_simpleob_schema",
        Mock(),
    )
    monkeypatch.setattr(
        "simpleob.database.postgresql_role_separation_service.PostgreSQLRoleSeparationService._reject_public_create_grants",
        Mock(),
    )
    monkeypatch.setattr(
        "simpleob.database.postgresql_role_separation_service.PostgreSQLRoleSeparationService._create_operating_role",
        Mock(),
    )
    monkeypatch.setattr(
        "simpleob.database.postgresql_role_separation_service.PostgreSQLRoleSeparationService._grant_operating_access",
        Mock(),
    )
    monkeypatch.setattr(
        "simpleob.database.postgresql_role_separation_service.DatabaseMigrationService",
        Mock(),
    )
    return first_inspector, final_inspector


def test_uniform_installation_is_split_then_verified_before_return(config, monkeypatch):
    first_inspector, final_inspector = _patch_success(monkeypatch)

    result = _call(PostgreSQLRoleSeparationService(), config)

    assert result.changed
    assert result.operating_role_created
    assert result.migration_role == "legacy_owner"
    assert result.operating_role == "simpleob_app"
    assert result.database_url == (
        "postgresql+psycopg://simpleob_app@localhost:5432/simpleob_books"
    )
    assert "secret" not in result.database_url
    assert first_inspector.inspect.call_count == 2
    assert final_inspector.inspect.called


def test_uneven_ownership_aborts_before_role_or_grant_changes(config, monkeypatch):
    inspector = Mock()
    inspector.inspect.return_value = _assessment(
        ownership=PostgreSQLOwnershipAssessment.INCONSISTENT_OWNERSHIP,
        migration=None,
        blockers=("Gemischte Eigentümerschaft",),
    )
    with (
        patch(
            "simpleob.database.postgresql_role_separation_service.PostgreSQLExistingInstallationInspector",
            return_value=inspector,
        ),
        patch.object(
            PostgreSQLRoleSeparationService,
            "_create_operating_role",
        ) as create_role,
        patch.object(
            PostgreSQLRoleSeparationService,
            "_grant_operating_access",
        ) as grant_access,
    ):
        with pytest.raises(RuntimeError, match="Gemischte Eigentümerschaft"):
            _call(PostgreSQLRoleSeparationService(), config)
    create_role.assert_not_called()
    grant_access.assert_not_called()


def test_already_split_installation_is_not_changed(config, monkeypatch):
    assessment = _assessment(
        ownership=PostgreSQLOwnershipAssessment.SPLIT_ROLES_COMPATIBLE,
        operating="simpleob_app",
        migration="legacy_owner",
    )
    with (
        patch(
            "simpleob.database.postgresql_role_separation_service.PostgreSQLExistingInstallationInspector"
        ) as inspector,
        patch.object(
            PostgreSQLRoleSeparationService,
            "_grant_operating_access",
        ) as grant_access,
    ):
        inspector.return_value.inspect.return_value = assessment
        result = PostgreSQLRoleSeparationService().separate_roles(
            application_config=replace(
                config,
                database_url_override=(
                    "postgresql+psycopg://simpleob_app@localhost:5432/simpleob_books"
                ),
            ),
            owner_credentials=PostgreSQLCredentials("owner-secret"),
            operating_username="simpleob_app",
            operating_credentials=PostgreSQLCredentials("app-secret"),
            create_operating_role=False,
            confirmed=True,
        )
    assert not result.changed
    assert result.migration_role == "legacy_owner"
    grant_access.assert_not_called()


def test_suitable_existing_operating_role_can_be_used(config, monkeypatch):
    _patch_success(monkeypatch)
    validate_role = Mock()
    monkeypatch.setattr(
        "simpleob.database.postgresql_role_separation_service.PostgreSQLRoleSeparationService._validate_existing_operating_role",
        validate_role,
    )

    result = _call(
        PostgreSQLRoleSeparationService(),
        config,
        create_operating_role=False,
        admin_username=None,
        admin_credentials=None,
    )

    assert result.changed
    assert not result.operating_role_created
    validate_role.assert_called_once()


def test_missing_admin_privileges_prevent_role_creation(config, monkeypatch):
    from simpleob.database.postgresql_role_separation_service import (
        PostgreSQLRoleSeparationService as Service,
    )

    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.one_or_none.return_value = SimpleNamespace(
        rolsuper=False,
        rolcreaterole=False,
    )
    with (
        patch(
            "simpleob.database.postgresql_role_separation_service.create_engine",
            return_value=engine,
        ),
        patch(
            "simpleob.database.postgresql_role_separation_service.PostgreSQLUserService._create_role"
        ) as create_role,
    ):
        with pytest.raises(RuntimeError, match="CREATEROLE oder SUPERUSER"):
            Service._create_operating_role(
                url=__import__("sqlalchemy.engine", fromlist=["make_url"]).make_url(
                    config.database_url
                ),
                admin_username="db_admin",
                admin_credentials=PostgreSQLCredentials("admin-secret"),
                operating_username="simpleob_app",
                operating_credentials=PostgreSQLCredentials("app-secret"),
            )
    create_role.assert_not_called()


def test_grant_failure_never_returns_a_new_configuration(config, monkeypatch):
    _patch_success(monkeypatch)
    monkeypatch.setattr(
        "simpleob.database.postgresql_role_separation_service.PostgreSQLRoleSeparationService._grant_operating_access",
        Mock(side_effect=RuntimeError("grant failed")),
    )
    with pytest.raises(RuntimeError, match="grant failed"):
        _call(PostgreSQLRoleSeparationService(), config)

"""Personenkonten-Roundtrip auf einem isolierten PostgreSQL-Cluster."""

from __future__ import annotations

import os
import socket
import subprocess
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from simpleob.client_transfer.model import (
    ClientTransferAccount,
    ClientTransferBusinessPartner,
    ClientTransferPersonAccount,
)
from simpleob.database.database import Base
from tests.client_transfer.test_roundtrip import (
    _build_rich_transfer,
    _build_position_provider,
    _import_and_export,
)


@pytest.mark.integration
def test_person_account_transfer_roundtrip_on_isolated_postgresql(
    tmp_path: Path,
) -> None:
    binary_dir_value = os.environ.get("SIMPLEOB_POSTGRES_BIN")
    if not binary_dir_value:
        pytest.skip("SIMPLEOB_POSTGRES_BIN für isolierten PostgreSQL-Test setzen.")
    binary_dir = Path(binary_dir_value)

    def run(name: str, *args: str) -> None:
        subprocess.run(
            [str(binary_dir / name), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
        )

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    cluster = str(tmp_path / "person-account-cluster")
    started = False
    engine = None
    try:
        run(
            "initdb",
            "-D",
            cluster,
            "-U",
            "postgres",
            "--auth=trust",
            "--no-locale",
            "--encoding=UTF8",
        )
        run(
            "pg_ctl",
            "-D",
            cluster,
            "-l",
            str(tmp_path / "postgres.log"),
            "-o",
            f"-h 127.0.0.1 -p {port} -k ''",
            "-w",
            "start",
        )
        started = True
        url = URL.create(
            "postgresql+psycopg",
            username="postgres",
            host="127.0.0.1",
            port=port,
            database="postgres",
        )
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        partner_id = UUID("22222222-2222-2222-2222-222222222222")
        source = _build_rich_transfer()
        source = replace(
            source,
            client=replace(
                source.client,
                master_data=replace(
                    source.client.master_data, legal_form="UG", country="DE"
                ),
            ),
        )
        transfer = replace(
            source,
            client=replace(
                source.client,
                accounts=source.client.accounts
                + (
                    ClientTransferAccount(
                        account_number="10000",
                        name="PostgreSQL Partner GmbH",
                        account_type="ASSET",
                        is_active=True,
                    ),
                    ClientTransferAccount(
                        account_number="70000",
                        name="PostgreSQL Partner GmbH",
                        account_type="LIABILITY",
                        is_active=False,
                    ),
                ),
                business_partners=(
                    ClientTransferBusinessPartner(
                        partner_id=partner_id,
                        name="PostgreSQL Partner GmbH",
                        is_customer=True,
                        is_supplier=True,
                        is_active=True,
                    ),
                ),
                person_accounts=(
                    ClientTransferPersonAccount("10000", partner_id, "DEBITOR"),
                    ClientTransferPersonAccount("70000", partner_id, "KREDITOR"),
                ),
            ),
        )

        exported = _import_and_export(
            engine=engine,
            transfer=transfer,
        )

        assert exported.client.person_accounts == transfer.client.person_accounts
        assert exported.client.business_partners == transfer.client.business_partners
        exported_accounts = {
            account.account_number: account for account in exported.client.accounts
        }
        assert exported_accounts["10000"].debit_position_code is None
        assert exported_accounts["70000"].credit_position_code is None
        assert exported_accounts["70000"].is_active is False
        assert exported_accounts["1200"].debit_position_code == "HGB.266.AKTIVA.B.IV"
    finally:
        if engine is not None:
            engine.dispose()
        if started:
            run("pg_ctl", "-D", cluster, "-m", "fast", "-w", "stop")

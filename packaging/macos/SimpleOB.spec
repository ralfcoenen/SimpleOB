# -*- mode: python ; coding: utf-8 -*-

from importlib.metadata import version
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
APPLICATION_VERSION = version("openbilanz")

eric_sdk_root_value = os.environ.get("SIMPLEOB_ERIC_SDK_ROOT")

if not eric_sdk_root_value:
    raise RuntimeError(
        "SIMPLEOB_ERIC_SDK_ROOT ist nicht gesetzt. "
        "Der Wert muss auf das plattformspezifische ERiC-SDK-Verzeichnis "
        "zeigen, das die Verzeichnisse 'lib' und 'Beispiel' enthält."
    )

ERIC_ROOT = Path(eric_sdk_root_value).expanduser().resolve()
ERIC_LIB_DIR = ERIC_ROOT / "lib"
ERIC_PLUGIN_DIR = ERIC_LIB_DIR / "plugins"

ERIC_WRAPPER_DIR = (
    ERIC_ROOT
    / "Beispiel"
    / "ericdemo-python"
    / "ericdemo"
    / "ericapi"
)

required_eric_paths = (
    ERIC_LIB_DIR,
    ERIC_PLUGIN_DIR,
    ERIC_WRAPPER_DIR,
)

missing_eric_paths = [
    path
    for path in required_eric_paths
    if not path.exists()
]

if missing_eric_paths:
    missing = "\n".join(
        f"  - {path}"
        for path in missing_eric_paths
    )
    raise RuntimeError(
        "Die ERiC-SDK-Struktur ist unvollständig:\n"
        f"{missing}"
    )

arelle_datas = collect_data_files(
    "arelle",
    include_py_files=False,
)

eric_binaries = [
    (
        str(path),
        "eric/lib",
    )
    for path in sorted(
        ERIC_LIB_DIR.glob("*.dylib")
    )
]

eric_binaries.extend(
    (
        str(path),
        "eric/lib/plugins",
    )
    for path in sorted(
        ERIC_PLUGIN_DIR.glob("*.dylib")
    )
)

eric_wrapper_datas = [
    (
        str(ERIC_WRAPPER_DIR),
        "eric/Beispiel/ericdemo-python/ericdemo/ericapi",
    ),
]

a = Analysis(
    [str(PROJECT_ROOT / "packaging/macos/simpleob_main.py")],
    pathex=[str(SRC_ROOT)],
    binaries=eric_binaries,
    datas=[
        (
            str(
                SRC_ROOT
                / "openbilanz/resources/chart_of_accounts/"
                "openbilanz_standard.csv"
            ),
            "openbilanz/resources/chart_of_accounts",
        ),
        (
            str(
                SRC_ROOT
                / "openbilanz/resources/e_bilanz/account_mappings/6.9/"
                "openbilanz_standard.csv"
            ),
            "openbilanz/resources/e_bilanz/account_mappings/6.9",
        ),
        *arelle_datas,
        *eric_wrapper_datas,
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SimpleOB",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SimpleOB",
)

app = BUNDLE(
    coll,
    name="SimpleOB.app",
    icon=None,
    bundle_identifier="de.subuthi.simpleob",
    version=APPLICATION_VERSION,
)

# packaging/openbilanz_windows.spec

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    copy_metadata,
)


project_root = Path(SPECPATH).parent
src_root = project_root / "src"

arelle_datas, arelle_binaries, arelle_hiddenimports = (
    collect_all("arelle")
)

datas = [
    (
        str(
            src_root
            / "openbilanz"
            / "resources"
            / "chart_of_accounts"
            / "openbilanz_standard.csv"
        ),
        "openbilanz/resources/chart_of_accounts",
    ),
    *arelle_datas,
]

datas.extend(
    copy_metadata("arelle-release")
)

a = Analysis(
    [
        str(
            src_root
            / "openbilanz"
            / "main.py"
        )
    ],
    pathex=[
        str(src_root),
    ],
    binaries=[
        *arelle_binaries,
    ],
    datas=datas,
    hiddenimports=[
        *arelle_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(
    a.pure,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OpenBilanz",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="OpenBilanz",
)

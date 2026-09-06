"""Zentrale Versionsinformationen für SimpleOB."""

from importlib.metadata import PackageNotFoundError, version

_DISTRIBUTION_NAME = "openbilanz"
_FALLBACK_VERSION = "0.0.0"


def get_application_version() -> str:
    """Liefert die installierte SimpleOB-Anwendungsversion."""
    try:
        return version(_DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return _FALLBACK_VERSION

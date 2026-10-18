"""Gemeinsame, portable Dateinamen für Mandantensicherungen."""

import re
import unicodedata
from datetime import datetime
from uuid import uuid4


def client_backup_filename(company_name: str) -> str:
    """Erzeugt einen lokalen Zeitstempel und einen zufälligen Sicherungsnamen.

    Maximal 255 UTF-8-Bytes begrenzen auch mehrbyteige Mandantennamen sicher.
    Damit bleibt der Dateiname auch unter dem Windows-Limit von 255 UTF-16-
    Codeeinheiten. Die Länge des gewählten Verzeichnispfads bleibt separat.
    """
    name = unicodedata.normalize("NFC", company_name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]', "_", name)
    name = name.strip(" .") or "Mandant"
    prefix = "SimpleOB-Mandant-"
    suffix = f"-{datetime.now():%Y%m%d-%H%M}-{uuid4().hex[:12]}.simpleob"
    budget = 255 - len((prefix + suffix).encode("utf-8"))
    name = name.encode("utf-8")[:budget].decode("utf-8", errors="ignore")
    name = name.rstrip(" .") or "Mandant"
    return f"{prefix}{name}{suffix}"

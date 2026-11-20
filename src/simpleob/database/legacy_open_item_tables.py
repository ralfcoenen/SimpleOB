"""Historische OP-Tabellen, die vor ihrer Alembic-Bereinigung vorkommen können."""

from alembic.script import ScriptDirectory
from alembic.util import CommandError

LEGACY_OPEN_ITEM_TABLES = frozenset(
    {
        "zahlungszuordnungskorrekturereignisse",
        "zahlungszuordnungskorrekturen",
        "rechnungs_op_zahlungsereignisse",
        "rechnungs_op_verrechnungsereignisse",
        "guthaben_op_ereignisse",
        "guthaben_op_rueckerstattungsruecknahmen",
        "guthaben_op_rueckerstattungen",
        "op_guthabenverrechnungen",
        "zahlungen",
        "guthaben_ops",
        "rechnungs_op_stornos",
        "forderungs_ops",
        "verbindlichkeits_ops",
        "gutschriften",
        "ausgangsrechnungen",
        "eingangsrechnungen",
    }
)

OPEN_ITEM_CLEANUP_REVISION = "a9c6e3b17d42"


def is_pre_open_item_cleanup_revision(
    *,
    current_revision: str | None,
    head_revision: str | None,
    script_directory: ScriptDirectory,
) -> bool:
    """Return whether a uniquely known revision is before OP cleanup.

    Revision identifiers are opaque. Alembic's graph traversal handles branch
    points and merge revisions; any unresolved or ambiguous graph fails closed.
    """
    if not current_revision or not head_revision:
        return False
    try:
        configured_head = script_directory.get_current_head()
        if configured_head != head_revision:
            return False
        ancestors_of_cleanup = {
            revision.revision
            for revision in script_directory.iterate_revisions(
                OPEN_ITEM_CLEANUP_REVISION,
                "base",
            )
        }
        ancestors_of_head = {
            revision.revision
            for revision in script_directory.iterate_revisions(
                head_revision,
                "base",
            )
        }
    except (CommandError, KeyError, TypeError, ValueError):
        return False
    return (
        current_revision in ancestors_of_cleanup
        and current_revision != OPEN_ITEM_CLEANUP_REVISION
        and OPEN_ITEM_CLEANUP_REVISION in ancestors_of_head
    )

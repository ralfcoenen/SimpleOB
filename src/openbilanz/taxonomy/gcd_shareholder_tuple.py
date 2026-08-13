"""GCD-Tuple-Strukturen für Gesellschafter."""

from dataclasses import dataclass

from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.text_fact import TaxonomyTextFact


@dataclass(frozen=True, slots=True)
class GcdShareholderLegalStatusTuple:
    """Enthält den ausgewählten Rechtsstatus eines Gesellschafters."""

    fact: TaxonomyTextFact


@dataclass(frozen=True, slots=True)
class GcdShareDivideKeyTuple:
    """Enthält Zähler und Nenner der Beteiligungsquote."""

    numerator: TaxonomyTextFact
    denominator: TaxonomyTextFact


@dataclass(frozen=True, slots=True)
class GcdShareholderTuple:
    """Enthält alle Facts eines GCD-Gesellschafter-Tuples."""

    name: TaxonomyTextFact
    shareholder_id: TaxonomyTextFact
    tax_number: TaxonomyTextFact
    tax_id: TaxonomyTextFact
    wid: TaxonomyTextFact
    legal_status: GcdShareholderLegalStatusTuple
    share_divide_key: GcdShareDivideKeyTuple
    first_name: TaxonomyTextFact | None = None
    group: TaxonomyTextFact | None = None
    current_number: TaxonomyFact | None = None
    signer_id: TaxonomyTextFact | None = None
    special_balance_required: TaxonomyTextFact | None = None
    extension_required: TaxonomyTextFact | None = None
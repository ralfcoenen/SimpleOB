"""GCD-Tuple-Strukturen für Gesellschafter."""

from dataclasses import dataclass

from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.nil_fact import TaxonomyNilFact
from simpleob.taxonomy.text_fact import TaxonomyTextFact


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
    tax_number: TaxonomyTextFact | TaxonomyNilFact
    tax_id: TaxonomyTextFact | TaxonomyNilFact
    wid: TaxonomyTextFact | TaxonomyNilFact
    legal_status: GcdShareholderLegalStatusTuple
    share_divide_key: GcdShareDivideKeyTuple
    first_name: TaxonomyTextFact | None = None
    group: TaxonomyTextFact | None = None
    current_number: TaxonomyFact | None = None
    signer_id: TaxonomyTextFact | None = None
    economic_id: TaxonomyTextFact | None = None
    id_not_assigned: TaxonomyTextFact | None = None
    special_balance_required: TaxonomyTextFact | None = None
    extension_required: TaxonomyTextFact | None = None

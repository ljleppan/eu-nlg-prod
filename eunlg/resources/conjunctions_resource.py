from typing import Dict

CONJUNCTIONS: Dict[str, Dict[str, str]] = {
    "fi": {
        "default_combiner": "ja",
        "inverse_combiner": "mutta",
        "subord_clause_start": ", mikä on",
        "comparator": "kuin",
    },
    "en": {
        "default_combiner": "and",
        "inverse_combiner": "but",
        "subord_clause_start": ", which is",
        "comparator": "than",
    },
    "de": {
        "default_combiner": "und",
        "inverse_combiner": "aber",
        "subord_clause_start": ", der/das/die ist",
        "comparator": "als",
    },
    "hr": {"default_combiner": "i", "inverse_combiner": "ali"},
    "ru": {
        "default_combiner": "и",
        "inverse_combiner": "но",
        "subord_clause_start": ", который",
        "comparator": "чем",
    },
    "sl": {
        "default_combiner": "in",
        "inverse_combiner": "ampak",
        "subord_clause_start": ", ki je",
        "comparator": "kot",
    },
}

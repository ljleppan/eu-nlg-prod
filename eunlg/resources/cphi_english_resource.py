from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

en: [in {time},] [in {location},] the {value_type} was {value} {unit}
en: [in {time},] [in {location},] it was {value} {unit}
en-head: in {location}, in {time}, the {value_type} was {value} {unit}
| value_type = cphi:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

en: [in {time},] [in {location},] the {value_type} was {value} {unit} more than the EU average
en: [in {time},] [in {location},] it was {value} {unit} more than the EU average
en-head: in {location}, in {time}, the {value_type} was {value} {unit} over EU average
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value > 0

en: [in {time},] [in {location},] the {value_type} was {value, abs} {unit} less than the EU average
en: [in {time},] [in {location},] it was {value, abs} {unit} less than the EU average
en-head: in {location}, in {time}, {value_type} at {value, abs} {unit} below EU average
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value < 0

en: [in {time},] [in {location},] the {value_type} was the same as the EU average
en: [in {time},] [in {location},] it was the same as the EU average
en-head: in {location}, in {time}, {value_type} tied with EU average
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

en: [in {time},] [in {location},] the {value_type} was {value} {unit} more than in US
en: [in {time},] [in {location},] it was {value} {unit} more than in US
en-head: in {location}, in {time}, {value_type} at {value} {unit} over US
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value > 0

en: [in {time},] [in {location},] the {value_type} was {value, abs} {unit} less than in US
en: [in {time},] [in {location},] it was {value, abs} {unit} less than in US
en-head: in {location}, in {time}, {value_type} at {value, abs} {unit} below US
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value < 0

en: [in {time},] [in {location},] the {value_type} was the same as in US
en: [in {time},] [in {location},] it was the same as in US
en-head: in {location}, in {time}, {value_type} tied with US
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

en: [in {time},] {location} had the {value, ord} highest {value_type} across the observed countries
en: [in {time},] {location} had the {value, ord} highest value for it across the observed countries
en-head: in {time}, {location, case=gen} {value, ord} {value_type} highest
| value_type = cphi:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

en: [in {time},] {location} had the {value, ord} lowest {value_type} across the observed countries
en: [in {time}, ]{location} had the {value, ord} lowest value for it across the observed countries
en-head: in {time}, {location, case=gen} {value, ord} {value_type} lowest
| value_type = cphi:.*:rank_reverse.*
"""

INDEX_CATEGORIES: Dict[str, str] = {
    "hicp2015": "harmonized consumer price index",  # harmonized consumer price index (2015=100)
    "rt1": "monthly growth rate",  # growth rate on previous period (t/t-1)
    "rt12": "yearly growth rate",  # growth rate (t/t-12)
    "cp-hi00": "'all items'",
    "cp-hi01": "'food and non-alcoholic beverages'",
    "cp-hi02": "'alcoholic beverages and tobacco'",
    "cp-hi03": "'clothing and footwear'",
    "cp-hi04": "'housing, water, electricity, gas and other fuels'",
    "cp-hi05": "'furnishings, household equipment and maintenance'",
    "cp-hi06": "'health'",
    "cp-hi07": "'transport'",
    "cp-hi08": "'communication'",
    "cp-hi09": "'recreation and culture'",
    "cp-hi10": "'education'",
    "cp-hi11": "'hotels, cafes and restaurants'",
    "cp-hi12": "'miscellaneous goods and services'",
    "cp-hi00xef": "'all items excluding energy, food, alcohol and tobacco'",
    "cp-hi00xtb": "'all items excluding tobacco'",
    "cp-hie": "'energy'",
    "cp-hif": "'food'",
    "cp-hifu": "'unprocessed food'",
    "cp-hig": "'total goods'",
    "cp-hiig": "'industrial goods'",
    "cp-his": "'total services'",
    "cp-hiigxe": "'non-energy industrial goods'",
    "cp-hi00xe": "'all items excluding energy'",
    "cp-hi00xefu": "'all items excluding energy and unprocessed food'",
    "cp-hi00xes": "'all items excluding energy and seasonal food'",
}


class CPHIEnglishResource(TabularDataResource):
    def __init__(self):
        super().__init__(["en"], ["cphi"])
        self.templates = TEMPLATES
        self.partials = INDEX_CATEGORIES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            EnglishCphiRawRealizer,
            EnglishCphiChangeRealizer,
            EnglishCphiCategoryRealizer,
            EnglishUnitCphiPercentageRealizer,
            EnglishUnitCphiPointsRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class EnglishCphiRawRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(registry, "en", r"^cphi:([^:]*):([^:]*)" + MAYBE_RANK_OR_COMP + "$", "{} for the category {}")


class EnglishCphiChangeRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "en",
            r"^cphi:([^:]*):([^:]*):(rt12?)" + MAYBE_RANK_OR_COMP + "$",
            "{2} of the {0} for the category {1}",
        )


class EnglishUnitCphiPercentageRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "en",
            r"^\[UNIT:cphi:.*\]$",
            "percentage points",
            slot_requirements=lambda slot: "rt1" in slot.value.split(":") or "rt12" in slot.value.split(":"),
        )


class EnglishUnitCphiPointsRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "en",
            r"^\[UNIT:cphi:.*\]$",
            "points",
            slot_requirements=lambda slot: "rt1" not in slot.value.split(":") and "rt12" not in slot.value.split(":"),
        )


class EnglishCphiCategoryRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "en", INDEX_CATEGORIES)

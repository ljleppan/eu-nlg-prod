from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

en: [in {time},] [in {location},] the {value_type} was {value} {unit}
en: [in {time},] [in {location},] it was {value} {unit}
en-head: in {location}, in {time}, the {value_type} was {value} {unit}
| value_type = health:funding:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

en: [in {time},] [in {location},] the {value_type} was {value} {unit} more than the EU average
en: [in {time},] [in {location},] it was {value} {unit} more than the EU average
en-head: in {location}, in {time}, the {value_type} at {value} {unit} over EU average
| value_type = health:funding:.*:comp_eu, value_type != .*:rank.*, value > 0

en: [in {time},] [in {location},] the {value_type} was {value, abs} {unit} less than the EU average
en: [in {time},] [in {location},] it was {value, abs} {unit} less than the EU average
en-head: in {location}, in {time}, the {value_type} at {value, abs} {unit} below EU average
| value_type = health:funding:.*:comp_eu, value_type != .*:rank.*, value < 0

en: [in {time},] [in {location},] the {value_type} was the same as the EU average
en: [in {time},] [in {location},] it was the same as the EU average
en-head: in {location}, in {time}, {value_type} tied with EU average
| value_type = health:funding:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

en: [in {time},] [in {location},] the {value_type} was {value} {unit} more than in US
en: [in {time},] [in {location},] it was {value} {unit} more than in US
en-head: in {location}, in {time}, {value_type} at {value} {unit} over US
| value_type = health:funding:.*:comp_us, value_type != .*:rank.*, value > 0

en: [in {time},] [in {location},] the {value_type} was {value, abs} {unit} less than in US
en: [in {time},] [in {location},] it was {value, abs} {unit} less than in US
en-head: in {location}, in {time}, {value_type} at {value, abs} {unit} below US
| value_type = health:funding:.*:comp_us, value_type != .*:rank.*, value < 0

en: [in {time},] [in {location},] the {value_type} was the same as in US
en: [in {time},] [in {location},] it was the same as in US
en-head: in {location}, in {time}, {value_type} tied with US
| value_type = health:funding:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

en: [in {time},] {location} had the {value, ord} highest {value_type} across the observed countries
en: [in {time}, ]{location} had the {value, ord} highest value for it across the observed countries
en-head: in {time}, {location, case=gen} {value, ord} {value_type} highest
| value_type = health:funding:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

en: [in {time},] {location} had the {value, ord} lowest {value_type} across the observed countries
en: [in {time}, ]{location} had the {value, ord} lowest value for it across the observed countries
en-head: in {time}, {location, case=gen} {value, ord} {value_type} lowest
| value_type = health:funding:.*:rank_reverse.*
"""
PARTIALS: Dict[str, str] = {
    "tot-hf": "total health care funding",
    "hf1": "health care funding from government schemes and compulsory contributory health care financing schemes",
    "hf11": "health care funding from government schemes",
    "hf12-13": "health care funding from compulsory contributory health insurance schemes and compulsory medical saving accounts",  # noqa: E501
    "hf121": "health care funding from social health insurance schemes",
    "hf122": "health care funding from compulsory private insurance schemes",
    "hf13": "health care funding from compulsory medical savings accounts (CMSA)",
    "hf2": "health care funding from voluntary health care payment schemes",
    "hf21": "health care funding from voluntary health insurance schemes",
    "hf22": "health care funding from NPISH financing schemes",
    "hf23": "health care funding from enterprise financing schemes",
    "hf3": "household out-of-pocket health care payments",
    "hf31": "out-of-pocket payments excluding cost-sharing",
    "hf32": "health care funding from cost sharing with third-party payers",
    "hf4": "health care funding from rest of the world financing schemes (non-resident)",
    "hf41": "health care funding from compulsory schemes (non-resident)",
    "hf42": "health care funding from voluntary schemes (non-resident)",
    "hf-unk": "health care funding from other, unknown, schemes",
}


UNITS: Dict[str, str] = {
    "[UNIT:health:funding:mio-eur]": "million euro",
    "[UNIT:health:funding:eur-hab]": "euro per inhabitant",
    "[UNIT:health:funding:mio-nac]": "million units of national currency",
    "[UNIT:health:funding:nac-hab]": "national currency per inhabitant",
    "[UNIT:health:funding:mio-pps]": "million purchasing power standards (PPS)",
    "[UNIT:health:funding:pps-hab]": "purchasing power standard (PPS) per inhabitant",
    "[UNIT:health:funding:pc-gdp]": "percent of the gross domestic product",
    "[UNIT:health:funding:pc-che]": "percent of the total current health expenditure",
}


class HealthFundingEnglishResource(TabularDataResource):
    def __init__(self):
        super().__init__(["en"], ["health_funding"])
        self.templates = TEMPLATES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            EnglishHealthFundingRawRealizer,
            EnglishHealthFundingUnitSimplifier,
            EnglishHealthFundingUnitRealizer,
            EnglishHealthFundingPartialRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class EnglishHealthFundingRawRealizer(RegexRealizer):
    def __init__(self, registry):
        # "the harmonized consumer price index for the category 'health'
        super().__init__(registry, "en", r"^health:funding:([^:]*):[^:]*" + MAYBE_RANK_OR_COMP + "$", "{}")


class EnglishHealthFundingUnitSimplifier(RegexRealizer):
    def __init__(self, registry):
        # "the monthly growth rate of the harmonized consumer price index for the category 'health'
        super().__init__(
            registry, "en", r"^\[UNIT:health:funding:[^:]*:([^:]*):?.*\]$", "[UNIT:health:funding:{}]",
        )


class EnglishHealthFundingUnitRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "en", UNITS)


class EnglishHealthFundingPartialRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "en", PARTIALS)

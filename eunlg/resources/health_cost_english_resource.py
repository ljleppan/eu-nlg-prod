from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

en: [in {time},] [in {location},] the {value_type} was {value} {unit}
en: [in {time},] [in {location},] it was {value} {unit}
en-head: in {location}, in {time}, the {value_type} was {value} {unit}
| value_type = health:cost:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

en: [in {time},] [in {location},] the {value_type} was {value} {unit} more than the EU average
en: [in {time},] [in {location},] it was {value} {unit} more than the EU average
en-head: in {location}, in {time}, the {value_type} at {value} {unit} over EU average
| value_type = health:cost:.*:comp_eu, value_type != .*:rank.*, value > 0

en: [in {time},] [in {location},] the {value_type} was {value, abs} {unit} less than the EU average
en: [in {time},] [in {location},] it was {value, abs} {unit} less than the EU average
en-head: in {location}, in {time}, the {value_type} at {value, abs} {unit} below EU average
| value_type = health:cost:.*:comp_eu, value_type != .*:rank.*, value < 0

en: [in {time},] [in {location},] the {value_type} was the same as the EU average
en: [in {time},] [in {location},] it was the same as the EU average
en-head: in {location}, in {time}, {value_type} tied with EU average
| value_type = health:cost:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

en: [in {time},] [in {location},] the {value_type} was {value} {unit} more than in US
en: [in {time},] [in {location},] it was {value} {unit} more than in US
en-head: in {location}, in {time}, {value_type} at {value} {unit} over US
| value_type = health:cost:.*:comp_us, value_type != .*:rank.*, value > 0

en: [in {time},] [in {location},] the {value_type} was {value, abs} {unit} less than in US
en: [in {time},] [in {location},] it was {value, abs} {unit} less than in US
en-head: in {location}, in {time}, {value_type} at {value, abs} {unit} below US
| value_type = health:cost:.*:comp_us, value_type != .*:rank.*, value < 0

en: [in {time},] [in {location},] the {value_type} was the same as in US
en: [in {time},] [in {location},] it was the same as in US
en-head: in {location}, in {time}, {value_type} tied with US
| value_type = health:cost:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

en: [in {time},] {location} had the {value, ord} highest {value_type} across the observed countries
en: [in {time}, ]{location} had the {value, ord} highest value for it across the observed countries
en-head: in {time}, {location, case=gen} {value, ord} highest {value_type}
| value_type = health:cost:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

en: [in {time},] {location} had the {value, ord} lowest {value_type} across the observed countries
en: [in {time}, ]{location} had the {value, ord} lowest value for it across the observed countries
en-head: in {time}, {location, case=gen} {value, ord} lowest {value_type}
| value_type = health:cost:.*:rank_reverse.*
"""

PARTIALS: Dict[str, str] = {
    "tot-hc": "current health care expenditure",
    "hc1-2": "cost of curative care and rehabilitative care",
    "hc1": "cost of curative care",
    "hc11-21": "cost of inpatient curative and rehabilitative care",
    "hc11": "cost of inpatient curative care",
    "hc12-22": "cost of day curative and rehabilitative care",
    "hc12": "cost of day curative care",
    "hc13-23": "cost of outpatient curative and rehabilitative care",
    "hc13": "cost of outpatient curative care",
    "hc131": "cost of general outpatient curative care",
    "hc132": "cost of dental outpatient curative care",
    "hc133": "cost of specialised outpatient curative care",
    "hc139": "cost of all other outpatient curative care n.e.c.",
    "hc14-24": "cost of home-based curative and rehabilitative care",
    "hc14": "cost of home-based curative care",
    "hc2": "cost of rehabilitative care",
    "hc21": "cost of inpatient rehabilitative care",
    "hc22": "cost of day rehabilitative care",
    "hc23": "cost of outpatient rehabilitative care",
    "hc24": "cost of home-based rehabilitative care",
    "hc3": "cost of long-term health care",
    "hc31": "cost of inpatient long-term health care",
    "hc32": "cost of day long-term health care",
    "hc33": "cost of outpatient long-term health care",
    "hc34": "cost of home-based long-term health care",
    "hc4": "cost of ancillary health services",
    "hc41": "cost of laboratory services",
    "hc42": "cost of imaging services",
    "hc43": "cost of patient transportation",
    "hc5": "cost of medical goods",
    "hc51": "cost of pharmaceuticals and other medical non-durable goods",
    "hc511": "cost of prescribed medicines",
    "hc512": "cost of over-the-counter medicines",
    "hc513": "cost of other medical non-durable goods",
    "hc52": "cost of therapeutic appliances and other medical durable goods",
    "hc6": "cost of preventive care",
    "hc61": "cost of information, education and counseling programmes",
    "hc62": "cost of immunisation programmes",
    "hc63": "cost of early disease detection programmes",
    "hc64": "cost of healthy condition monitoring programmes",
    "hc65": "cost of epidemiological surveillance and risk and disease control programmes",
    "hc66": "cost of preparing for disaster and emergency response programmes",
    "hc7": "cost of governance and health system and financing administration",
    "hc71": "cost of governance and health system administration",
    "hc72": "cost of administration of health financing",
    "hc-unk": "cost of other, unknown, health care services",
    "hcr1": "cost of long-term social care",
}


UNITS: Dict[str, str] = {
    "[UNIT:health:cost:mio-eur]": "million euro",
    "[UNIT:health:cost:eur-hab]": "euro per inhabitant",
    "[UNIT:health:cost:mio-nac]": "million units of national currency",
    "[UNIT:health:cost:nac-hab]": "national currency per inhabitant",
    "[UNIT:health:cost:mio-pps]": "million purchasing power standards (PPS)",
    "[UNIT:health:cost:pps-hab]": "purchasing power standards (PPS) per inhabitant",
    "[UNIT:health:cost:pc-gdp]": "percent of the gross domestic product",
    "[UNIT:health:cost:pc-che]": "percent of the total current health expenditure",
}


class HealthCostEnglishResource(TabularDataResource):
    def __init__(self):
        super().__init__(["en"], ["health_cost"])
        self.templates = TEMPLATES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            EnglishHealthCostRawRealizer,
            EnglishHealthCostUnitSimplifier,
            EnglishHealthCostUnitRealizer,
            EnglishHealthCostPartialRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class EnglishHealthCostRawRealizer(RegexRealizer):
    def __init__(self, registry):
        # "the harmonized consumer price index for the category 'health'
        super().__init__(registry, "en", r"^health:cost:([^:]*):?.*" + MAYBE_RANK_OR_COMP + "$", "{}")


class EnglishHealthCostUnitSimplifier(RegexRealizer):
    def __init__(self, registry):
        # "the monthly growth rate of the harmonized consumer price index for the category 'health'
        super().__init__(
            registry, "en", r"^\[UNIT:health:cost:[^:]*:([^:]*):?.*\]$", "[UNIT:health:cost:{}]",
        )


class EnglishHealthCostUnitRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "en", UNITS)


class EnglishHealthCostPartialRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "en", PARTIALS)

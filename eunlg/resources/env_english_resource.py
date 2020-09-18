from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

en: [in {time},] [in {location},] the {value_type} was {value} {unit}
en: [in {time},] [in {location},] it was {value} {unit}
en-head: in {location}, in {time}, the {value_type} was {value} {unit}
| value_type = env:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

en: [in {time},] [in {location},] the {value_type} was {value} {unit} more than the EU average
en: [in {time},] [in {location},] it was {value} {unit} more than the EU average
en-head: in {location}, in {time}, the {value_type} was {value} {unit} over EU average
| value_type = env:.*:comp_eu, value_type != .*:rank.*, value > 0

en: [in {time},] [in {location},] the {value_type} was {value, abs} {unit} less than the EU average
en: [in {time},] [in {location},] it was {value, abs} {unit} less than the EU average
en-head: in {location}, in {time}, {value_type} at {value, abs} {unit} below EU average
| value_type = env:.*:comp_eu, value_type != .*:rank.*, value < 0

en: [in {time},] [in {location},] the {value_type} was the same as the EU average
en: [in {time},] [in {location},] it was the same as the EU average
en-head: in {location}, in {time}, {value_type} tied with EU average
| value_type = env:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

en: [in {time},] [in {location},] the {value_type} was {value} {unit} more than in US
en: [in {time},] [in {location},] it was {value} {unit} more than in US
en-head: in {location}, in {time}, {value_type} at {value} {unit} over US
| value_type = env:.*:comp_us, value_type != .*:rank.*, value > 0

en: [in {time},] [in {location},] the {value_type} was {value, abs} {unit} less than in US
en: [in {time},] [in {location},] it was {value, abs} {unit} less than in US
en-head: in {location}, in {time}, {value_type} at {value, abs} {unit} below US
| value_type = env:.*:comp_us, value_type != .*:rank.*, value < 0

en: [in {time},] [in {location},] the {value_type} was the same as in US
en: [in {time},] [in {location},] it was the same as in US
en-head: in {location}, in {time}, {value_type} tied with US
| value_type = env:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

en: [in {time},] {location} had the {value, ord} highest {value_type} across the observed countries
en: [in {time}, ]{location} had the {value, ord} highest value for it across the observed countries
en-head: in {time}, {location, case=gen} {value, ord} {value_type} highest
| value_type = env:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

en: [in {time},] {location} had the {value, ord} lowest {value_type} across the observed countries
en: [in {time}, ]{location} had the {value, ord} lowest value for it across the observed countries
en-head: in {time}, {location, case=gen} {value, ord} {value_type} lowest
| value_type = env:.*:rank_reverse.*
"""

PARTIALS: Dict[str, str] = {
    "tot-cepa": "total environmental protection activities",
    "cepa1-4-9": "other protection activities",
    "cepa1": "protection of ambient air and climate",
    "cepa112-122": "protection of climate and ozone layer",
    "cepa2": "wastewater management",
    "cepa3": "waste management",
    "cepa4": "protection and remediation of soil, groundwater and surface water",
    "cepa5": "noise and vibration abatement (excluding workplace protection)",
    "cepa6": "protection of biodiversity and landscapes",
    "cepa7": "protection against radiation (excluding external safety)",
    "cepa8": "environmental research and development",
    "cepa9": "other environmental protection activities",
    "eps-p1": "output",
    "eps-p11": "market output",
    "eps-p13": "non-market output",
    "eps-p1-anc": "environmental protection related ancillary output",
    "eps-p2-eps-sp": "intermediate consumption of environmental protection services by corporations as specialist producers",  # noqa: E501
    "p3-eps": "final consumption expenditure of environmental protection services",
    "eps-p51g-np": "gross fixed capital formation and acquisition less disposals of non-produced non-financial assets",
    "p7-eps": "import of environmental protection services",
    "p6-eps": "export of environmental protection services",
    "eps-d21x31": "taxes less subsidies on products",
    "eps-sup-nu": "supply at purchasers' prices available for national uses",
    "ep-d3-7-92-99-p": "current and capital transfers for environmental protection, paid",
    "ep-d3-7-92-99-r": "current and capital transfers for environmental protection, received",
}


class ENVEnglishResource(TabularDataResource):
    def __init__(self):
        super().__init__(["en"], ["env"])
        self.templates = TEMPLATES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            EnglishEnvRawRealizer,
            EnglishEnvUnitMioEurRealizer,
            EnglishEnvUnitMioNacRealizer,
            EnglishEnvPartialRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class EnglishEnvRawRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry, "en", r"^env:([^:]*):([^:]*):[^:]*" + MAYBE_RANK_OR_COMP + "$", "spending on {} in terms of {}"
        )


class EnglishEnvUnitMioEurRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(registry, "en", r"^\[UNIT:env:.*:mio-eur:?.*\]$", "million euros")


class EnglishEnvUnitMioNacRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(registry, "en", r"^\[UNIT:env:.*:mio-nac:?.*\]$", "million in their national currency")


class EnglishEnvPartialRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "en", PARTIALS)

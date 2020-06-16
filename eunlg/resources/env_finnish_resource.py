from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

fi: [{location, case=ssa},] {value_type} oli {value} {unit} [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit}
| value_type = env:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

fi: [{location, case=ssa},] {value_type} oli {value} {unit} enemmän kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} yli EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} yli EU:n keskiarvon
| value_type = env:.*:comp_eu, value_type != .*:rank.*, value > 0

fi: [{location, case=ssa},] {value_type} oli {value} {unit} vähemmän kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} ali EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} ali EU:n keskiarvon
| value_type = env:.*:comp_eu, value_type != .*:rank.*, value < 0

fi: [{location, case=ssa},] {value_type} oli sama kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli sama kuin EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} sama kuin EU:n keskiarvon
| value_type = env:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

fi: [{location, case=ssa},] {value_type} oli {value} {unit} enemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} enemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} oli {value} {unit} yli EU:n keskiarvon
| value_type = env:.*:comp_us, value_type != .*:rank.*, value > 0

fi: [{location, case=ssa},] {value_type} oli {value} {unit} vähemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} vähemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} vähemmän kuin Yhdysvalloissa
| value_type = env:.*:comp_us, value_type != .*:rank.*, value < 0

fi: [{location, case=ssa},] {value_type} oli sama kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli sama kuin EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} sama kuin EU:n keskiarvon
| value_type = env:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

fi: [{location, case=gen}] {value_type} oli {value, ord} korkein [{time, case=gen}]
fi: [{location, case=gen}] se oli {value, ord} korkein [{time, case=gen}]
fi-head: [{time, case=gen}] [[{location, case=ssa}] {value, ord} korkein {value_type}
| value_type = env:.*:rank, value_type != .*rank_reverse.*

# RANK_REVERSE

fi: [{location, case=gen}] {value_type} oli {value, ord} matalin [{time, case=gen}]
fi: [{location, case=gen}] se oli {value, ord} matalin [{time, case=gen}]
fi-head: [{time, case=gen}] [[{location, case=ssa}] {value, ord} matalin {value_type}
| value_type = env:.*:rank_reverse.*
"""

PARTIALS: Dict[str, str] = {
    "tot_cepa": "kaikki ympäristönsuojelu",
    "cepa1-4-9": "muut ympäristönsuojelu",
    "cepa1": "ilman ja ilmaston suojelu",
    "cepa112-122": "ilmaston ja otsonikerroksen suojelu",
    "cepa2": "jätevesihuolto",
    "cepa3": "jätehuolto",
    "cepa4": "maan, pintaveden ja pohjaveden suojelu",
    "cepa5": "melun ja värinän hallinta (pl. työsuojelutoimet)",
    "cepa6": "luonnon monimuotoisuuden ja maisemien suojelu",
    "cepa7": "säteilyltä suojaus",
    "cepa8": "ympäristön tutkimus ja kehitys",
    "cepa9": "muut ympäristönsuojelutoimet",
    "eps-p1": "",
    "eps-p11": "markkinoiden suoriteita",
    "eps-p13": "markkinoiden ulkopuolisia suoriteita",
    "eps-p1-anc": "ympäristön suojaukseen liittyviä avustussuoriteita",
    "eps-p2-eps-sp": "ympäristonsuojelupalveluita yritysten toimesta",  # noqa: E501
    "p3-eps": "ympäristönsuojelupalveluita",
    "eps-p51g-np": "kiinteän pääoman bruttomuodostus tietyin vähennyksin",
    "p7-eps": "ympäristönsuojelun maahantuonti",
    "p6-eps": "ympäristönsuojelun maastavietin",
    "eps-d21x31": "verot vähennettynä tuotetuilla",
    "eps-sup-nu": "tarjonta kansalliseen käyttöön ostajan hinnalla",
    "ep-d3-7-92-99-p": "tulon ja pääomansiirrot ympäristönsuojeluun, maksetut",
    "ep-d3-7-92-99-r": "tulon ja pääomansiirrot ympäristönsuojeluun, saadut",
}


class ENVFinnishResource(TabularDataResource):
    def __init__(self):
        super().__init__(["fi"], ["env"])
        self.templates = TEMPLATES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            FinnishEnvRawRealizer,
            FinnishEnvUnitMioEurRealizer,
            FinnishEnvUnitMioNacRealizer,
            FinnishEnvPartialRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class FinnishEnvRawRealizer(RegexRealizer):
    def __init__(self, registry):
        # "the harmonized consumer price index for the category 'health'
        super().__init__(
            registry, "fi", r"^env:([^:]*):[^:]*:[^:]*" + MAYBE_RANK_OR_COMP + "$", "kohteeseen {} keytetty summa"
        )


class FinnishEnvUnitMioEurRealizer(RegexRealizer):
    def __init__(self, registry):
        # "the monthly growth rate of the harmonized consumer price index for the category 'health'
        super().__init__(
            registry, "fi", r"^\[UNIT:env:[^:]*:([^:]*):?.*:mio-eur:?.*\]$", "miljoonaa euroa kun mittarina oli {}"
        )


class FinnishEnvUnitMioNacRealizer(RegexRealizer):
    def __init__(self, registry):
        # "the monthly growth rate of the harmonized consumer price index for the category 'health'
        super().__init__(
            registry,
            "fi",
            r"^\[UNIT:env:[^:]*:([^:]*):?.*:mio-nac:?.*\]$",
            "miljoonaa paikallisessa valuutassa kun mittarina oli {}",
        )


class FinnishEnvNullUnitRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "fi",
            r"^\[UNIT:env:[^:]*:([^:]*):?.*\]$",
            "kun mittarina oli {}",
            slot_requirements=lambda slot: "mio-nac" not in slot.value.split(":")
            and "mio-eur" not in slot.value.split(":"),
        )


class FinnishEnvPartialRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "fi", PARTIALS)

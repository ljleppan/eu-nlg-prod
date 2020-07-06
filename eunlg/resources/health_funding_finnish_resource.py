from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

fi: [{location, case=ssa},] {value_type} oli {value} {unit} [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} oli {value} {unit}
| value_type = health:funding:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

fi: [{location, case=ssa},] {value_type} oli {value} {unit} enemmän kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} yli EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} yli EU:n keskiarvon
| value_type = health:funding:.*:comp_eu, value_type != .*:rank.*, value > 0

fi: [{location, case=ssa},] {value_type} oli {value} {unit} vähemmän kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} ali EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} ali EU:n keskiarvon
| value_type = health:funding:.*:comp_eu, value_type != .*:rank.*, value < 0

fi: [{location, case=ssa},] {value_type} oli sama kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli sama kuin EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} sama kuin EU:n keskiarvon
| value_type = health:funding:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

fi: [{location, case=ssa},] {value_type} oli {value} {unit} enemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} enemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} oli {value} {unit} yli EU:n keskiarvon
| value_type = health:funding:.*:comp_us, value_type != .*:rank.*, value > 0

fi: [{location, case=ssa},] {value_type} oli {value, abs} {unit} vähemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value, abs} {unit} vähemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} vähemmän kuin Yhdysvalloissa
| value_type = health:funding:.*:comp_us, value_type != .*:rank.*, value < 0

fi: [{location, case=ssa},] {value_type} oli sama kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli sama kuin EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} sama kuin EU:n keskiarvon
| value_type = health:funding:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

fi: [{location, case=gen}] {value_type} oli {value, ord} korkein [{time, case=ssa}]
fi: [{location, case=gen}] se oli {value, ord} korkein [{time, case=ssa}]
fi-head: [{time, case=ssa}] [[{location, case=ssa}] {value, ord} korkein {value_type}
| value_type = health:funding:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

fi: [{location, case=gen}] {value_type} oli {value, ord} matalin [{time, case=ssa}]
fi: [{location, case=gen}] se oli {value, ord} matalin [{time, case=ssa}]
fi-head: [{time, case=ssa}] [[{location, case=ssa}] {value, ord} matalin {value_type}
| value_type = health:funding:.*:rank_reverse.*
"""


PARTIALS: Dict[str, str] = {
    "tot-hf": "terveydenhuollon kokonaisrahoitus",
    "hf1": "terveydenhuollon rahoitus hallituksen järjestämistä ja pakollisista järjestelmistä",
    "hf11": "hallituksen järjestämä terveydenhuollon rahoitus",
    "hf12-13": "pakollisten sairasvakuutuksien ja lääkinnällisten säästötilien kautta järjestetty rahoitus",  # noqa: E501
    "hf121": "erveydenhuollon rahoitus sosiaaliterveyden vakuutusten kautta",
    "hf122": "terveydenhuollon rahoitus pakollisten yksityisten sairasvakuutuksien kautta",
    "hf13": "terveydenhuollon rahoitus pakollisten sairassäästötilien kautta)",
    "hf2": "vapaaehtoisten maksujärjestelmien kautta järjestetty terveydenhuollon rahoitus",
    "hf21": "vapaaehtoisten sairasvakuutusten kautta järjestetty terveydenhuollon rahoitus",
    "hf22": "NPISH-rahoituksen kautta järjestetty terveydenhuollon rahoitus",
    "hf23": "terveydenhuollon yhtiörahoitus",
    "hf3": "talouksien itse maksaman terveydenhuollon hinta",
    "hf31": "talouksien itse maksaman terveyden huollon hinta pl. kulujenjako",
    "hf32": "terveydenhuollon rahoitus kolmannen osapuolien kulujenjakosopimusten kautta",
    "hf4": "terveydenhuollon rahoitus muun maailman rahoituksen kautta",
    "hf41": "terveydenhuollon rahoitus pakollisten maksujen kautta (ei-pysyvät asukkaat)",
    "hf42": "terveydenhuollon rahoitus vapaaehtoisten maksujen kautta (ei-pysyvät asukkeet)",
    "hf-unk": "terveydenhuollon rahoitus muiden, tuntemattomien, tapojen kautta",
}

UNITS: Dict[str, str] = {
    "[UNIT:health:funding:mio-eur]": "miljoonaa euroa",
    "[UNIT:health:funding:eur-hab]": "euroa per asukas",
    "[UNIT:health:funding:mio-nac]": "miljoonaa paikallisessa valuutassa",
    "[UNIT:health:funding:nac-hab]": "paikallista valuuttayksikköä per asukas",
    "[UNIT:health:funding:mio-pps]": "miljoonaa ostovoimastandardia (OVS)",
    "[UNIT:health:funding:pps-hab]": "ostovoimastandaria (OVS) per asukas",
    "[UNIT:health:funding:pc-gdp]": "prosenttia bruttokansantuotteesta",
    "[UNIT:health:funding:pc-che]": "prosenttia terveydenhuollon kokonaismenoista",
}


class HealthFundingFinnishResource(TabularDataResource):
    def __init__(self):
        super().__init__(["fi"], ["health_funding"])
        self.templates = TEMPLATES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            FinnishHealthFundingRawRealizer,
            FinnishHealthFundingUnitSimplifier,
            FinnishHealthFundingUnitRealizer,
            FinnishHealthFundingPartialRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class FinnishHealthFundingRawRealizer(RegexRealizer):
    def __init__(self, registry):
        # "the harmonized consumer price index for the category 'health'
        super().__init__(registry, "fi", r"^health:funding:([^:]*):[^:]*" + MAYBE_RANK_OR_COMP + "$", "{}")


class FinnishHealthFundingUnitSimplifier(RegexRealizer):
    def __init__(self, registry):
        # "the monthly growth rate of the harmonized consumer price index for the category 'health'
        super().__init__(
            registry, "fi", r"^\[UNIT:health:funding:[^:]*:([^:]*):?.*\]$", "[UNIT:health:funding:{}]",
        )


class FinnishHealthFundingUnitRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "fi", UNITS)


class FinnishHealthFundingPartialRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "fi", PARTIALS)

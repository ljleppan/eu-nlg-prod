from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

fi: [{location, case=ssa},] {value_type} oli {value} {unit} [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit}
| value_type = cphi:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

fi: [{location, case=ssa},] {value_type} oli {value} {unit} enemmän kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} yli EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} yli EU:n keskiarvon
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value > 0

fi: [{location, case=ssa},] {value_type} oli {value} {unit} vähemmän kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} ali EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} ali EU:n keskiarvon
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value < 0

fi: [{location, case=ssa},] {value_type} oli sama kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli sama kuin EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} sama kuin EU:n keskiarvon
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

fi: [{location, case=ssa},] {value_type} oli {value} {unit} enemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} enemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} oli {value} {unit} yli EU:n keskiarvon
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value > 0

fi: [{location, case=ssa},] {value_type} oli {value, abs} {unit} vähemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value, abs} {unit} vähemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} vähemmän kuin Yhdysvalloissa
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value < 0

fi: [{location, case=ssa},] {value_type} oli sama kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli sama kuin EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} sama kuin EU:n keskiarvon
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

fi: [{location, case=gen}] {value_type} oli {value, ord} korkein [{time, case=ssa}]
fi: [{location, case=gen}] se oli {value, ord} korkein [{time, case=ssa}]
fi-head: [{time, case=ssa}] [[{location, case=ssa}] {value, ord} korkein {value_type}
| value_type = cphi:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

fi: [{location, case=gen}] {value_type} oli {value, ord} matalin [{time, case=ssa}]
fi: [{location, case=gen}] se oli {value, ord} matalin [{time, case=ssa}]
fi-head: [{time, case=ssa}] [[{location, case=ssa}] {value, ord} matalin {value_type}
| value_type = cphi:.*:rank_reverse.*
"""

INDEX_CATEGORIES: Dict[str, str] = {
    "hicp2015": "kuluttajahintaindeksi",  # harmonized consumer price index (2015=100)
    "rt1": "kuukausittainen kasvu",  # growth rate on previous period (t/t-1)
    "rt12": "vuosittainen kasvu",  # growth rate (t/t-12)
    "cp-hi00": "'kaikki osiot'",
    "cp-hi01": "'ruoka ja alkoholittomat juomat'",
    "cp-hi02": "'alkoholi ja tupakka'",
    "cp-hi03": "'vaattete ja jalkineet'",
    "cp-hi04": "'asuminen, vesi, sähkö ja lämmitys'",
    "cp-hi05": "'huonekalut, talousesineet ja kunnossapito'",
    "cp-hi06": "'terveys'",
    "cp-hi07": "'liikenne'",
    "cp-hi08": "'viestintä'",
    "cp-hi09": "'vapaa-aika ja kulttuuri'",
    "cp-hi10": "'koulutus'",
    "cp-hi11": "'hotellit, kahvilat ja ravintolat'",
    "cp-hi12": "'sekalaiset'",
    "cp-hi00xef": "'kaikki paitsi energia, ruoka, alkoholi ja tupakka'",
    "cp-hi00xtb": "'kaikki paitsi tupakka'",
    "cp-hie": "'energia'",
    "cp-hif": "'ruoka'",
    "cp-hifu": "'prosessoimaton ruoka'",
    "cp-hig": "'kaikki tavarat'",
    "cp-hiig": "'teollisuuden tavarat'",
    "cp-his": "'kaikki palvelut'",
    "cp-hiigxe": "'teolliset tavarat pl. energia'",
    "cp-hi00xe": "'kaikki pl. energia'",
    "cp-hi00xefu": "'kaikki paitsi energia ja prosessoimaton ruoka'",
    "cp-hi00xes": "'kaikki paitsi energia ja kausikausiluontoinen ruoka'",
}


class CPHIFinnishResource(TabularDataResource):
    def __init__(self):
        super().__init__(["fi"], ["cphi"])
        self.templates = TEMPLATES
        self.partials = INDEX_CATEGORIES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            FinnishCphiRawRealizer,
            FinnishCphiChangeRealizer,
            FinnishCphiCategoryRealizer,
            FinnishUnitCphiPercentageRealizer,
            FinnishUnitCphiPointsRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class FinnishCphiRawRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(registry, "fi", r"^cphi:([^:]*):([^:]*)" + MAYBE_RANK_OR_COMP + "$", "{} kategoriassa {}")


class FinnishCphiChangeRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "fi",
            r"^cphi:([^:]*):([^:]*):(rt12?)" + MAYBE_RANK_OR_COMP + "$",
            "{2} kuluttajahintaindeksissä {1}",
        )


class FinnishUnitCphiPercentageRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "fi",
            r"^\[UNIT:cphi:.*\]$",
            "prosenttiyksikköä",
            slot_requirements=lambda slot: "rt1" in slot.value.split(":") or "rt12" in slot.value.split(":"),
        )


class FinnishUnitCphiPointsRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "fi",
            r"^\[UNIT:cphi:.*\]$",
            "yksikköä",
            slot_requirements=lambda slot: "rt1" not in slot.value.split(":") and "rt12" not in slot.value.split(":"),
        )


class FinnishCphiCategoryRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "fi", INDEX_CATEGORIES)

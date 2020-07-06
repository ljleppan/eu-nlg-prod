from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

fi: [{location, case=ssa},] {value_type} oli {value} {unit} [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} oli {value} {unit}
| value_type = health:cost:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

fi: [{location, case=ssa},] {value_type} oli {value} {unit} enemmän kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} yli EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} yli EU:n keskiarvon
| value_type = health:cost:.*:comp_eu, value_type != .*:rank.*, value > 0

fi: [{location, case=ssa},] {value_type} oli {value} {unit} vähemmän kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} ali EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} ali EU:n keskiarvon
| value_type = health:cost:.*:comp_eu, value_type != .*:rank.*, value < 0

fi: [{location, case=ssa},] {value_type} oli sama kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli sama kuin EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} sama kuin EU:n keskiarvon
| value_type = health:cost:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

fi: [{location, case=ssa},] {value_type} oli {value} {unit} enemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value} {unit} enemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} oli {value} {unit} yli EU:n keskiarvon
| value_type = health:cost:.*:comp_us, value_type != .*:rank.*, value > 0

fi: [{location, case=ssa},] {value_type} oli {value, abs} {unit} vähemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi: [{location, case=ssa},] se oli {value, abs} {unit} vähemmän kuin Yhdysvalloissa [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} vähemmän kuin Yhdysvalloissa
| value_type = health:cost:.*:comp_us, value_type != .*:rank.*, value < 0

fi: [{location, case=ssa},] {value_type} oli sama kuin EU:n keskiarvo [{time, case=ssa}]
fi: [{location, case=ssa},] se oli sama kuin EU:n keskiarvon [{time, case=ssa}]
fi-head: {location, case=ssa}, {time, case=ssa}, {value_type} sama kuin EU:n keskiarvon
| value_type = health:cost:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

fi: [{location, case=gen}] {value_type} oli {value, ord} korkein [{time, case=ssa}]
fi: [{location, case=gen}] se oli {value, ord} korkein [{time, case=ssa}]
fi-head: [{time, case=ssa}] [[{location, case=ssa}] {value, ord} korkein {value_type}
| value_type = health:cost:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

fi: [{location, case=gen}] {value_type} oli {value, ord} matalin [{time, case=ssa}]
fi: [{location, case=gen}] se oli {value, ord} matalin [{time, case=ssa}]
fi-head: [{time, case=ssa}] [[{location, case=ssa}] {value, ord} matalin {value_type}
| value_type = health:cost:.*:rank_reverse.*
"""

PARTIALS: Dict[str, str] = {
    "tot-hc": "terveydenhuollon kokonaiskustannus",
    "hc1-2": "parantavan ja kuntouttavan hoidon hinta",
    "hc1": "parantavan hoidon hinta",
    "hc11-21": "laitos- ja kuntouttavan hoidon hinta",
    "hc11": "parantavan laitoshoidon hinta",
    "hc12-22": "parantavan ja kuntoittavan päivittäishoidon hinta",
    "hc12": "parantavan päivittäishoidon hinta",
    "hc13-23": "parantavan ja kuntoittavan avohoidon hinta",
    "hc13": "parantavan avohoidon hinta",
    "hc131": "yleisen parantavan avohoidon hinta",
    "hc132": "parantavan avohammashuollon hinta",
    "hc133": "erikoistuneen parantavan avohoidon hinta",
    "hc139": "muun parantavan avohoidon hinta",
    "hc14-24": "parantavan ja kuntoittavan kotihoidon hinta",
    "hc14": "parantavan kotihoidon hinta",
    "hc2": "kuntouttavan hoidon hinta",
    "hc21": "kuntouttavan laitoshuollon hinta",
    "hc22": "kuntouttavan päivittäishoidon hinta",
    "hc23": "kuntouttavan avohoidon hinta",
    "hc24": "kuntouttavan kotihoidon hinta",
    "hc3": "pitkäjänteisen terveydenhuollon hinta",
    "hc31": "pitkäjänteisen laitosterveydenhuollon hinta",
    "hc32": "pitkäjänteisen päivittäisterveydenhuollon hinta",
    "hc33": "pitkäjänteisen avohuollon hinta",
    "hc34": "pitkäjänteisen kotihoidon hinta",
    "hc4": "tukevien lääkintäpalveluiden hinta",
    "hc41": "laboratoriopalveuiden hinta",
    "hc42": "kuvantamispalveluiden hinta",
    "hc43": "potilassiirtojen hinta",
    "hc5": "lääkintätarvikkeiden hinta",
    "hc51": "lääkkeiden ja muiden kertakäyttöisten välineiden hinta",
    "hc511": "reseptilääkkeiden hinta",
    "hc512": "reseptivapaiden lääkkeiden hinta",
    "hc513": "lääkinnällisten kertakäyttövälineiden hinta",
    "hc52": "terapiavälineiden ja muiden kestotuotteiden hinta",
    "hc6": "ennaltaestävän terveydenhuollon hinta",
    "hc61": "tiedotus-, koulutus- ja neuvontapalveluiden hinta",
    "hc62": "rokotusohjelmien hinta",
    "hc63": "tautien aikaisen havaitsemisen ohjelmien hinta",
    "hc64": "terveystilan seurantapalveuiden hinta",
    "hc65": "epidemologisen seurannnan sekä riskien ja tautien ehkäisyn hinta",
    "hc66": "suuronnettomuus- ja onnettomuusvarautumisen hinta",
    "hc7": "lääke-, kustannus- ja hoitopalveluiden hallintokulut",
    "hc71": "terveydenhuollon hallintokulut",
    "hc72": "terveydenhuollon rahoitushallinnon kulut",
    "hc-unk": "muiden, tuntemattomien palveuiden hinta",
    "hcr1": "pitkäaikaisen sosiaalihuollon hinta",
}


UNITS: Dict[str, str] = {
    "[UNIT:health:cost:mio-eur]": "miljoonaa euroa",
    "[UNIT:health:cost:eur-hab]": "euroa per asukas",
    "[UNIT:health:cost:mio-nac]": "miljoonaa paikallisessa valuutassa",
    "[UNIT:health:cost:nac-hab]": "paikallista valuuttayksikköä per asukas",
    "[UNIT:health:cost:mio-pps]": "miljoonaa ostovoimastandardia (OVS)",
    "[UNIT:health:cost:pps-hab]": "ostovoimastandaria (OVS) per asukas",
    "[UNIT:health:cost:pc-gdp]": "prosenttia bruttokansantuotteesta",
    "[UNIT:health:cost:pc-che]": "prosenttia terveydenhuollon kokonaismenoista",
}


class HealthCostFinnishResource(TabularDataResource):
    def __init__(self):
        super().__init__(["fi"], ["health_cost"])
        self.templates = TEMPLATES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            FinnishHealthCostRawRealizer,
            FinnishHealthCostUnitSimplifier,
            FinnishHealthCostUnitRealizer,
            FinnishHealthCostPartialRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class FinnishHealthCostRawRealizer(RegexRealizer):
    def __init__(self, registry):
        # "the harmonized consumer price index for the category 'health'
        super().__init__(registry, "fi", r"^health:cost:([^:]*):?.*" + MAYBE_RANK_OR_COMP + "$", "{}")


class FinnishHealthCostUnitSimplifier(RegexRealizer):
    def __init__(self, registry):
        # "the monthly growth rate of the harmonized consumer price index for the category 'health'
        super().__init__(
            registry, "fi", r"^\[UNIT:health:cost:[^:]*:([^:]*):?.*\]$", "[UNIT:health:cost:{}]",
        )


class FinnishHealthCostUnitRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "fi", UNITS)


class FinnishHealthCostPartialRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "fi", PARTIALS)

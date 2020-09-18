from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

hr: [U {location, case=loc}] [{time, case=ssa}] {value_type} bio na {value} {unit}
hr: [U {location, case=loc}] [{time, case=ssa}] bilo je {value} {unit}
hr-head: U {location, case=loc}, {time, case=ssa}, {value_type} bio na {value} {unit}
| value_type = cphi:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

hr: [U {location, case=loc}] [{time, case=ssa}] {value_type} bio {value} {unit} više od prosjeka EU
hr: [U {location, case=loc}] [{time, case=ssa}] bio je {value} {unit} više od prosjeka EU
hr-head: U {location, case=loc} {time, case=ssa} {value_type} bio {value} {unit} više od prosjeka EU
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value > 0

hr: [U {location, case=loc}] [{time, case=ssa}] {value_type} bio {value, abs} {unit} ispod prosjeka EU
hr: [U {location, case=loc}] [{time, case=ssa}] bio je {value, abs} {unit} ispod prosjeka EU
hr-head: U {location, case=loc} {time, case=ssa} {value_type} bio {value, abs} {unit} ispod prosjeka EU
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value < 0

hr: [U {location, case=loc}] [{time, case=ssa}] {value_type} bio isti kao prosjeka EU
hr: [U {location, case=loc}] [{time, case=ssa}] bio je isti kao prosjeka EU
hr-head: U {location, case=loc} {time, case=ssa} {value_type} bio isti kao prosjeka EU
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

hr: [U {location, case=loc}] [{time, case=ssa}] {value_type} bio {value} {unit} više od prosjeka američki
hr: [U {location, case=loc}] [{time, case=ssa}] bio je {value} {unit} više od prosjeka američki
hr-head: U {location, case=loc} {time, case=ssa} {value_type} bio {value} {unit} više od prosjeka američki
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value > 0

hr: [U {location, case=loc}] [{time, case=ssa}] {value_type} bio {value, abs} {unit} ispod prosjeka američki
hr: [U {location, case=loc}] [{time, case=ssa}] bio je {value, abs} {unit} ispod prosjeka američki
hr-head: U {location, case=loc} {time, case=ssa} {value_type} bio {value, abs} {unit} ispod prosjeka američki
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value < 0

hr: [U {location, case=loc}] [{time, case=ssa}] {value_type} bio isti kao prosjeka američki
hr: [U {location, case=loc}] [{time, case=ssa}] bio je isti kao prosjeka američki
hr-head: U {location, case=loc} {time, case=ssa} {value_type} bio isti kao prosjeka američki
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

hr: [U {location, case=loc}] [{time, case=ssa}] {value_type} bio {value, ord} najviši
hr: [U {location, case=loc}] [{time, case=ssa}] bio je {value, ord} najviši
hr-head: [U {location, case=gen}] [{time, case=ssa}] {value_type} bio {value, ord} najviši
| value_type = cphi:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

hr: [U {location, case=loc}] [{time, case=ssa}] {value_type} bio {value, ord} najniži
hr: [U {location, case=loc}] [{time, case=ssa}] bio je {value, ord} najniži
hr-head: [U {location, case=loc}] [{time, case=ssa}] {value_type} bio {value, ord} najniži
| value_type = cphi:.*:rank_reverse.*
"""

INDEX_CATEGORIES: Dict[str, str] = {
    "hicp2015": "usklađeni indeks potrošačkih cijena",  # harmonized consumer price index (2015=100)
    "rt1": "stopa rasta u odnosu na prethodni mjesec",  # growth rate on previous period (t/t-1)
    "rt12": "stopa rasta u odnosu na prethodnu godinu",  # growth rate (t/t-12)
    "cp-hi00": "'svih predmeta'",
    "cp-hi01": "'hrana i bezalkoholna pića'",
    "cp-hi02": "'alkoholna pića i duhan'",
    "cp-hi03": "'odjeća i obuća'",
    "cp-hi04": "'kućište, voda, električna energija, plin i druga goriva'",
    "cp-hi05": "'namještaj, oprema za kućanstvo i održavanje'",
    "cp-hi06": "'zdravlje'",
    "cp-hi07": "'prijevoz'",
    "cp-hi08": "'komunikacija'",
    "cp-hi09": "'rekreacija i kultura'",
    "cp-hi10": "'obrazovanje'",
    "cp-hi11": "'hoteli, kafići i restorani'",
    "cp-hi12": "'razne robe i usluge'",
    "cp-hi00xef": "'svih predmeta osim energije, hrane, alkohola i duhana'",
    "cp-hi00xtb": "'svih predmeta osim duhana'",
    "cp-hie": "'energija'",
    "cp-hif": "'hrana'",
    "cp-hifu": "'neobrađena hrana'",
    "cp-hig": "'ukupna roba'",
    "cp-hiig": "'industrijska roba'",
    "cp-his": "'ukupne usluge'",
    "cp-hiigxe": "'neenergetska industrijska roba'",
    "cp-hi00xe": "'svih predmeta osim energije'",
    "cp-hi00xefu": "'svih predmeta osim energije i neobrađene hrane'",
    "cp-hi00xes": "'svih predmeta osim energije i sezonske hrane'",
}


class CPHICroatianResource(TabularDataResource):
    def __init__(self):
        super().__init__(["hr"], ["cphi"])
        self.templates = TEMPLATES
        self.partials = INDEX_CATEGORIES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            CroatianCphiRawRealizer,
            CroatianCphiChangeRealizer,
            CroatianCphiCategoryRealizer,
            CroatianUnitCphiPercentageRealizer,
            CroatianUnitCphiPointsRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class CroatianCphiRawRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry, "hr", r"^cphi:([^:]*):([^:]*)" + MAYBE_RANK_OR_COMP + "$", "{} je za cijenovnu kategoriju {}"
        )


class CroatianCphiChangeRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "hr",
            r"^cphi:([^:]*):([^:]*):(rt12?)" + MAYBE_RANK_OR_COMP + "$",
            "{2} indeksa potrošačkih cijena {1}",
        )


class CroatianUnitCphiPercentageRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "hr",
            r"^\[UNIT:cphi:.*\]$",
            "postotnih bodova",
            slot_requirements=lambda slot: "rt1" in slot.value.split(":") or "rt12" in slot.value.split(":"),
        )


class CroatianUnitCphiPointsRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "hr",
            r"^\[UNIT:cphi:.*\]$",
            "bodova",
            slot_requirements=lambda slot: "rt1" not in slot.value.split(":") and "rt12" not in slot.value.split(":"),
        )


class CroatianCphiCategoryRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "hr", INDEX_CATEGORIES)

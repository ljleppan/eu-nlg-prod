from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

ee: [{location, case=ssa}] oli  {value_type} {value} {unit} [{time, case=ssa}]
ee: [{location, case=ssa}] see oli {value} {unit}  [{time, case=ssa}]
ee-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit}
| value_type = cphi:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

ee: [{location, case=ssa}] oli {value_type} {value} {unit} üle EL-i keskmise [{time, case=ssa}]
ee: [{location, case=ssa}] see oli {value} {unit} üle EL-i keskmise [{time, case=ssa}]
ee-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} üle EL-i keskmise
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value > 0

ee: [{location, case=ssa}] {value_type} oli {value} {unit} võrra madalam EL-i keskmisest
ee: [{location, case=ssa}] see oli {value} {unit} võrra madalam EL-i keskmisest
ee-head: {location, case=ssa} {time, case=ssa} {value_type} {value} {unit} võrra madalam EL-i keskmisest
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value < 0

ee: [{location, case=ssa}] {value_type} oli sama, mis EL-i keskmine [{time, case=ssa}]
ee: [{location, case=ssa}] see oli sama, mis EL-i keskmine [{time, case=ssa}]
ee-head:  {location, case=ssa} {time, case=ssa} {value_type} sama, mis EL-i keskmine
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

ee: [{location, case=ssa}] oli {value_type} {value} {unit} võrra USA-st kõrgem [{time, case=ssa}]
ee: [{location, case=ssa}] see oli {value} {unit} võrra USA-st kõrgem [{time, case=ssa}]
ee-head: {location, case=ssa}, {time, case=ssa}, {value_type} {value} {unit} võrra USA-st kõrgem
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value > 0

ee: [{location, case=ssa}] {value_type} oli {value} {unit} võrra USA-st madalam
ee: [{location, case=ssa}] see oli {value} {unit} võrra USA-st madalam
ee-head: {location, case=ssa} {time, case=ssa} {value_type} {value} {unit} võrra USA-st madalam.
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value < 0

ee: [{location, case=ssa}] {value_type} oli USA-ga sama [{time, case=ssa}]
ee: [{location, case=ssa}] see oli USA-ga sama [{time, case=ssa}]
ee-head:  {location, case=ssa} {time, case=ssa} {value_type} USA-ga sama
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# RANK

ee: [{location, case=gen}] {value_type} oli {value, ord} suuruselt [{time, case=ssa}]
ee: [{location, case=gen}] see oli {value, ord} suuruselt [{time, case=ssa}]
ee-head: [{time, case=ssa}] [[{location, case=ssa}] {value, ord} suuruselt {value_type}
| value_type = cphi:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

ee: [{location, case=gen}] {value_type} oli {value, ord} madalaim [{time, case=ssa}]
ee: [{location, case=gen}] see oli {value, ord} madalaim [{time, case=ssa}]
ee-head: [{time, case=ssa}] [[{location, case=ssa}] {value, ord} madalaim {value_type}
| value_type = cphi:.*:rank_reverse.*
"""

INDEX_CATEGORIES: Dict[str, str] = {
    "hicp2015": "harmoniseeritud tarbijahinnaindeks",  # harmonized consumer price index (2015=100)
    "rt1": "igakuine kasvumäär", # eelmiseperioodi kasvumäär (t/t-1)
    "rt12": "iga-aastane kasvumäär", # kasvumäär (t/t-12)
    "cp-hi00": "'kõik tooted'",
    "cp-hi01": "'toit ja mittealkohoolsed joogid'",
    "cp-hi02": "'alkohoolsed joogid ja tubakas'",
    "cp-hi03": "'riided ja jalanõud'",
    "cp-hi04": "'eluase, vesi, elekter, bensiin ja teised kütused'",
    "cp-hi05": "'sisustus, majapidamistarbed ja -hooldus'",
    "cp-hi06": "'tervis'",
    "cp-hi07": "'transport'",
    "cp-hi08": "'kommunikatsioon'", #I guess it can also be "'side'
    "cp-hi09": "'vaba aeg ja kultuur'",
    "cp-hi10": "'haridus'",
    "cp-hi11": "'hotellid, kohvikud ja restoranid'",
    "cp-hi12": "'mitmesugused kaubad ja teenused'",
    "cp-hi00xef": "'kõik tooted, v.a energia, toit, alkohol ja tubakas'",
    "cp-hi00xtb": "'kõik tooted, v.a tubakas'",
    "cp-hie": "'energia'",
    "cp-hif": "'toit'",
    "cp-hifu": "'töötlemata toit'",
    "cp-hig": "'kõik kaubad'",
    "cp-hiig": "'tööstuskaubad'",
    "cp-his": "'kõik teenused'",
    "cp-hiigxe": "'tööstuskaubad (v.a energia)'",
    "cp-hi00xe": "'kõik kaubad, v.a energia'",
    "cp-hi00xefu": "'kõik kaubad, v.a energia ja töötlemata toit'",
    "cp-hi00xes": "'kõik kaubad, v.a energia ja hooajaline toit'",
}


class CPHIEstonianResource(TabularDataResource):
    def __init__(self):
        super().__init__(["ee"], ["cphi"])
        self.templates = TEMPLATES
        self.partials = INDEX_CATEGORIES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            EstonianCphiRawRealizer,
            EstonianCphiChangeRealizer,
            EstonianCphiCategoryRealizer,
            EstonianUnitCphiPercentageRealizer,
            EstonianUnitCphiPointsRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class EstonianCphiRawRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(registry, "ee", r"^cphi:([^:]*):([^:]*)" + MAYBE_RANK_OR_COMP + "$", "{} kategoorias {}")


class EstonianCphiChangeRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "ee",
            r"^cphi:([^:]*):([^:]*):(rt12?)" + MAYBE_RANK_OR_COMP + "$",
            "{2} {0} kategoorias {1}",
        )


class EstonianUnitCphiPercentageRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "ee",
            r"^\[UNIT:cphi:.*\]$",
            "protsendipunktid",
            slot_requirements=lambda slot: "rt1" in slot.value.split(":") or "rt12" in slot.value.split(":"),
        )


class EstonianUnitCphiPointsRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "ee",
            r"^\[UNIT:cphi:.*\]$",
            "punktid",
            slot_requirements=lambda slot: "rt1" not in slot.value.split(":") and "rt12" not in slot.value.split(":"),
        )


class EstonianCphiCategoryRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "ee", INDEX_CATEGORIES)

from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

sl: [{time, case=loct}] {value_type} [{location, case=loct}] je znašala {value} {unit}
sl-head: {location, case=loct} {time, case=loct} {value_type} znašala {value} {unit}
| value_type = cphi:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

sl: [{time, case=loct}] [{location, case=loct}] je bila {value_type} {value} {unit} večja od povprečja EU
sl-head: {location, case=loct} {time, case=loct} je bila {value_type} {value} {unit} večja od povprečja EU
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value > 0

sl: [{time, case=loct}] [{location, case=loct}] je bila {value_type} za {value, abs} {unit} nižja od povprečja EU
sl-head: {location, case=loct} {time, case=loct} {value_type} za {value, abs} {unit} manjša od povprečja EU.
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value < 0

sl: [{time, case=loct}] [{location, case=loct}] {value_type} enaka povprečju EU
sl-head: {location, case=loct} {time, case=loct} {value_type} enaka povprečju EU
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

sl: [{time, case=loct}] [{location, case=loct}] je bila {value_type} za {value} {unit} večja kot v ZDA
sl-head: {location, case=loct} {time, case=loct} {value_type} za {value} {unit} večja kot v ZDA
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value > 0

sl: [{time, case=loct}] [{location, case=loct}] je bila {value_type} za {value, abs} {unit} nižja kot v ZDA
sl-head: v {location, case=loct} {time, case=loct}, {value_type} za {value, abs} {unit} manjša kot v ZDA
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value < 0

sl: [{time, case=loct}] [{location, case=loct}] {value_type} enaka kot v ZDA
sl-head: {location, case=loct} в {time, case=loct} {value_type} enaka kot v ZDA
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

sl: [{time, case=loct}] {location} je {"imela", gendered=previous_word} {value, ord} največjo {value_type} v vseh opazovanih državah
sl: [{time, case=loct}] {location} je {"imela", gendered=previous_word} {value, ord} največjo vrednost v vseh opazovanih državah
sl-head: {time, case=loct} {location} je {"imela", gendered=previous_word} {value, ord} največjo {value_type}
| value_type = cphi:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

sl: [{time, case=loct}] {location} je {"imela", gendered=previous_word} {value, ord} najnižjo {value_type} v vseh opazovanih državah
sl: [{time, case=loct}] {location} {"imela", gendered=previous_word} {value, ord} najnižjo vrednost v vseh opazovanih državah
sl-head: {time, case=loct} {location} je {"imela", gendered=previous_word} {value, ord} najnižjo {value_type}
| value_type = cphi:.*:rank_reverse.*
"""  # noqa: E501

INDEX_CATEGORIES: Dict[str, str] = {
    "hicp2015": "usklajenega indeksa cen življenjskih potrebščin",
    "rt1": "mesečna stopnja rasti",
    "rt12": "letna stopnja rasti",
    "cp-hi00": "'vsi izdelki'",
    "cp-hi01": "'hrana in brezalkoholne pijače'",
    "cp-hi02": "'alkoholne pijače in tobak'",
    "cp-hi03": "'oblačila in obutev'",
    "cp-hi04": "'stanovanja, voda, elektrika, plin in druga goriva'",
    "cp-hi05": "'pohištvo, gospodinjska oprema in vzdrževanje'",
    "cp-hi06": "'zdravje'",
    "cp-hi07": "'transport'",
    "cp-hi08": "'komunikacija'",
    "cp-hi09": "'rekreacija in kultura'",
    "cp-hi10": "'izobraževanje'",
    "cp-hi11": "'hoteli, kavarne in restavracije'",
    "cp-hi12": "'razno blago in storitve'",
    "cp-hi00xef": "'vsi izdelki razen energije, hrane, alkohola in tobaka'",
    "cp-hi00xtb": "'vsi izdelki razen tobaka'",
    "cp-hie": "'energija'",
    "cp-hif": "'hrana'",
    "cp-hifu": "'nepredelana hrana'",
    "cp-hig": "'vse blago'",
    "cp-hiig": "'industrijsko blago'",
    "cp-his": "'vse storitve'",
    "cp-hiigxe": "'neenergetsko industrijsko blago'",
    "cp-hi00xe": "'vsi artikli razen energije'",
    "cp-hi00xefu": "'vsi artikli razen energije in nepredelane hrane'",
    "cp-hi00xes": "'vsi artikli razen energije in sezonske hrane'",
}


class CPHISlovenianResource(TabularDataResource):
    def __init__(self):
        super().__init__(["sl"], ["cphi"])
        self.templates = TEMPLATES
        self.partials = INDEX_CATEGORIES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            SlovenianCphiRawRealizer,
            SlovenianCphiChangeRealizer,
            SlovenianCphiCategoryRealizer,
            SlovenianUnitCphiPercentageRealizer,
            SlovenianUnitCphiPointsRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class SlovenianCphiRawRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(registry, "sl", r"^cphi:([^:]*):([^:]*)" + MAYBE_RANK_OR_COMP + "$", "{} za kategorijo {}")


class SlovenianCphiChangeRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry, "sl", r"^cphi:([^:]*):([^:]*):(rt12?)" + MAYBE_RANK_OR_COMP + "$", "{2} od {0} za kategorijo {1}",
        )


class SlovenianUnitCphiPercentageRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "sl",
            r"^\[UNIT:cphi:.*\]$",
            "procentne točke",
            slot_requirements=lambda slot: "rt1" in slot.value.split(":") or "rt12" in slot.value.split(":"),
        )


class SlovenianUnitCphiPointsRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "sl",
            r"^\[UNIT:cphi:.*\]$",
            "točke",
            slot_requirements=lambda slot: "rt1" not in slot.value.split(":") and "rt12" not in slot.value.split(":"),
        )


class SlovenianCphiCategoryRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "sl", INDEX_CATEGORIES)

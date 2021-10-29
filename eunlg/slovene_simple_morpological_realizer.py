import logging
from typing import Optional, List, Dict

from core.models import Slot, TemplateComponent
from core.morphological_realizer import LanguageSpecificMorphologicalRealizer

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

VOWELS = "aeiouyAEIOUY"

LOC_MAP: Dict[str, str] = {
    "Evroobmočje (v tistem trenutku)": "v Evroobmočju (v tistem trenutku)",
    "Evroobmočje (19 držav)": "v Evroobmočju (19 držav)",
    "Evroobmočje (18 držav)": "v Evroobmočju (18 držav)",
    "Evropska unija (v tistem trenutku)": "v Evropski uniji (v tistem trenutku)",
    "Evropska unija (28 držav)": "v Evropski uniji (28 držav)",
    "Bosna in Hercegovina": "v Bosni in Hercegovini",
    "Belgija": "v Belgiji",
    "Bolgarija": "v Bolgariji",
    "Češka": "na Češkem",
    "Danska": "na Danskem",
    "Nemčija": "v Nemčiji",
    "Estonija": "v Estoniji",
    "Irska": "na Irskem",
    "Grčija": "v Grčiji",
    "Španija": "v Španiji",
    "Francija": "v Franciji",
    "Hrvaška": "na Hrvaškem",
    "Italija": "v Italiji",
    "Ciper": "na Cipru",
    "Liechtenstein": "v Lihtenštajnu",
    "Latvija": "v Latviji",
    "Litva": "v Litvi",
    "Luksemburg": "v Luksemburgu",
    "Madžarska": "na Madžarskem",
    "Malta": "na Malti",
    "Nizozemska": "na Nizozemskem",
    "Avstrija": "v Avstriji",
    "Poljska": "na Poljskem",
    "Portugalska": "na Portugalskem",
    "Romunija": "v Romuniji",
    "Slovenija": "v Sloveniji",
    "Slovaška": "na Slovaškem",
    "Finska": "na Finskem",
    "Švedska": "na Švedskem",
    "Združeno kraljestvo": "v Združenem kraljestvu",
    "Islandija": "na Islandiji",
    "Norveška": "na Norveškem",
    "Švica": "v Švici",
    "Severna Makedonija": "v Severni Makedoniji",
    "Srbija": "v Srbiji",
    "Turčija": "v Turčiji",
    "Združene države": "v Združenih državah",
}


class SlovenianSimpleMorphologicalRealizer(LanguageSpecificMorphologicalRealizer):
    def __init__(self):
        super().__init__("sl")

    def realize(self, slot: Slot, left_context: List[TemplateComponent], right_context: List[TemplateComponent]) -> str:
        case: Optional[str] = slot.attributes.get("case")
        if case is None:
            return slot.value

        log.debug("Realizing {} to Slovenian".format(slot.value))
        if case == "loct":
            if slot.value in LOC_MAP:
                log.debug(f"Found item in LOC_MAP, realizing as such '{LOC_MAP.get(slot.value)}'")
                return LOC_MAP.get(slot.value)
            else:
                log.debug("Item not in LOC_MAP, leaving as-is")
                return slot.value

        log.debug("Had either no case or something weird, just ignore")
        return slot.value

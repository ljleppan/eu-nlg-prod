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


REV_LOC = {v: k for k, v in LOC_MAP.items()}


GENDER: Dict[str, str] = {
    "Evroobmočje (v tistem trenutku)": "nt",
    "Evroobmočje (19 držav)": "nt",
    "Evroobmočje (18 držav)": "nt",
    "Evropska unija (v tistem trenutku)": "f)",
    "Evropska unija (28 držav)": "f",
    "Bosna in Hercegovina": "f",
    "Belgija": "f",
    "Bolgarija": "f",
    "Češka": "f",
    "Danska": "f",
    "Nemčija": "f",
    "Estonija": "f",
    "Irska": "f",
    "Grčija": "f",
    "Španija": "f",
    "Francija": "f",
    "Hrvaška": "f",
    "Italija": "f",
    "Ciper": "m",
    "Liechtenstein": "f",
    "Latvija": "f",
    "Litva": "f",
    "Luksemburg": "m",
    "Madžarska": "f",
    "Malta": "f",
    "Nizozemska": "f",
    "Avstrija": "f",
    "Poljska": "f",
    "Portugalska": "f",
    "Romunija": "f",
    "Slovenija": "f",
    "Slovaška": "f",
    "Finska": "f",
    "Švedska": "f",
    "Združeno kraljestvo": "f",
    "Islandija": "f",
    "Norveška": "f",
    "Švica": "f",
    "Severna Makedonija": "f",
    "Srbija": "f",
    "Turčija": "f",
    "Združene države": "m",
}


class SlovenianSimpleMorphologicalRealizer(LanguageSpecificMorphologicalRealizer):
    def __init__(self):
        super().__init__("sl")

    def realize(self, slot: Slot, left_context: List[TemplateComponent], right_context: List[TemplateComponent]) -> str:
        case: Optional[str] = slot.attributes.get("case")
        gendered: Optional[str] = slot.attributes.get("gendered")

        if case is None and gendered is None:
            return slot.value

        log.debug("Realizing {} to Slovenian".format(slot.value))

        if case == "loct":
            if slot.value in LOC_MAP:
                log.debug(f"Found item in LOC_MAP, realizing as such '{LOC_MAP.get(slot.value)}'")
                return LOC_MAP.get(slot.value)
            else:
                log.debug("Item not in LOC_MAP, leaving as-is")
                return slot.value

        if gendered == "previous_word" and slot.value == "imela":
            log.debug(f"Found gendered word '{slot.value}'")
            for left_slot in left_context[::-1]:
                word = left_slot.value
                log.debug(f"Checking word {word} to find the word that closest NP")
                word = REV_LOC.get(word, word)  # Undo locative, if it was applied
                if word in GENDER:
                    gender = GENDER[word]
                    log.debug(f"Identified the operative previous word/phrase as '{word}'")
                    if word == "Združene države":  # special case, plural
                        modified = "imeli"
                    elif gender == "nt":
                        modified = "imelo"
                    elif gender == "m":
                        modified = "imel"
                    else:  # Feminine, and also a fallback for something weird
                        modified = "imela"
                    log.debug(f"Inflected form is '{modified}'")
                    return modified
        elif gendered:
            log.warning(f"Encountered word that needs gender agreement, but has no rules: '{slot.value}'")

        log.debug("Had either no case or something weird, just ignore")
        return slot.value

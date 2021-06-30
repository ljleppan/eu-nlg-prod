import logging
from typing import Optional, List

from core.models import Slot, TemplateComponent
from core.morphological_realizer import LanguageSpecificMorphologicalRealizer

log = logging.getLogger("root")

VOWELS = "aeiouyAEIOUY"


class CroatianSimpleMorphologicalRealizer(LanguageSpecificMorphologicalRealizer):
    def __init__(self):
        super().__init__("hr")

    def realize(self, slot: Slot, left_context: List[TemplateComponent], right_context: List[TemplateComponent]) -> str:
        case: Optional[str] = slot.attributes.get("case")
        if case is None:
            return slot.value

        log.debug("Realizing {} to Croatian".format(slot.value))

        if case == "loc":
            log.debug('Has case "loc", this we can handle.')
            if slot.value[-1] in VOWELS:
                if slot.value[-2] == "j":
                    new_value = slot.value[:-1] + "i"
                else:
                    new_value = slot.value[:-1] + "oj"
            else:
                new_value = slot.value + "u"
            log.debug("Realized as {}".format(new_value))
            return new_value

        log.debug("Had either no case or somehing weird, just ignore")
        return slot.value

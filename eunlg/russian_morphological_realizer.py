import logging
from typing import List

from core.models import Slot, TemplateComponent
from core.morphological_realizer import LanguageSpecificMorphologicalRealizer

import pymorphy2

log = logging.getLogger("root")


class RussianMorphologicalRealizer(LanguageSpecificMorphologicalRealizer):
    def __init__(self):
        super().__init__("ru")
        self.morph = pymorphy2.MorphAnalyzer()

    def realize(self, slot: Slot, left_context: List[TemplateComponent], right_context: List[TemplateComponent]) -> str:
        gender: Optional[str] = slot.attributes.get("gendered")
        if gender is not None:
            if gender == "previous_word":
                previous_word = left_context[-1]
                analysis = self.morph.parse(previous_word.value)[0]
                verb_analysis = self.morph.parse(slot.value)[0]
                if "femn" in analysis.tag:
                    modified_value = verb_analysis.inflect({"femn"}).word
                else:
                    modified_value = verb_analysis.inflect({"masc"}).word
                log.debug("Realizing {} to Russian".format(modified_value))
        else:
            modified_value = slot.value

        case: Optional[str] = slot.attributes.get("case")
        if case is not None:

            log.debug("Realizing {} to Russian".format(modified_value))

            possible_analyses = [
                analysis
                for analysis in self.morph.parse(modified_value)
                if "nomn" in analysis.tag
            ]

            log.debug("Identified {} possible analyses".format(len(possible_analyses)))
            if len(possible_analyses) == 0:
                log.warning(
                    "No valid morphological analysis for {}, unable to realize despite case attribute".format(modified_value)
                )
                return modified_value

            analysis = possible_analyses[0]
            log.debug("Picked {} as the morphological analysis of {}".format(analysis, modified_value))

            modified_value = analysis.inflect({case}).word

            if "Geox" in analysis.tag:
                modified_value = modified_value.capitalize()
            log.debug("Realized value is {}".format(modified_value))

        return modified_value


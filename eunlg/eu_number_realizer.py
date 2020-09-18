import logging
from abc import ABC, abstractmethod
from numbers import Number
from typing import Dict, Tuple, Union, cast

from numpy.random import Generator

from core.models import DocumentPlanNode, Slot
from core.pipeline import NLGPipelineComponent
from core.registry import Registry

log = logging.getLogger("root")


class EUNumberRealizer(NLGPipelineComponent):
    """
    A NLGPipelineComponent that realizers numbers.
    """

    def __init__(self):
        self.realizers = {
            "fi": {"car": FinnishCardinalRealizer(), "ord": FinnishOrdinalRealizer()},
            "en": {"car": EnglishCardinalRealizer(), "ord": EnglishOrdinalRealizer()},
            "hr": {"ord": CroatianOrdinalRealizer()},
            "de": {"car": GermanCardinalRealizer()},
        }

    def run(
        self, registry: Registry, random: Generator, language: str, document_plan: DocumentPlanNode
    ) -> Tuple[DocumentPlanNode]:
        """
        Run this pipeline component.
        """
        log.info("Realizing dates")

        if language.endswith("-head"):
            language = language[:-5]
            log.debug("Language had suffix '-head', removing. Result: {}".format(language))

        self._recurse(registry, random, language, document_plan)

        if log.isEnabledFor(logging.DEBUG):
            document_plan.print_tree()

        return (document_plan,)

    def _recurse(
        self, registry: Registry, random: Generator, language: str, this: DocumentPlanNode,
    ):
        """
        Traverses the DocumentPlan tree recursively in-order and modifies named
        entity to_value functions to return the chosen form of that NE's name.
        """
        language_specific_realizers = self.realizers.get(language, {})
        if isinstance(this, Slot):
            this = cast(Slot, this)
            if this.attributes and this.attributes.get("ord"):
                realizer = language_specific_realizers.get("ord")
                if not realizer:
                    log.error("Wanted to realize as ordinal '{}' but found no realizer.".format(this.value))
                else:
                    new_value = realizer.realize(this)
                    this.value = lambda x: new_value

        elif isinstance(this, DocumentPlanNode):
            log.debug("Visiting non-leaf '{}'".format(this))
            for child in this.children:
                self._recurse(registry, random, language, child)


class Realizer(ABC):
    @abstractmethod
    def realize(self, slot) -> str:
        """ Implemented in a subclass. """


class DictionaryRealizer(Realizer):
    def __init__(self, dictionary: Dict[str, str]):
        self.dictionary = dictionary

    def realize(self, slot: Slot) -> str:
        return self.dictionary.get(str(slot.value), str(slot.value))


class FinnishCardinalRealizer(DictionaryRealizer):
    def __init__(self):
        super(FinnishCardinalRealizer, self).__init__(
            {
                "1": "yksi",
                "2": "kaksi",
                "3": "kolme",
                "4": "neljä",
                "5": "viisi",
                "6": "kuusi",
                "7": "seitsemän",
                "8": "kahdeksan",
                "9": "yhdeksän",
                "10": "kymmenen",
            }
        )


class FinnishOrdinalRealizer(Realizer):
    SMALL_ORDINALS: Dict[str, str] = {
        "1": "ensimmäinen",
        "2": "toinen",
        "3": "kolmas",
        "4": "neljäs",
        "5": "viides",
        "6": "kuudes",
        "7": "seitsemäs",
        "8": "kahdeksas",
        "9": "yhdeksäs",
        "10": "kymmenes",
    }

    def realize(self, slot: Slot) -> str:
        return self.SMALL_ORDINALS.get(slot.value, "{}.".format(slot.value))


class EnglishCardinalRealizer(DictionaryRealizer):
    def __init__(self):
        super(EnglishCardinalRealizer, self).__init__(
            {
                "1": "one",
                "2": "two",
                "3": "three",
                "4": "four",
                "5": "five",
                "6": "six",
                "7": "seven",
                "8": "eight",
                "9": "nine",
                "10": "ten",
            }
        )


class EnglishOrdinalRealizer(Realizer):
    SMALL_ORDINALS: Dict[str, str] = {
        "1": "first",
        "2": "second",
        "3": "third",
        "4": "fourth",
        "5": "fifth",
        "6": "sixth",
        "7": "seventh",
        "8": "eighth",
        "9": "ninth",
        "10": "tenth",
        "11": "eleventh",
        "12": "twelfth",
    }

    def _get_suffix(self, value: Union[Number, str]) -> str:
        if value in [11, 12, 13]:
            return "th"
        elif str(value)[-1] == "1":
            return "st"
        elif str(value)[-1] == "2":
            return "nd"
        elif str(value)[-1] == "3":
            return "rd"
        else:
            return "th"

    def realize(self, slot: Slot) -> str:
        if str(slot.value) == "1":
            # Rather than saying "1st highest", it's sufficient to simply say "highest"
            return ""
        return self.SMALL_ORDINALS.get(slot.value, "{}{}".format(slot.value, self._get_suffix(slot.value)))


class GermanCardinalRealizer(DictionaryRealizer):
    def __init__(self):
        super(GermanCardinalRealizer, self).__init__(
            {
                "1": "eins",
                "2": "zwei",
                "3": "drei",
                "4": "vier",
                "5": "fünf",
                "6": "sechs",
                "7": "sieben",
                "8": "acht",
                "9": "neun",
                "10": "zehn",
                "11": "elf",
                "12": "zwölf",
            }
        )


class CroatianOrdinalRealizer(Realizer):
    def realize(self, slot: Slot) -> str:
        return "{}.".format(slot.value)

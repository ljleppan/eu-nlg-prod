import logging
import re
from typing import List, Optional, Tuple, Union

from numpy.random import Generator

from core.models import DocumentPlanNode, Slot
from core.pipeline import NLGPipelineComponent
from core.registry import Registry

log = logging.getLogger("root")


class EUDateRealizer(NLGPipelineComponent):
    """
    A NLGPipelineComponent that realizers dates.
    """

    def __init__(self, vocab):
        self.vocab = vocab

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

        self._recurse(registry, random, language, document_plan, None)

        if log.isEnabledFor(logging.DEBUG):
            document_plan.print_tree()

        return (document_plan,)

    def _recurse(
        self,
        registry: Registry,
        random: Generator,
        language: str,
        this: DocumentPlanNode,
        previous_entity: Optional[str],
    ) -> Optional[str]:
        """
        Traverses the DocumentPlan tree recursively in-order and modifies named
        entity to_value functions to return the chosen form of that NE's name.
        """
        if isinstance(this, Slot):
            if not isinstance(this.value, str) or this.value[0] != "[" or this.value[-1] != "]":
                log.debug("Visited non-tag leaf node {}".format(this.value))
                return previous_entity

            segments = this.value[1:-1].split(":")
            if segments[0] != "TIME":
                log.debug("Visited non-TIME leaf node {}".format(this.value))
                return previous_entity

            if segments[1] == "month":
                new_value = self._realize_month(this, previous_entity)
            elif segments[1] == "year":
                new_value = self._realize_year(this, previous_entity)
            else:
                log.error("Visited TIME leaf node {} but couldn't realize it!".format(this.value))
                return previous_entity

            if isinstance(new_value, list):
                new_value = random.choice(new_value)

            original_value = this.value
            this.value = lambda x: new_value
            log.debug("Visited TIME leaf node {} and realized it as {}".format(original_value, new_value))
            return original_value
        elif isinstance(this, DocumentPlanNode):
            log.debug("Visiting non-leaf '{}'".format(this))
            for child in this.children:
                previous_entity = self._recurse(registry, random, language, child, previous_entity)
            return previous_entity
        return previous_entity

    def _realize_month(self, this: Slot, previous: Optional[str]) -> Union[str, List[str]]:
        if previous is None:
            this_year, this_month = re.match(r"\[TIME:month:(\d+)M(\d+)\]", this.value).groups()
            return self.vocab["month-year-expression"].format(month=self.vocab["month"][this_month], year=this_year)

        if this.value == previous:
            return self.vocab["month"]["reference_options"]

        this_year, this_month = re.match(r"\[TIME:month:(\d+)M(\d+)\]", this.value).groups()

        prev_year = None
        if re.match(r"\[TIME:month:(\d+)M(\d+)\]", previous):
            prev_year = re.match(r"\[TIME:month:(\d+)M(\d+)\]", previous).groups(0)
        elif re.match(r"\[TIME:year:(\d+)\]", previous):
            prev_year = re.match(r"\[TIME:month:(\d+)\]", previous).groups()[0]

        if this_year == prev_year:
            return self.vocab["month-expression"].format(month=self.vocab["month"][this_month])
        else:
            return self.vocab["month-year-expression"].format(month=self.vocab["month"][this_month], year=this_year)

    def _realize_year(self, this: Slot, previous: str) -> Union[str, List[str]]:
        if previous and this.value == previous:
            return self.vocab["year"]["reference_options"]

        this_year = re.match(r"\[TIME:year:(\d+)\]", this.value).groups()[0]

        return self.vocab["year-expression"].format(year=this_year)


class EnglishEUDateRealizer(EUDateRealizer):
    def __init__(self):
        from resources.date_expression_resource import ENGLISH

        super().__init__(ENGLISH)


class CroatianEUDateRealizer(EUDateRealizer):
    def __init__(self):
        from resources.date_expression_resource import CROATIAN

        super().__init__(CROATIAN)


class GermanEUDateRealizer(EUDateRealizer):
    def __init__(self):
        from resources.date_expression_resource import GERMAN

        super().__init__(GERMAN)


class FinnishEUDateRealizer(EUDateRealizer):
    def __init__(self):
        from resources.date_expression_resource import FINNISH

        super().__init__(FINNISH)

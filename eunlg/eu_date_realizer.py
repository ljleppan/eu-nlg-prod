import logging
import re
from typing import Dict, List, Optional, Tuple, Union

from numpy.random import Generator

from core.models import DocumentPlanNode, Slot
from core.pipeline import NLGPipelineComponent
from core.registry import Registry

log = logging.getLogger("root")


class EUDateRealizer(NLGPipelineComponent):
    """
    A NLGPipelineComponent that realizers dates.
    """

    def __init__(self, vocab, attach_attributes_map: Optional[Dict[str, List[int]]] = None):
        self.vocab = vocab
        self.attach_attributes = attach_attributes_map

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
        idx = 0
        while idx < len(this.children):
            child = this.children[idx]
            if isinstance(child, Slot):
                if not isinstance(child.value, str) or child.value[0] != "[" or child.value[-1] != "]":
                    log.debug("Visited non-tag leaf node {}".format(child.value))
                    idx += 1
                    continue

                segments = child.value[1:-1].split(":")
                if segments[0] != "TIME":
                    log.debug("Visited non-TIME leaf node {}".format(child.value))
                    idx += 1
                    continue

                timestamp_type = segments[1]
                if timestamp_type == "month":
                    new_value = self._realize_month(child, previous_entity)
                elif timestamp_type == "year":
                    new_value = self._realize_year(child, previous_entity)
                else:
                    log.error("Visited TIME leaf node {} but couldn't realize it!".format(child.value))
                    idx + 1
                    continue

                if isinstance(new_value, list):
                    new_value = random.choice(new_value)

                original_value = child.value
                new_components = []
                for component_idx, realization_token in enumerate(new_value.split()):
                    new_slot = child.copy(include_fact=True)

                    # By default, copy copies the attributes too. In case attach_attributes_to was set,
                    # we need to explicitly reset the attributes for all those slots NOT explicitly mentioned
                    if (
                        self.attach_attributes
                        and timestamp_type in self.attach_attributes
                        and component_idx not in self.attach_attributes[timestamp_type]
                    ):
                        new_slot.attributes = {}

                    # An ugly hack that ensures the lambda correctly binds to the value of realization_token at this
                    # time. Without this, all the lambdas bind to the final value of the realization_token variable, ie.
                    # the final value at the end of the loop.  See https://stackoverflow.com/a/10452819
                    new_slot.value = lambda f, realization_token=realization_token: realization_token
                    new_components.append(new_slot)

                this.children[idx : idx + 1] = new_components
                idx += len(new_components)
                log.debug("Visited TIME leaf node {} and realized it as {}".format(original_value, new_value))
                previous_entity = original_value
            elif isinstance(child, DocumentPlanNode):
                log.debug("Visiting non-leaf '{}'".format(child))
                previous_entity = self._recurse(registry, random, language, child, previous_entity)
                idx += 1
            else:
                # Neither DocumentPlan nor Slot, must be f.ex. Literal -> skip.
                idx += 1
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

        super().__init__(FINNISH, {"month": [0], "year": [0]})

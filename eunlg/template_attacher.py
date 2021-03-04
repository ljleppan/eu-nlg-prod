import itertools
import logging
from typing import List

from numpy.random.mtrand import RandomState

from core.models import Message, DocumentPlanNode
from core.pipeline import NLGPipelineComponent
from core.realize_slots import SlotRealizer
from core.registry import Registry
from core.template_selector import TemplateSelector
from eu_named_entity_resolver import EUEntityNameResolver

log = logging.getLogger("root")


class TemplateAttacher(NLGPipelineComponent):
    def run(
        self,
        registry: Registry,
        random: RandomState,
        language: str,
        core_messages: List[Message],
        expanded_messages: List[Message],
    ):
        """
        Runs this pipeline component.
        """
        template_selector = TemplateSelector()
        slot_realizer = SlotRealizer()
        entity_name_resolver = EUEntityNameResolver()
        for msg in itertools.chain(core_messages, expanded_messages):
            doc_plan = DocumentPlanNode([msg])
            template_selector.run(registry, random, language, doc_plan, core_messages)
            slot_realizer.run(registry, random, language, doc_plan)
            entity_name_resolver.run(registry, random, language, doc_plan)

        return core_messages, expanded_messages

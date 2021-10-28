import itertools
import logging
from typing import List

from numpy.random.mtrand import RandomState

from core.models import Message, DocumentPlanNode
from core.pipeline import NLGPipelineComponent, LanguageSplitComponent
from core.realize_slots import SlotRealizer
from core.registry import Registry
from core.template_selector import TemplateSelector
from eu_date_realizer import EnglishEUDateRealizer, FinnishEUDateRealizer, CroatianEUDateRealizer, GermanEUDateRealizer
from eu_named_entity_resolver import EUEntityNameResolver
from eu_number_realizer import EUNumberRealizer

log = logging.getLogger(__name__)


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
        date_realizer = LanguageSplitComponent(
            {
                "en": EnglishEUDateRealizer(),
                "fi": FinnishEUDateRealizer(),
                "hr": CroatianEUDateRealizer(),
                "de": GermanEUDateRealizer(),
            }
        )
        number_realizer = EUNumberRealizer()
        entity_name_resolver = EUEntityNameResolver()

        root_logger = logging.getLogger()
        original_log_level = root_logger.level
        log.info(
            f"Setting root log level to WARNING (={logging.WARNING}) temporarily (was {original_log_level}), "
            f"because we're going to produce hella spam by running the first half of the pipeline at least a few "
            f"thousand times."
        )
        root_logger.setLevel(logging.WARNING)
        # i = 0
        # start = time.time()
        for msg in itertools.chain(core_messages, expanded_messages):
            doc_plan = DocumentPlanNode([msg])
            template_selector.run(registry, random, language, doc_plan, core_messages)
            slot_realizer.run(registry, random, language, doc_plan)
            date_realizer.run(registry, random, language, doc_plan)
            entity_name_resolver.run(registry, random, language, doc_plan)
            number_realizer.run(registry, random, language, doc_plan)

        root_logger.setLevel(original_log_level)
        log.info(f"Log level restored to {original_log_level}")
        return core_messages, expanded_messages

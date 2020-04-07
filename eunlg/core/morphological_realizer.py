import logging
from abc import ABC, abstractmethod
from typing import Dict, Tuple

from numpy.random import Generator

from .models import DocumentPlanNode, Message, Slot
from .pipeline import NLGPipelineComponent
from .registry import Registry

log = logging.getLogger("root")


class LanguageSpecificMorphologicalRealizer(ABC):
    def __init__(self, language):
        self.language = language

    @abstractmethod
    def realize(self, slot: Slot) -> str:
        pass


class MorphologicalRealizer(NLGPipelineComponent):
    def __init__(self, language_realizers: Dict[str, LanguageSpecificMorphologicalRealizer]) -> None:
        self.language_realizers = language_realizers

    def run(
        self, registry: Registry, random: Generator, language: str, document_plan: DocumentPlanNode
    ) -> Tuple[DocumentPlanNode]:
        """
        Run this pipeline component.
        """
        log.info("Running Morphological Realizer")

        if language.endswith("-head"):
            language = language[:-5]
            log.debug("Language had suffix '-head', removing. Result: {}".format(language))

        if language not in self.language_realizers:
            log.warning("No morphological realizer for language {}".format(language))
            return (document_plan,)

        self._recurse(language, document_plan)

        if log.isEnabledFor(logging.DEBUG):
            document_plan.print_tree()

        return (document_plan,)

    def _recurse(self, language: str, this: DocumentPlanNode) -> None:
        log.debug("Visiting '{}'".format(this))
        if not isinstance(this, Message):
            for child in this.children:
                self._recurse(language, child)
            return

        for template_component in this.template.components:
            if isinstance(template_component, Slot):
                realized_value = self.language_realizers[language].realize(template_component)
                template_component.value = lambda x, realized_value=realized_value: realized_value

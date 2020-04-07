import logging
from abc import abstractmethod
from collections import defaultdict
from typing import Any, DefaultDict, Set, Tuple

from numpy.random import Generator

from core.models import DocumentPlanNode, Slot
from core.pipeline import NLGPipelineComponent
from core.registry import Registry

log = logging.getLogger("root")


class EntityNameResolver(NLGPipelineComponent):
    """
    A NLGPipelineComponent that transforms abstracted entity identifers to names.

    Entity name variants are supplied as the 'ner_table' component in the registry.

    When an entity is first encountered, "full_name" is used. On subsequent uses,
    either "short_name" or "pronoun" is used depending on whether the previously
    encountered entity is the same entity as the one being processed.
    """

    def run(
        self, registry: Registry, random: Generator, language: str, document_plan: DocumentPlanNode
    ) -> Tuple[DocumentPlanNode]:
        """
        Run this pipeline component.
        """
        log.info("Running NER")

        if language.endswith("-head"):
            language = language[:-5]
            log.debug("Language had suffix '-head', removing. Result: {}".format(language))

        previous_entities = defaultdict(lambda: None)
        self._recurse(registry, random, language, document_plan, previous_entities, set())

        if log.isEnabledFor(logging.DEBUG):
            document_plan.print_tree()

        return (document_plan,)

    def _recurse(
        self,
        registry: Registry,
        random: Generator,
        language: str,
        this: DocumentPlanNode,
        previous_entities: DefaultDict[str, None],
        encountered: Set[str],
    ) -> Tuple[Set[str], DefaultDict[str, None]]:
        """
        Traverses the DocumentPlan tree recursively in-order and modifies named
        entity to_value functions to return the chosen form of that NE's name.
        """
        if isinstance(this, Slot):
            if not self.is_entity(this.value):
                log.debug("Visited non-NE leaf node {}".format(this.value))
                return encountered, previous_entities

            log.debug("Visiting NE leaf {}".format(this.value))
            entity_type, entity = self.parse_entity(this.value)

            if previous_entities[entity_type] == entity:
                log.debug("Same as previous entity")
                this.attributes["name_type"] = "pronoun"

            elif entity in encountered:
                log.debug("Different entity than previous, but has been previously encountered")
                this.attributes["name_type"] = "short"

            else:
                log.debug("First time encountering this entity")
                this.attributes["name_type"] = "full"
                encountered.add(entity)
                log.debug("Added entity to encountered, all encountered: {}".format(encountered))

            self.resolve_surface_form(registry, random, language, this, entity, entity_type)
            log.debug("Resolved entity name")

            this.attributes["entity_type"] = entity_type
            previous_entities[entity_type] = entity

            return encountered, previous_entities
        elif isinstance(this, DocumentPlanNode):
            log.debug("Visiting non-leaf '{}'".format(this))
            for child in this.children:
                encountered, previous_entities = self._recurse(
                    registry, random, language, child, previous_entities, encountered
                )
            return encountered, previous_entities
        return encountered, previous_entities

    @abstractmethod
    def is_entity(self, maybe_entity: Any) -> bool:
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def parse_entity(self, entity: str) -> Tuple[str, str]:
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def resolve_surface_form(
        self, registry: Registry, random: Generator, language: str, slot: Slot, entity: str, entity_type: str
    ) -> None:
        raise NotImplementedError("Not implemented")

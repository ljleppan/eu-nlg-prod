import logging
from abc import abstractmethod
from typing import List, Tuple

from numpy.random import Generator

from .models import DocumentPlanNode, Message, Relation
from .pipeline import NLGPipelineComponent
from .registry import Registry

log = logging.getLogger("root")


class NoInterestingMessagesException(Exception):
    pass


class DocumentPlanner(NLGPipelineComponent):
    @abstractmethod
    def run(
        self, registry: Registry, random: Generator, language: str, scored_messages
    ) -> Tuple[DocumentPlanNode, List[Message]]:
        pass


class HeadlineDocumentPlanner(DocumentPlanner):
    def run(
        self, registry: Registry, random: Generator, language: str, scored_messages
    ) -> Tuple[DocumentPlanNode, List[Message]]:
        """
        Run this pipeline component.
        """

        log.debug("Creating headline document plan")

        # Root contains a sequence of children
        document_plan = DocumentPlanNode(children=[], relation=Relation.SEQUENCE)

        headline_message, _ = self.select_next_nucleus(scored_messages, [])
        all_messages = scored_messages

        document_plan.children.append(DocumentPlanNode(children=[headline_message], relation=Relation.SEQUENCE))

        return document_plan, all_messages

    @abstractmethod
    def select_next_nucleus(
        self, available_message: List[Message], selected_nuclei: List[Message]
    ) -> Tuple[Message, float]:
        raise NotImplementedError


class BodyDocumentPlanner(DocumentPlanner):
    def __init__(self, new_paragraph_absolute_threshold) -> None:
        self.new_paragraph_absolute_threshold = new_paragraph_absolute_threshold

    def run(
        self, registry: Registry, random: Generator, language: str, scored_messages: List[Message]
    ) -> Tuple[DocumentPlanNode, List[Message]]:
        log.debug("Creating body document plan")

        # Root contains a sequence of children
        document_plan = DocumentPlanNode(children=[], relation=Relation.SEQUENCE)

        available_messages = scored_messages[:]  # Make a copy s.t. we can modify in place
        selected_nuclei: List[Message] = []

        while True:
            nucleus: Message
            nucleus_score: float
            nucleus, nucleus_score = self.select_next_nucleus(available_messages, selected_nuclei)

            if (
                nucleus_score < self.new_paragraph_absolute_threshold
                or nucleus_score < self.new_paragraph_relative_threshold(selected_nuclei)
            ):
                if selected_nuclei:
                    return (document_plan, scored_messages)

            selected_nuclei.append(nucleus)

            # Messages are only allowed in the DP once
            available_messages = [m for m in available_messages if m != nucleus]

            # Get a suitable amount of satellites
            satellites: List[Message] = self.select_satellites_for_nucleus(nucleus, available_messages)

            # Messages are only allowed in the DP once
            available_messages = [m for m in available_messages if m not in satellites]

            document_plan.children.append(DocumentPlanNode([nucleus] + satellites, Relation.SEQUENCE))

    @abstractmethod
    def select_next_nucleus(
        self, available_message: List[Message], selected_nuclei: List[Message]
    ) -> Tuple[Message, float]:
        raise NotImplementedError

    @abstractmethod
    def new_paragraph_relative_threshold(self, selected_nuclei: List[Message]) -> float:
        raise NotImplementedError

    @abstractmethod
    def select_satellites_for_nucleus(self, nucleus: Message, available_messages: List[Message]) -> List[Message]:
        raise NotImplementedError

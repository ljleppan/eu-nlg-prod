import logging
import random
from typing import List, Optional, Tuple

from core.document_planner import BodyDocumentPlanner, HeadlineDocumentPlanner
from core.models import Message

log = logging.getLogger("root")

MAX_PARAGRAPHS = 3

MAX_SATELLITES_PER_NUCLEUS = 5
MIN_SATELLITES_PER_NUCLEUS = 2

NEW_PARAGRAPH_ABSOLUTE_THRESHOLD = 0.0

SATELLITE_RELATIVE_THRESHOLD = 0.5
SATELLITE_ABSOLUTE_THRESHOLD = 0.2


class EURandomBodyDocumentPlanner(BodyDocumentPlanner):
    def __init__(self) -> None:
        super().__init__(new_paragraph_absolute_threshold=NEW_PARAGRAPH_ABSOLUTE_THRESHOLD)

    def select_next_nucleus(
        self, available_message: List[Message], selected_nuclei: List[Message]
    ) -> Tuple[Message, float]:
        return _select_next_nucleus(available_message, selected_nuclei)

    def new_paragraph_relative_threshold(self, selected_nuclei: List[Message]) -> float:
        return float("-inf")

    def select_satellites_for_nucleus(
        self, nucleus: Message, available_core_messages: List[Message], available_expanded_message: List[Message]
    ) -> List[Message]:
        satellites: List[Message] = []
        available_messages = available_core_messages + available_expanded_message
        while available_messages and len(satellites) < MAX_SATELLITES_PER_NUCLEUS:
            random.shuffle(available_messages)
            satellites.append(available_messages.pop())
        return satellites


class EURandomHeadlineDocumentPlanner(HeadlineDocumentPlanner):
    def select_next_nucleus(
        self, available_message: List[Message], selected_nuclei: List[Message]
    ) -> Tuple[Message, float]:
        return _select_next_nucleus(available_message, selected_nuclei)


def _select_next_nucleus(
    available_messages: List[Message], selected_nuclei: List[Message]
) -> Tuple[Optional[Message], float]:

    if len(selected_nuclei) >= MAX_PARAGRAPHS:
        return None, 0
    next_nucleus = random.choice(available_messages)
    return next_nucleus, next_nucleus.score

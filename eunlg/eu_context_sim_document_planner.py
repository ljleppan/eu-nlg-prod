import logging
from typing import List, Optional, Tuple

from core.document_planner import BodyDocumentPlanner, HeadlineDocumentPlanner
from core.models import Message

log = logging.getLogger("root")

MAX_PARAGRAPHS = 3

MAX_SATELLITES_PER_NUCLEUS = 5
MIN_SATELLITES_PER_NUCLEUS = 2

NEW_PARAGRAPH_ABSOLUTE_THRESHOLD = 0.5

SATELLITE_RELATIVE_THRESHOLD = 0.5
SATELLITE_ABSOLUTE_THRESHOLD = 0.2


class EUContextSimBodyDocumentPlanner(BodyDocumentPlanner):
    def __init__(self) -> None:
        super().__init__(new_paragraph_absolute_threshold=NEW_PARAGRAPH_ABSOLUTE_THRESHOLD)

    def select_next_nucleus(
        self, available_message: List[Message], selected_nuclei: List[Message]
    ) -> Tuple[Message, float]:
        return _select_next_nucleus(available_message, selected_nuclei)

    def new_paragraph_relative_threshold(self, selected_nuclei: List[Message]) -> float:
        return _new_paragraph_relative_threshold(selected_nuclei)

    def select_satellites_for_nucleus(self, nucleus: Message, available_core_messages: List[Message]) -> List[Message]:
        return _select_satellites_for_nucleus(nucleus, available_core_messages)


class EUContextSimHeadlineDocumentPlanner(HeadlineDocumentPlanner):
    def select_next_nucleus(
        self, available_message: List[Message], selected_nuclei: List[Message]
    ) -> Tuple[Message, float]:
        return _select_next_nucleus(available_message, selected_nuclei)


def _topic(message: Message) -> str:
    return ":".join(message.main_fact.value_type.split(":")[:2])


def _select_next_nucleus(
    available_messages: List[Message], selected_nuclei: List[Message]
) -> Tuple[Optional[Message], float]:

    log.debug("Starting a new paragraph")
    available = available_messages[:]  # copy

    if len(selected_nuclei) >= MAX_PARAGRAPHS or not available_messages:
        log.debug("MAX_PARAGPAPHS reached, stopping")
        return None, 0

    available.sort(key=lambda message: message.score, reverse=True)
    next_nucleus = available[0]

    return next_nucleus, next_nucleus.score


def _new_paragraph_relative_threshold(selected_nuclei: List[Message]) -> float:
    # Gotta have something, so we'll add the first nucleus not matter value
    if not selected_nuclei:
        return float("-inf")

    # We'd really like to get a second paragraph, so we relax the requirements a bit here
    if len(selected_nuclei) == 1:
        return 0.1 * selected_nuclei[0].score

    # We already have at least 2 paragraphs, so we can be picky about whether we continue or not
    return 0.3 * selected_nuclei[0].score


def _select_satellites_for_nucleus(nucleus: Message, available_messages: List[Message]) -> List[Message]:
    log.debug("Selecting satellites for {} from among {} options".format(nucleus, len(available_messages)))
    satellites: List[Message] = []
    available_messages = available_messages[:]  # Copy, s.t. we can modify in place

    previous = nucleus
    while True:

        # Modify scores to account for context
        scored_available = [(message.score, message) for message in available_messages if message.score > 0]
        scored_available = _weigh_by_analysis_similarity(scored_available, previous)
        scored_available = _weigh_by_analysis_similarity(scored_available, nucleus)
        scored_available = _weigh_by_context_similarity(scored_available, previous)

        # Filter out based on thresholds
        filtered_scored_available = [
            (score, message)
            for (score, message) in scored_available
            if score > SATELLITE_RELATIVE_THRESHOLD * nucleus.score or score > SATELLITE_ABSOLUTE_THRESHOLD
        ]
        log.debug("After rescoring for context, {} available satellites remain".format(len(scored_available)))

        if not filtered_scored_available:
            if len(satellites) >= MIN_SATELLITES_PER_NUCLEUS:
                log.debug("Done with satellites: MIN_SATELLITES_PER_NUCLEUS reached, no satellites pass filter.")
                return satellites
            elif scored_available:
                log.debug(
                    "No satellite candidates pass threshold but have not reached MIN_SATELLITES_PER_NUCLEUS. "
                    "Trying without filter."
                )
                filtered_scored_available = scored_available
            else:
                log.debug("Did not reach MIN_SATELLITES_PER_NUCLEUS, but ran out of candidates. Ending paragraphs.")
                return satellites

        if len(satellites) >= MAX_SATELLITES_PER_NUCLEUS:
            log.debug("Stopping due to having reaches MAX_SATELLITE_PER_NUCLEUS")
            return satellites

        filtered_scored_available.sort(key=lambda pair: pair[0], reverse=True)

        score, selected_satellite = filtered_scored_available[0]
        satellites.append(selected_satellite)
        log.debug("Added satellite {} (temp_score={})".format(selected_satellite, score))

        previous = selected_satellite
        available_messages = [message for message in available_messages if message != selected_satellite]


def _weigh_by_analysis_similarity(
    messages: List[Tuple[float, Message]], previous: Message
) -> List[Tuple[float, Message]]:

    weighted: List[Tuple[float, Message]] = []
    unprocessed: List[Message] = []

    # Given that the previous message has value_type of "a:b:c:d", we start trying prefixes longest-first,
    # i.e. starting with "a:b:c:d", then "a:b:c", then "a:b" etc.
    # Each message's score is then weighted by 1/n where n is how many'th prefix this is. That is,
    # "a:b:c:d" -> n=1, "a:b:c" -> n=2 etc.
    value_type_fragments = previous.main_fact.value_type.split(":")
    for n, fragment_count in enumerate(reversed(range(len(value_type_fragments)))):
        value_type_prefix = ":".join(value_type_fragments[: fragment_count + 1])

        for score, message in messages:
            if message.main_fact.value_type.startswith(value_type_prefix):
                weighted.append((score * 1 / (n + 1), message))
            else:
                unprocessed.append((score, message))

        messages, unprocessed = unprocessed, []

    # Still need to process the messages which shared no prefix at all.
    weighted.extend((0, message) for (score, message) in unprocessed)
    return weighted


def _weigh_by_context_similarity(
    messages: List[Tuple[float, Message]], previous: Message
) -> List[Tuple[float, Message]]:
    weighted: List[Tuple[float, Message]] = []

    for score, message in messages:
        if previous.main_fact.location == message.main_fact.location:
            score *= 1.5

        if previous.main_fact.timestamp == message.main_fact.timestamp:
            score *= 1.1

        weighted.append((score, message))
    return weighted

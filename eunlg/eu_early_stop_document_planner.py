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


class EUEarlyStopBodyDocumentPlanner(BodyDocumentPlanner):
    def __init__(self) -> None:
        super().__init__(new_paragraph_absolute_threshold=NEW_PARAGRAPH_ABSOLUTE_THRESHOLD)

    def select_next_nucleus(
        self, available_message: List[Message], selected_nuclei: List[Message]
    ) -> Tuple[Message, float]:
        return _select_next_nucleus(available_message, selected_nuclei)

    def new_paragraph_relative_threshold(self, selected_nuclei: List[Message]) -> float:
        return _new_paragraph_relative_threshold(selected_nuclei)

    def select_satellites_for_nucleus(self, nucleus: Message, available_core_messages: List[Message]) -> List[Message]:
        satellites: List[Message] = []
        available_core_messages = available_core_messages[:]  # Copy, s.t. we can modify in place
        available_core_messages.sort(key=lambda x: x.score, reverse=True)

        while available_core_messages and len(satellites) < MAX_SATELLITES_PER_NUCLEUS:
            satellites.append(available_core_messages.pop(0))
        return satellites


class EUEarlyStopHeadlineDocumentPlanner(HeadlineDocumentPlanner):
    def select_next_nucleus(
        self, available_message: List[Message], selected_nuclei: List[Message]
    ) -> Tuple[Message, float]:
        return _select_next_nucleus(available_message, selected_nuclei)


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

    while True:

        scored_available = [(message.score, message) for message in available_messages if message.score > 0]

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

        available_messages = [message for message in available_messages if message != selected_satellite]

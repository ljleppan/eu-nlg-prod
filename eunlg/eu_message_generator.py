import logging
from collections import deque
from datetime import datetime
from math import isnan
from typing import List, Optional, Tuple

from numpy.random.mtrand import RandomState
from pandas import Series

from core.datastore import DataFrameStore
from core.message_generator import MessageGenerator, NoMessagesForSelectionException
from core.models import Fact, Message, DocumentPlanNode
from core.pipeline import NLGPipeline
from core.registry import Registry
from eu_document_planner import EUHeadlineDocumentPlanner, EUBodyDocumentPlanner
from eu_importance_allocator import EUImportanceSelector

log = logging.getLogger("root")


class EUMessageGenerator(MessageGenerator):
    """
    An NLGPipelineComponent that creates messages from StatFi crime statistics data.
    """

    def __init__(self, expand=True):
        self.expand = expand
        super(EUMessageGenerator, self).__init__()

    def run(
        self,
        registry: Registry,
        random: RandomState,
        language: str,
        location_query: str,
        location_type_query: str,
        dataset: str,
        previous_location: str,
        ignored_cols: Optional[List[str]] = None,
    ) -> Tuple[List[Message], List[Message], List[Message]]:
        log.info(
            "Generating messages with location={}, location_type={}, data={}, previous_location={}".format(
                location_query, location_type_query, dataset, previous_location
            )
        )

        data_store: DataFrameStore = registry.get("{}-data".format(dataset))
        log.debug("Underlying DataFrame is of size {}".format(data_store.all().shape))

        if ignored_cols is None:
            ignored_cols = []

        if location_query == "all":
            core_df = data_store.all()
            expanded_df = None
        elif self.expand:
            log.debug('Query: "{}"'.format("location=={!r}".format(location_query)))
            core_df = data_store.query("location=={!r}".format(location_query))
            expanded_df = data_store.query("location!={!r}".format(location_query))
        else:
            log.debug('Query: "{}"'.format("location=={!r}".format(location_query)))
            core_df = data_store.query("location=={!r}".format(location_query))
            expanded_df = None
        log.debug(
            "Resulting DataFrames are of sizes {} and {}".format(
                core_df.shape, "empty" if expanded_df is None else expanded_df.shape
            )
        )

        core_messages: List[Message] = []
        expanded_messages: List[Message] = []
        col_names = core_df
        col_names = [
            col_name
            for col_name in col_names
            if not (
                col_name in ["location", "location_type", "timestamp", "timestamp_type", "agent", "agent_type"]
                or col_name in ignored_cols
                or ":outlierness" in col_name
            )
        ]
        core_df.apply(self._gen_messages, axis=1, args=(col_names, core_messages))
        if expanded_df is not None:
            expanded_df.apply(self._gen_messages, axis=1, args=(col_names, expanded_messages))

        if log.getEffectiveLevel() <= 5:
            for m in core_messages:
                log.debug("Extracted CORE message {}".format(m.main_fact))
            for m in expanded_messages:
                log.debug("Extracted EXPANDED message {}".format(m.main_fact))

        log.info(
            "Extracted total {} core messages and {} expanded messages".format(
                len(core_messages), len(expanded_messages)
            )
        )
        if not core_messages:
            raise NoMessagesForSelectionException("No core messages")

        if previous_location:
            log.info("Have previous_location, generating stuff for that")
            previous_location_messages = self._gen_messages_for_previous_location(
                registry, language, location_query, dataset, previous_location
            )
        else:
            previous_location_messages = []

        return core_messages, expanded_messages, previous_location_messages

    def _gen_messages(
        self,
        row: Series,
        col_names: List[str],
        messages: List[Message],
        importance_coefficient: float = 1.0,
        polarity: float = 0.0,
    ) -> None:
        location = row["location"]
        location_type = row["location_type"]
        timestamp_type = row["timestamp_type"]
        agent = row["agent"]
        agent_type = row["agent_type"]
        timestamp = row["timestamp"]

        if isinstance(timestamp, float):
            timestamp = str(int(timestamp))

        # Retain this + last years' monthly stuff. Skip older monthly stuff.
        if timestamp_type == "month":
            year, month = timestamp.split("M")
            if int(year) < datetime.now().year - 1:
                return

        # For yearly stuff, keep the last three years.
        elif timestamp_type == "year":
            if int(timestamp) < datetime.now().year - 3:
                return

        for col_name in col_names:
            value_type = col_name
            value = row[col_name]

            outlierness_col_name = col_name + ":outlierness"
            outlierness = row.get(outlierness_col_name, None)

            # There are potentially multiple outlierness values to choose from, corresponding to multiple ways of
            # grouping the data. TODO: Smarter way to select which on the use
            if not outlierness:
                outlierness = row.get(col_name + ":grouped_by_time:outlierness", None)

            if value is None or value == "" or (isinstance(value, float) and isnan(value)):
                # 'value' is effectively undefined, do not REALLY generate the message.
                continue

            fact = Fact(
                location="[ENTITY:{}:{}]".format(location_type, location),
                location_type=location_type,
                value=value,
                value_type=value_type,
                timestamp=timestamp,
                timestamp_type=timestamp_type,
                agent=agent,
                agent_type=agent_type,
                outlierness=outlierness,
            )

            message = Message(facts=fact, importance_coefficient=importance_coefficient, polarity=polarity)
            messages.append(message)

    def _gen_messages_for_previous_location(
        self, registry: Registry, language: str, location_type: str, dataset: str, previous_location: str,
    ) -> List[Message]:
        pipeline = NLGPipeline(
            registry,
            EUMessageGenerator(expand=True),
            EUImportanceSelector(),
            EUHeadlineDocumentPlanner() if "-head" in language else EUBodyDocumentPlanner(),
        )

        previous_docplan = pipeline.run((previous_location, location_type, dataset, None), language)[0]
        assert isinstance(previous_docplan, DocumentPlanNode)

        log.debug(f"PREVIOUS DOCPLAN: {previous_docplan}")

        messages: List[Message] = []
        queue = deque([previous_docplan])
        while queue:
            item = queue.pop()
            if isinstance(item, Message):
                messages.append(item)
            else:
                queue.extend(item.children)

        log.debug(f"PREVIOUS MESSAGES: {messages}")

        return messages

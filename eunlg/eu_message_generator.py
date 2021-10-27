import logging
from datetime import datetime
from math import isnan
from typing import List, Optional, Tuple

from numpy.random.mtrand import RandomState
from pandas import Series

from core.datastore import DataFrameStore
from core.message_generator import MessageGenerator, NoMessagesForSelectionException
from core.models import Fact, Message
from core.registry import Registry

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
        ignored_cols: Optional[List[str]] = None,
    ) -> Tuple[List[Message], List[Message]]:
        log.info(
            "Generating messages with location={}, location_type={}, data={}".format(
                location_query, location_type_query, dataset,
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

        # Remove all but 10k most interesting expanded messages
        expanded_messages = sorted(expanded_messages, key=lambda msg: msg.score, reverse=True)[:10_000]
        log.info(f"Filtered expanded messages to top {len(expanded_messages)}")

        return core_messages, expanded_messages

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

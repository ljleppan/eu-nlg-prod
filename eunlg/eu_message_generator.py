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
    ) -> Tuple[List[Message]]:
        log.info(
            "Generating messages with location={}, location_type={}, data={}".format(
                location_query, location_type_query, dataset,
            )
        )

        data_store: DataFrameStore = registry.get("{}-data".format(dataset))
        log.debug("Underlying DataFrame is of size {}".format(data_store.all().shape))

        if ignored_cols is None:
            ignored_cols = []

        query: List[str] = []
        if location_query and location_query != "all":
            query.append("location=={!r}".format(location_query))

        # if location_type_query:
        #    query.append("location_type=={!r}".format(location_type_query))

        query_str = " and ".join(query)

        if query_str:
            log.debug('Query: "{}"'.format(query_str))
            df = data_store.query(query_str)
        else:
            log.debug("Empty query, getting full data")
            df = data_store.all()
        log.debug("Resulting DataFrame is of size {}".format(df.shape))

        messages: List[Message] = []
        col_names = df
        col_names = [
            col_name
            for col_name in col_names
            if not (
                col_name in ["location", "location_type", "timestamp", "timestamp_type", "agent", "agent_type"]
                or col_name in ignored_cols
                or ":outlierness" in col_name
            )
        ]
        df.apply(self._gen_messages, axis=1, args=(col_names, messages))

        if log.getEffectiveLevel() <= 5:
            for m in messages:
                log.debug("Extracted {}".format(m.main_fact))

        log.info("Extracted total {} messages".format(len(messages)))
        if not messages:
            raise NoMessagesForSelectionException()

        # for v in {message.main_fact.value_type for message in messages}:
        #    print(v)
        # raise ValueError()

        return (messages,)

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
                log.debug("Skipping data from {} as too old to be interesting".format(timestamp))
                return

        # For yearly stuff, keep the last three years.
        elif timestamp_type == "year":
            if int(timestamp) < datetime.now().year - 3:
                log.debug("Skipping data from {} as too old to be interesting".format(timestamp))
                return

        log.debug("Keeping data from {} as it seems reasonably recent".format(timestamp))

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

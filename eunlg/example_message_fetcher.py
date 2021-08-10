import logging
import random
from math import isnan
from pathlib import Path
from typing import List, Optional

from pandas import Series, DataFrame

from core.datastore import DataFrameStore
from core.message_generator import MessageGenerator
from core.models import Template, Message, Fact
from service import DATA_ROOT

log = logging.getLogger("root")


class ExampleMessageFetcher(MessageGenerator):
    def __init__(self):
        super(ExampleMessageFetcher, self).__init__()

    def run(self, dataset: str, template: Optional[Template], shuffle: bool = False) -> List[Message]:
        """
        Fetch a representative sample of example messages from `dataset`that match `template`.

        If `template` is not given, return a representative sample of all the messages in `dataset`.

        If `suffle` is set to True, the messages are suffled before selection, resulting in a somewhat more random
        sample. If left False, as per the default, the ordering of the data in the underlying DF effectively decides
        what messages are returned.

        "Representative sample" is defined as a sample containing all (or rather as many as possible) of the unique
        values present within the Messages available for the dataset, except the "value" values themselves. Not all
        COMBINATIONS of values are guaranteed to be present, as that is by definition just the set of all messages.
        """

        # Find the correct dataframe. Passing a registry as an argument could maybe be slightly more foolproof, but
        # generating a complete registry is 1) a hassle and 2) a lot of extra work. Instead we just borrow the same
        # DATA_ROOT used in producing the prime Registry in NLGService.
        cache_path: Path = (DATA_ROOT / "{}.cache".format(dataset)).absolute()
        if not cache_path.exists():
            raise IOError("No cached dataset found at {}.")
        df: DataFrame = DataFrameStore(str(cache_path)).all()
        log.debug("Found DataFrame of size {}".format(df.shape))

        # Get ALL messages (copied from EUMessageGenerator)
        messages: List[Message] = []
        col_names = df
        col_names = [
            col_name
            for col_name in col_names
            if not (
                col_name in ["location", "location_type", "timestamp", "timestamp_type", "agent", "agent_type"]
                or ":outlierness" in col_name
            )
        ]
        df.apply(self._gen_messages, axis=1, args=(col_names, messages))
        log.info(f"Generated a total of {len(messages)} messages")

        if template is not None:
            # Limit to those that match the given template
            messages = [message for message in messages if template.check(message, messages, fill_slots=False)]
            log.info(f"Filtered to a total of {len(messages)} messages matching the provided template")
        else:
            log.info(f"No template given, continuing with {len(messages)} messages")

        # Shuffle data if this was requested. NB: This shuffle is *FAR* from being cryptographically secure due to
        # the amount of data. As per https://docs.python.org/3/library/random.html#random.shuffle the Mersenne Twister
        # period can only fit up to 2080 elements.
        if shuffle:
            random.shuffle(messages)

        # Find a selection that covers all unique values for the "meta" fields. We are NOT finding all *combinations*
        # of values.
        selected_messages: List[Message] = []
        for meta_col_name in ["location", "location_type", "timestamp", "timestamp_type", "agent", "agent_type"]:
            unique_col_values = {getattr(msg.main_fact, meta_col_name) for msg in messages}
            for unique_value in unique_col_values:

                log.debug(f"Ensuring we have a message where '{meta_col_name}' is '{unique_value}'")

                # Check if we, by chance, already have selected a message that has this value
                if any(getattr(msg.main_fact, meta_col_name) == unique_value for msg in selected_messages):
                    log.debug("Already had one selected from prior")
                    continue

                # We did NOT have a message with this specific unique value, so we attempt to find one
                try:
                    selected_message = next(
                        msg for msg in messages if getattr(msg.main_fact, meta_col_name) == unique_value
                    )
                    selected_messages.append(selected_message)
                    log.debug("Didn't have one already, but found a new one")
                except StopIteration:
                    log.debug("Didn't have one, and can't find one. Skipping as an impossible combo.")
                    pass

        # Add messages s.t. all value_type values are covered. col_names is defined way above, back when we first
        # start generating messages.
        for unique_value_type_value in col_names:
            log.debug(f"Ensuring we have a message where 'value_type' is '{unique_value_type_value}'")
            if any(msg.main_fact.value_type == unique_value_type_value for msg in selected_messages):
                log.debug("Already had one selected from prior")
                continue

            # We did NOT have a message with this specific unique value, so we attempt to find one
            try:
                selected_message = next(msg for msg in messages if msg.main_fact.value_type == unique_value_type_value)
                selected_messages.append(selected_message)
                log.debug("Didn't have one already, but found a new one")
            except StopIteration:
                log.debug("Didn't have one, and can't find one. Skipping as an impossible combo.")
                pass

        log.info(
            f"Identified a total of {len(selected_messages)} messages that cover as many of the unique values as "
            f"possible while matching the template."
        )
        for msg in selected_messages:
            log.debug(msg)
        return selected_messages

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


if __name__ == "__main__":
    # log.info = print
    # log.debug = print

    fetcher = ExampleMessageFetcher()
    fetcher.run("cphi", None, shuffle=True)

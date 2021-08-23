import logging
import random
from functools import lru_cache
from math import isnan
from typing import List, Optional, Tuple, Dict

import numpy as np
from pandas import Series, DataFrame

from core.models import Template, Message, Fact, Slot, DocumentPlanNode
from core.morphological_realizer import MorphologicalRealizer
from core.pipeline import LanguageSplitComponent
from core.realize_slots import SlotRealizer
from core.template_reader import read_templates
from core.template_selector import TemplateSelector
from croatian_simple_morpological_realizer import CroatianSimpleMorphologicalRealizer
from english_uralicNLP_morphological_realizer import EnglishUralicNLPMorphologicalRealizer
from eu_date_realizer import EnglishEUDateRealizer, FinnishEUDateRealizer, CroatianEUDateRealizer, GermanEUDateRealizer
from eu_named_entity_resolver import EUEntityNameResolver
from eu_number_realizer import EUNumberRealizer
from finnish_uralicNLP_morphological_realizer import FinnishUralicNLPMorphologicalRealizer
from service import EUNlgService
from service import translator as TRANSLATOR

log = logging.getLogger("root")


SERVICE = EUNlgService()
TEMPLATE_SELECTOR = TemplateSelector()
SLOT_REALIZER = SlotRealizer()
DATE_REALIZER = LanguageSplitComponent(
    {
        "en": EnglishEUDateRealizer(),
        "fi": FinnishEUDateRealizer(),
        "hr": CroatianEUDateRealizer(),
        "de": GermanEUDateRealizer(),
    }
)
ENTITY_NAME_RESOLVER = EUEntityNameResolver(TRANSLATOR)
NUMBER_REALIZER = EUNumberRealizer()
MORPHOLOGICAL_REALIZER = MorphologicalRealizer(
    {
        "en": EnglishUralicNLPMorphologicalRealizer(),
        "fi": FinnishUralicNLPMorphologicalRealizer(),
        "hr": CroatianSimpleMorphologicalRealizer(),
    }
)


def obtain_example_messages_for_all_templates(
    dataset: str, language: str, shuffle: bool = False
) -> List[Tuple[Template, List[Message]]]:

    log.info("Loading templates")
    templates: List[Template] = []
    for resource in SERVICE.resources:
        if resource.supports(language, dataset):
            for _, new_templates in read_templates(resource.templates)[0].items():
                templates.extend(new_templates)

    log.info(f"Found a total of {len(templates)} templates for language '{language}' and dataset '{dataset}'")

    output: List[Tuple[Template, List[Message]]] = []
    for template in templates:
        example_messages = fetch_example_messages(dataset, template, shuffle)
        output.append((template, example_messages))

    return output


def fetch_example_messages(dataset: str, template: Optional[Template], shuffle: bool = False) -> List[Message]:
    """
    Fetch a representative sample of example messages from `dataset` that match `template`.

    If `template` is not given, return a representative sample of all the messages in `dataset`.

    If `shuffle` is set to True, the messages are shuffled before selection, resulting in a somewhat more random
    sample. If left False, as per the default, the ordering of the data in the underlying DF effectively decides
    what messages are returned.

    "Representative sample" is defined as a sample containing all (or rather as many as possible) of the unique
    values present within the Messages available for the dataset, except the "value" values themselves. Not all
    COMBINATIONS of values are guaranteed to be present, as that is by definition just the set of all messages.
    """

    # Get ALL messages (the result is cached, 'cause we don't want to keep regenerating the same messages over and
    # over again.
    messages, df = _generate_all_messages(dataset)

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
                log.debug("\tAlready had one selected from prior")
                continue

            # We did NOT have a message with this specific unique value, so we attempt to find one
            try:
                selected_message = next(
                    msg for msg in messages if getattr(msg.main_fact, meta_col_name) == unique_value
                )
                selected_messages.append(selected_message)
                log.debug("\tDidn't have one already, but found a new one")
            except StopIteration:
                log.debug("\tDidn't have one, and can't find one. Skipping as an impossible combo.")
                pass

    # Add messages s.t. all value_type values are covered.
    value_types = [
        col_name
        for col_name in df
        if not (
            col_name in ["location", "location_type", "timestamp", "timestamp_type", "agent", "agent_type"]
            or ":outlierness" in col_name
        )
    ]
    for unique_value_type_value in value_types:
        log.info(f"Ensuring we have a message where 'value_type' is '{unique_value_type_value}'")
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


@lru_cache(maxsize=1)
def _generate_all_messages(dataset: str) -> Tuple[List[Message], DataFrame]:
    log.info("DataFrame not in LRU cache, generating messages")
    dataframe: DataFrame = SERVICE.registry.get(f"{dataset}-data").all()
    log.debug("Found DataFrame of size {}".format(dataframe.shape))

    messages: List[Message] = []
    col_names = dataframe
    col_names = [
        col_name
        for col_name in col_names
        if not (
            col_name in ["location", "location_type", "timestamp", "timestamp_type", "agent", "agent_type"]
            or ":outlierness" in col_name
        )
    ]
    dataframe.apply(_gen_messages, axis=1, args=(col_names, messages))
    log.info(f"Generated a total of {len(messages)} messages")
    return messages, dataframe


def _gen_messages(
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


def template_as_string_approximation(template: Template) -> str:
    strn = ""
    for element in template.components:
        if isinstance(element, Slot):
            strn += "{" + element.slot_type + "}"
        else:
            strn += element.value
        strn += " "
    return strn


def msg_as_realized_dict(message: Message, template: Template, language: str) -> Dict[str, str]:
    rnd = np.random.default_rng(42)

    # Disable logging for a while
    old_log_level = log.level
    log.setLevel(logging.WARNING)

    # Accessing a non-public method, but I can't be bothered to re-engineer the whole class.
    TEMPLATE_SELECTOR._add_template_to_message(message, template, [message])

    # Realize the single message + template pair
    doc_plan = DocumentPlanNode([message])
    (doc_plan,) = SLOT_REALIZER.run(SERVICE.registry, rnd, language, doc_plan)
    (doc_plan,) = DATE_REALIZER.run(SERVICE.registry, rnd, language, doc_plan)
    (doc_plan,) = ENTITY_NAME_RESOLVER.run(SERVICE.registry, rnd, language, doc_plan)
    (doc_plan,) = NUMBER_REALIZER.run(SERVICE.registry, rnd, language, doc_plan)
    (doc_plan,) = MORPHOLOGICAL_REALIZER.run(SERVICE.registry, rnd, language, doc_plan)

    # Re-enable logging
    log.setLevel(old_log_level)

    msg: Message = doc_plan.children[0]

    dct = dict()
    for component in msg.template.components:
        if isinstance(component, Slot):
            slot_type = component.slot_type
            if slot_type not in dct:
                dct[slot_type] = []
            dct[slot_type].append(str(component.value))

    for key, val in dct.items():
        dct[key] = " ".join(val)

    return dct


if __name__ == "__main__":
    print("asd")
    log.setLevel(logging.DEBUG)
    log.debug("test")
    print("asd")

    for (tmpl, example_msgs) in obtain_example_messages_for_all_templates("cphi", "en", shuffle=True):
        print(f"{len(example_msgs)} example messages found for template {tmpl}")

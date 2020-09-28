# FYI: needed to change the year to 2020
import datetime
import logging
import math
from typing import List

from numpy.random.mtrand import RandomState

from core.models import Message
from core.pipeline import NLGPipelineComponent
from core.registry import Registry

log = logging.getLogger("root")


class EUImportanceSelector(NLGPipelineComponent):
    def run(
        self,
        registry: Registry,
        random: RandomState,
        language: str,
        core_messages: List[Message],
        expanded_messages: List[Message],
    ):
        """
        Runs this pipeline component.
        """
        core_messages = self.score_importance(core_messages, registry)
        core_messages = sorted(core_messages, key=lambda x: float(x.score), reverse=True)

        expanded_messages = self.score_importance(expanded_messages, registry)
        expanded_messages = sorted(expanded_messages, key=lambda x: float(x.score), reverse=True)

        return core_messages, expanded_messages

    def score_importance(self, messages: List[Message], registry: Registry) -> List[Message]:
        for msg in messages:
            msg.score = self.score_importance_single(msg, registry)
        return messages

    def score_importance_single(self, message: Message, registry: Registry) -> float:
        fact = message.main_fact
        outlier_score = fact.outlierness or 1

        if math.isnan(outlier_score):
            outlier_score = 0

        # importance of location types - where_type_score
        pass

        # importance of location size
        pass

        # importance of locations
        where_type_score = 1

        # importance of fact
        value_type_score = 1

        if "_trend" in fact.value_type:
            value_type_score *= 500

        # TODO ATM we do not consider national currencies
        if "_nac" in fact.value_type:
            return 0
        elif "_pps" in fact.value_type:
            value_type_score *= 10
        elif "_eur" in fact.value_type:
            value_type_score *= 40

        # TODO young age groups are a bit odd
        if "y-lt6" in fact.value_type:
            return 0
        elif "y6-10" in fact.value_type:
            return 0
        elif "y6-11" in fact.value_type:
            return 0
        elif "y11-15" in fact.value_type:
            return 0
        elif "y12-17" in fact.value_type:
            return 0
        elif "y-lt16" in fact.value_type:
            return 0
        elif "y16-24" in fact.value_type:
            return 0
        elif "y16-64" in fact.value_type:
            return 0
        elif "y-ge16" in fact.value_type:
            return 0
        elif "y-lt18" in fact.value_type:
            return 0

        if "_t_" in fact.value_type:
            return 0

        # importance of value
        what_score = value_type_score * outlier_score

        timestamp_score = 20
        # importance of time
        if fact.timestamp_type == "year":
            # For each year, the importance is simply 1 / diff,
            # where diff is the difference between the next year (from now)
            # and the year the fact discusses. That is, facts regarding
            # the current year get a multiplier of 1, the year before that
            # gets a multiplied of 0.5, the year before that 0.11... etc.
            timestamp_score *= min(1, (1 / (datetime.datetime.now().year + 1 - int(fact.timestamp)) ** 2))
            timestamp_score *= 2
        elif fact.timestamp_type == "month":
            # For months, the penalty is scaled linearly between the multipliers
            # of the year it belongs to and the previous year. The notable
            # complication here is that we consider the year to consists of 13
            # months, so that (for example) the year 2020 is considered to be
            # more newsworthy than the month 2020M12 by the same amount that
            # 2020M12 is more newsworthy than 2020M11.
            year, month = fact.timestamp.split("M")
            this_year = min(1.0, (1 / (datetime.datetime.now().year + 1 - int(year))) ** 2)
            prev_year = min(1.0, (1 / (datetime.datetime.now().year + 1 - (int(year) - 1))) ** 2)
            month_effect = (this_year - prev_year) / (int(month) + 1)
            timestamp_score *= this_year - month_effect

        # total importance score
        message_score = where_type_score * what_score * timestamp_score
        # message_score = "{:.5f}".format(message_score)

        if "_rank" in fact.value_type:
            message_score *= math.pow(0.7, fact.value - 1)

        if "_reverse" in fact.value_type:
            if "_change" in fact.value_type:
                message_score *= 0.7
            else:
                message_score *= 0.25

        # During fact selection, some facts were marked as inherently less important (for the current article)
        # Scale the importance if this was specified
        if message.importance_coefficient is not None:
            message_score *= message.importance_coefficient

        return message_score

# FYI: needed to change the year to 2020
import datetime
import logging
import math
from typing import List

from numpy.random.mtrand import RandomState

from collections import defaultdict

from core.models import Message
from core.pipeline import NLGPipelineComponent
from core.registry import Registry

log = logging.getLogger(__name__)


class EUImportanceSelector(NLGPipelineComponent):
    def run(
        self,
        registry: Registry,
        random: RandomState,
        language: str,
        core_messages: List[Message],
        expanded_messages: List[Message],
        previous_messages: List[Message],
    ):
        """
        Runs this pipeline component.
        """

        core_messages = self.score_importance(core_messages, registry)
        expanded_messages = self.score_importance(expanded_messages, registry)

        if previous_messages:
            # INCREASE COHESION: boost messages that refer to similar facts as previous ones
            key_components = defaultdict(lambda: defaultdict(int))
            for m in previous_messages:
                key_components[m.main_fact.value_type][m.main_fact.timestamp] = m.score

            log.debug("KEY_COMPONENTS: %s" % key_components)

            START_INCREASE = 10
            for m in core_messages:
                # defaultdict will return 0 for undefined values
                # 0/START_INCREASE+1 = 1 --> do nothing
                # if in previous messages this type of information has score > START INCREASE
                # then increase message weight
                coef = key_components[m.main_fact.value_type][m.main_fact.timestamp] / START_INCREASE + 1
                log.debug("*******M: %s SCORE: %s COEF: %s" % (m, m.score, coef))

                m.score = m.score * coef
                log.debug("NEW: %s" % m.score)

            # AVOID REDUNDANCE: can repeat at most one previous message
            EXP_BASE = 1.1
            prev_locs = set([m.main_fact.location for m in previous_messages])
            log.debug("PREV_LOCS: %s" % prev_locs)

            if prev_locs:
                expanded_in_prev = [m.score for m in expanded_messages if m.main_fact.location in prev_locs]
                if expanded_in_prev:
                    max_prev_scores = max(expanded_in_prev)
                    denominator = math.pow(EXP_BASE, max_prev_scores)

                    for m in expanded_messages:
                        if m.main_fact.location in prev_locs:
                            m.score *= math.pow(EXP_BASE, m.score) / denominator

        # sort and return
        core_messages = sorted(core_messages, key=lambda x: float(x.score), reverse=True)
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
            timestamp_score *= min(1, (1 / (datetime.datetime.now().year + 1 - int(fact.timestamp)) ** 2))
            timestamp_score *= 2
        elif fact.timestamp_type == "month":
            year, month = fact.timestamp.split("M")
            this_year = min(1.0, (1 / (datetime.datetime.now().year + 1 - int(year))) ** 2)
            prev_year = min(1.0, (1 / (datetime.datetime.now().year + 1 - (int(year) - 1))) ** 2)
            delta = this_year - prev_year
            delta_per_month = delta / 13
            month_effect = delta_per_month * (13 - int(month))
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

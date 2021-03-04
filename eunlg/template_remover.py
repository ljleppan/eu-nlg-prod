import itertools
import logging
from typing import List

from numpy.random.mtrand import RandomState

from core.models import Message
from core.pipeline import NLGPipelineComponent
from core.registry import Registry

log = logging.getLogger("root")


class TemplateRemover(NLGPipelineComponent):
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
        for msg in itertools.chain(core_messages, expanded_messages):
            msg.template = None

        return core_messages, expanded_messages

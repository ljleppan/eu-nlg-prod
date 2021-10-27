import logging
from typing import List

from numpy.random.mtrand import RandomState

from core.models import Message
from core.pipeline import NLGPipelineComponent
from core.registry import Registry

log = logging.getLogger("root")


class EmbeddingRemover(NLGPipelineComponent):
    def run(
        self,
        registry: Registry,
        random: RandomState,
        language: str,
        documentplan: List[Message],
        messages: List[Message],
    ):
        """
        Runs this pipeline component.
        """
        for msg in messages:
            msg.template = None
            if hasattr(msg, "embedding"):
                delattr(msg, "embedding")

        return documentplan, messages

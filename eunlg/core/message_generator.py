import logging

from .pipeline import NLGPipelineComponent

log = logging.getLogger("root")


class NoMessagesForSelectionException(Exception):
    pass


class MessageGenerator(NLGPipelineComponent):
    pass

import logging

from .pipeline import NLGPipelineComponent

log = logging.getLogger(__name__)


class NoMessagesForSelectionException(Exception):
    pass


class MessageGenerator(NLGPipelineComponent):
    pass

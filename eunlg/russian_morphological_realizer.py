import logging
from typing import Optional

from core.models import Slot
from core.morphological_realizer import LanguageSpecificMorphologicalRealizer

log = logging.getLogger("root")


class RussianMorphologicalRealizer(LanguageSpecificMorphologicalRealizer):
    def __init__(self):
        super().__init__("ru")

    def realize(self, slot: Slot) -> str:
        return slot.value

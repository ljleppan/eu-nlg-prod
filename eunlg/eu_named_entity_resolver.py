import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from numpy.random import Generator

from core.entity_name_resolver import EntityNameResolver
from core.models import Slot
from core.registry import Registry

log = logging.getLogger("root")


class EUEntityNameResolver(EntityNameResolver):
    def __init__(self):
        self._matcher = re.compile(r"\[ENTITY:([^:]+):([^\]]+)\]")
        self.realizers: Dict[str, Dict[str, Dict[str, EUEntityNameResolverComponent]]] = {
            "en": {
                "country": {
                    "full": EnglishEULocationNameResolver(),
                    "short": EnglishEULocationNameResolver(),
                    "pronoun": EUEntityNameListResolver(["the country"]),
                }
            },
            "hr": {
                "country": {
                    "full": CroatianEULocationNameResolver(),
                    "short": CroatianEULocationNameResolver(),
                    "pronoun": CroatianEULocationNameResolver(),
                }
            },
            "de": {
                "country": {
                    "full": GermanEULocationNameResolver(),
                    "short": GermanEULocationNameResolver(),
                    "pronoun": GermanEULocationNameResolver(),
                }
            },
            "fi": {
                "country": {
                    "full": FinnishEULocationNameResolver(),
                    "short": FinnishEULocationNameResolver(),
                    "pronoun": FinnishEULocationNameResolver(),
                }
            },
        }

    def is_entity(self, maybe_entity: Any) -> bool:
        if not isinstance(maybe_entity, str):
            log.debug("Value {} is not an entity".format(maybe_entity))
            return False
        return self._matcher.fullmatch(maybe_entity) is not None

    def parse_entity(self, entity: str) -> Tuple[str, str]:
        match = self._matcher.fullmatch(entity)
        if not match:
            raise ValueError("Value {} does not match entity regex".format(entity))
        if not len(match.groups()) == 2:
            raise Exception("Invalid number of matched groups?!")
        return match.groups()[0], match.groups()[1]

    def resolve_surface_form(
        self, registry: Registry, random: Generator, language: str, slot: Slot, entity: str, entity_type: str
    ) -> None:
        realizer = self.realizers.get(language, {}).get(entity_type, {}).get(slot.attributes.get("name_type"))
        if realizer is None:
            log.error(
                "No entity name resolver component for language {} and entity_type {}!".format(language, entity_type)
            )
            return

        realization = realizer.resolve(random, entity)
        slot.value = lambda x: realization
        log.debug('Realizer entity "{}" of type "{}" as "{}"'.format(entity, entity_type, realization))


class EUEntityNameResolverComponent(ABC):
    @abstractmethod
    def resolve(self, random: Generator, entity: str) -> str:
        """ Must be implemented in subclass. """


class EUEntityNameListResolver(EUEntityNameResolverComponent):
    def __init__(self, variants: List[str]) -> None:
        self.variants = variants

    def resolve(self, random: Generator, entity: str) -> str:
        return random.choice(self.variants)


class EUEntityNameDictionaryResolver(EUEntityNameResolverComponent):
    def __init__(self, dictionary: Dict[str, str]) -> None:
        self.dictionary = dictionary

    def resolve(self, random: Generator, entity: str) -> str:
        return self.dictionary.get(entity, "UNKNOWN-ENTITY:{}".format(entity))


class EnglishEULocationNameResolver(EUEntityNameDictionaryResolver):
    def __init__(self):
        from resources.country_name_resource import ENGLISH

        super().__init__(ENGLISH)


class CroatianEULocationNameResolver(EUEntityNameDictionaryResolver):
    def __init__(self):
        from resources.country_name_resource import CROATIAN

        super().__init__(CROATIAN)


class GermanEULocationNameResolver(EUEntityNameDictionaryResolver):
    def __init__(self):
        from resources.country_name_resource import GERMAN

        super().__init__(GERMAN)


class FinnishEULocationNameResolver(EUEntityNameDictionaryResolver):
    def __init__(self):
        from resources.country_name_resource import FINNISH

        super().__init__(FINNISH)

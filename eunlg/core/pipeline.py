import logging
from abc import ABC
from typing import Any, Dict, List, Optional, Tuple, Union

from numpy import random
from numpy.random import Generator

from .registry import Registry

log = logging.getLogger("root")


class NLGPipelineComponent(ABC):

    # TODO: We'd want this to be along the lines of "run(self, registry: Registry, ..., *args: Any) but that's not
    #  possible with the current implementation of
    def run(self, *args, **kwargs):
        """
        The real signature is (self, registry: Registry, random: numpy.random.Generator, language: str, *args)
        but that cannot be expressed as a Python type hint. Or rather, that type hint then requires a LITERAL "*args*"
        in all implementing subclasses which is not what we want to convey.

        See e.g. https://github.com/python/mypy/issues/5876 for discussion.
        """
        raise NotImplementedError

    def __str__(self) -> str:
        return str(self.__class__.__name__)


class LanguageSplitComponent(NLGPipelineComponent):
    def __init__(self, subcomponents: Dict[str, NLGPipelineComponent]):
        self.subcomponents = subcomponents

    def run(self, registry, random, language, *args):
        """
        The real signature is (self, registry: Registry, random: numpy.random.Generator, language: str, *args)
        but that cannot be expressed as a Python type hint. Or rather, that type hint then requires a LITERAL "*args*"
        in all implementing subclasses which is not what we want to convey.

        See e.g. https://github.com/python/mypy/issues/5876 for discussion.
        """

        lookup_language = language[:-5] if language.endswith("-head") else language
        if lookup_language not in self.subcomponents:
            raise Exception(
                "Attempted to access subcomponent for unknown language {} (formatted as {})".format(
                    language, lookup_language
                )
            )
        return self.subcomponents[lookup_language].run(registry, random, language, *args)


class NLGPipeline(object):
    def __init__(self, registry: Registry, *components: NLGPipelineComponent) -> None:
        self._registry = registry
        self._components = components

    @property
    def registry(self) -> Registry:
        return self._registry

    @property
    def components(self) -> Tuple[NLGPipelineComponent]:
        return self._components

    def run(self, initial_inputs: Any, language: str, prng_seed: Optional[int] = None) -> Union[List[Any], Tuple[Any]]:
        log.info("Starting NLG pipeline")
        log.debug("PRNG seed is {}".format(prng_seed))
        prng: Generator = random.default_rng(prng_seed)
        log.info("First random is {}".format(prng.integers(0, 1000000)))
        args = initial_inputs
        for component in self.components:
            log.info("Running component {}".format(component))
            try:
                output = component.run(self.registry, prng, language, *args)
            except Exception as ex:
                log.exception(ex)
                raise
            args = output
        log.info("NLG Pipeline completed")
        return output

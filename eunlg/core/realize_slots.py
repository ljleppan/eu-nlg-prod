import logging
import re
from abc import ABC, abstractmethod
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

from numpy.random import Generator

from .models import DocumentPlanNode, Message, Slot, TemplateComponent
from .pipeline import NLGPipelineComponent
from .registry import Registry

log = logging.getLogger("root")


class SlotRealizer(NLGPipelineComponent):
    def __init__(self) -> None:
        self._random = None
        self._registry = None
        self.slot_realizers = None

    def run(
        self, registry: Registry, random: Generator, language: str, document_plan: DocumentPlanNode
    ) -> Tuple[DocumentPlanNode]:
        """
        Run this pipeline component.
        """
        log.info("Realizing slots")
        self._registry = registry
        self._random = random
        # This *MUST* be a copy operation. Otherwise we just keep appending more NumberRealizers to it, leaking
        # memory all over the place and causing a slowdown. Previously, when this was re-initialized per-slot, the
        # slowdown ended up being about a factor of 500 over the generation of ~120 texts.
        self.slot_realizers = self._registry.get("slot-realizers")[:]
        self.slot_realizers.append(NumberRealizer())
        while self._recurse(document_plan, language.split("-")[0]):
            pass  # Repeat until no more changes
        return (document_plan,)

    def _recurse(self, this: DocumentPlanNode, language: str) -> bool:
        if not isinstance(this, Message):
            log.debug("Visiting '{}'".format(this))
            return any(self._recurse(child, language) for child in this.children)
        else:
            log.debug("Visiting {}".format(this))
            any_modified = False
            # Use indexes to iterate through the children since the template slots may be edited, added or replaced
            # during iteration. Ugly, but will do for now.
            idx = 0
            while idx < len(this.children):
                child = this.children[idx]
                if not isinstance(child, Slot):
                    idx += 1
                    continue
                modified_components = self._realize_slot(language, child)
                if modified_components != [child]:
                    any_modified = True
                this.children[idx : idx + 1] = modified_components
                idx += len(modified_components)
            return any_modified

    def _realize_slot(self, language: str, slot: Slot) -> List[TemplateComponent]:
        for slot_realizer in self.slot_realizers:
            assert isinstance(slot_realizer, SlotRealizerComponent)
            if language in slot_realizer.supported_languages() or "ANY" in slot_realizer.supported_languages():
                success, components = slot_realizer.realize(slot, self._random)
                if success:
                    return components
        return [slot]


class SlotRealizerComponent(ABC):
    @abstractmethod
    def supported_languages(self) -> List[str]:
        pass

    @abstractmethod
    def realize(self, slot: Slot, random: Generator) -> Tuple[bool, List[TemplateComponent]]:
        pass


class NumberRealizer(SlotRealizerComponent):
    def supported_languages(self) -> List[str]:
        return ["ANY"]

    def realize(self, slot: Slot, random: Generator) -> Tuple[bool, List[TemplateComponent]]:
        value = slot.value

        try:
            value = float(value)
        except ValueError:
            return False, []

        if slot.attributes.get("abs"):
            value = abs(value)

        if isinstance(value, (int, float)):
            if int(value) == value:
                slot.value = lambda x: int(value)
                return True, [slot]

            for rounding in range(5):
                if round(value, rounding) != 0:
                    slot.value = lambda x: round(value, rounding + 2)
                    return True, [slot]

        return True, [slot]


class RegexRealizer(SlotRealizerComponent):
    def __init__(
        self,
        registry: Registry,
        languages: Union[str, List[str]],
        regex: str,
        template: Union[str, Iterable[str]],
        group_requirements: Optional[Callable[..., bool]] = None,
        slot_requirements: Optional[Callable[[Slot], bool]] = None,
        attach_attributes_to: Optional[Iterable[int]] = None,
        add_attributes: Optional[Dict[int, Dict[str, str]]] = None,
    ) -> None:
        self.registry = registry
        self.languages = languages if isinstance(languages, list) else [languages]
        self.regex = regex
        self.templates = [template] if isinstance(template, str) else template
        self.group_requirements = group_requirements
        self.slot_requirements = slot_requirements
        self.attach_attributes_to = attach_attributes_to if attach_attributes_to is not None else []
        self.add_attributes = add_attributes if add_attributes is not None else {}

    def supported_languages(self) -> List[str]:
        return self.languages

    def realize(self, slot: Slot, random: Generator) -> Tuple[bool, List[TemplateComponent]]:
        # We can only parse the slot contents with a regex if the slot contents are a string
        if not isinstance(slot.value, str):
            return False, []

        match = re.fullmatch(self.regex, slot.value)

        if not match:
            return False, []

        # Check that the requirements placed on the groups are fulfilled
        if self.group_requirements is not None and not self.group_requirements(*match.groups()):
            return False, []

        # Check that the requirements placed on the slot are fulfilled
        if self.slot_requirements is not None and not self.slot_requirements(slot):
            return False, []

        template = random.choice(self.templates)
        log.debug("'Template: {}".format(template))

        string_realization = template.format(*match.groups())
        log.debug("String realization: {}".format(string_realization))

        components = []
        for idx, realization_token in enumerate(string_realization.split()):
            new_slot = slot.copy(include_fact=True)

            # By default, copy copies the attributes too. In case attach_attributes_to was set,
            # we need to explicitly reset the attributes for all those slots NOT explicitly mentioned
            if idx not in self.attach_attributes_to:
                new_slot.attributes = {}

            for attribute, value in self.add_attributes.get(idx, {}).items():
                new_slot.attributes[attribute] = value

            # An ugly hack that ensures the lambda correctly binds to the value of realization_token at this
            # time. Without this, all the lambdas bind to the final value of the realization_token variable, ie.
            # the final value at the end of the loop.  See https://stackoverflow.com/a/10452819
            new_slot.value = lambda f, realization_token=realization_token: realization_token
            components.append(new_slot)
        log.debug("Components: {}".format([str(c) for c in components]))

        return True, components


class LookupRealizer(SlotRealizerComponent):
    def __init__(
        self,
        registry: Registry,
        languages: Union[str, List[str]],
        dictionary: Dict[str, str],
        attach_attributes_to: Optional[Iterable[int]] = None,
    ) -> None:
        self.registry = registry
        self.languages = languages if isinstance(languages, list) else [languages]
        self.dictionary = dictionary
        self.attach_attributes_to = attach_attributes_to if attach_attributes_to is not None else []

    def supported_languages(self) -> List[str]:
        return self.languages

    def realize(self, slot: Slot, random: Generator) -> Tuple[bool, List[TemplateComponent]]:
        # We can only parse the slot contents with a regex if the slot contents are a string
        if not isinstance(slot.value, str):
            return False, []

        string_realization = self.dictionary.get(slot.value)
        if string_realization is None:
            return False, []

        log.debug("String realization: {}".format(string_realization))
        components = []
        for idx, realization_token in enumerate(string_realization.split()):
            new_slot = slot.copy(include_fact=True)

            # By default, copy copies the attributes too. In case attach_attributes_to was set,
            # we need to explicitly reset the attributes for all those slots NOT explicitly mentioned
            if idx not in self.attach_attributes_to:
                new_slot.attributes = {}

            # An ugly hack that ensures the lambda correctly binds to the value of realization_token at this
            # time. Without this, all the lambdas bind to the final value of the realization_token variable, ie.
            # the final value at the end of the loop.  See https://stackoverflow.com/a/10452819
            new_slot.value = lambda f, realization_token=realization_token: realization_token
            components.append(new_slot)
        log.debug("Components: {}".format([str(c) for c in components]))

        return True, components

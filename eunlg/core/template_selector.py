import logging
from functools import lru_cache
from typing import Iterator, List, Optional, Tuple

from numpy.random import Generator

from .models import DefaultTemplate, DocumentPlanNode, Message, Template
from .pipeline import NLGPipelineComponent
from .registry import Registry

log = logging.getLogger("root")

# If we're starting a new paragraph and haven't mentioned the location for more than this number of
# messages, say it again (if possible), even if it's not changed
LOC_IF_NOT_SINCE = 6


class TemplateSelector(NLGPipelineComponent):
    """
    Adds a matching Template to each Message in the DocumentPlan.

    """

    def run(
        self,
        registry: Registry,
        random: Generator,
        language: str,
        document_plan: DocumentPlanNode,
        all_messages: List[Message],
    ) -> Tuple[DocumentPlanNode]:
        """
        Run this pipeline component.
        """
        if log.isEnabledFor(logging.DEBUG):
            document_plan.print_tree()

        templates = registry.get("templates")[language.lower()]

        template_checker = TemplateMessageChecker(templates, all_messages)
        log.info("Selecting templates from {} templates".format(len(templates)))
        self._recurse(random, language, document_plan, all_messages, template_checker, None)

        return (document_plan,)

    def _recurse(
        self,
        random: Generator,
        language: str,
        this: DocumentPlanNode,
        all_messages: List[Message],
        template_checker: "TemplateMessageChecker",
        context: Optional[Message],
    ) -> Optional[Message]:
        """
        Recursively works through the tree, adding Templates to Messages.
        """
        # Check all children of this root
        for idx, child in enumerate(this.children):
            if isinstance(child, Message):
                templates = list(template_checker.all_templates_for_message(child))
                if len(templates) == 0:
                    # If there are no templates, something's gone horribly wrong
                    # The document planner should have made sure this didn't happen, but the only thing we can
                    # at this point is skip the fact
                    log.error("Found no templates to express {}".format(child))
                    raise Exception("No template for message {}".format(child))
                else:
                    templates = self._filter_by_context(templates, context, child, is_first=(idx == 0))
                    random.shuffle(templates)
                    template = templates[0]
                    self._add_template_to_message(child, template, all_messages)
                    context = child
            else:
                # This child is NOT a message and we should just recurse
                context = self._recurse(random, language, child, all_messages, template_checker, context)
        return context

    def _value_type_is_substantially_similar(self, first: Message, second: Message) -> bool:
        # TODO: This logic might very well be dataset specific and should be placed somewhere else
        first_type = first.main_fact.value_type
        second_type = second.main_fact.value_type

        first_type = first_type if ":comp_" not in first_type else first_type[:-8]
        second_type = second_type if ":comp_" not in second_type else second_type[:-8]

        return first_type == second_type

    def _filter_by_context(
        self, templates: List[Template], context: Optional[Message], this: Message, is_first: bool
    ) -> List[Template]:
        log.debug("Filtering templates by context. Initial templates:")
        for t in templates:
            log.debug("\t{}".format(t))

        # Filter s.t. location is either mandatory present or absent based on context
        if (
            context
            and context.main_fact.timestamp == this.main_fact.timestamp
            and context.main_fact.timestamp_type == this.main_fact.timestamp_type
        ):
            proposed = [template for template in templates if not template.has_slot_of_type("time")]
        else:
            proposed = [template for template in templates if template.has_slot_of_type("time")]

        # Only update proper list if above filter did *not* result in empty set
        if proposed:
            log.debug("Non-empty filtered list after location filter, checkpointing")
            templates = proposed

        # Filter s.t. location is either mandatory present or absent based on context
        if (
            context
            and context.main_fact.location == this.main_fact.location
            and context.main_fact.location_type == this.main_fact.location_type
        ):
            proposed = [template for template in templates if not template.has_slot_of_type("location")]
        else:
            proposed = [template for template in templates if template.has_slot_of_type("location")]

        # Only update proper list if above filter did *not* result in empty set
        if proposed:
            log.debug("Non-empty filtered list after location filter, checkpointing")
            templates = proposed

        # Filter s.t. value_type is either mandatory present or absent based on context
        if context and self._value_type_is_substantially_similar(context, this) and not is_first:
            proposed = [template for template in templates if not template.has_slot_of_type("value_type")]
        else:
            proposed = [template for template in templates if template.has_slot_of_type("value_type")]

        # Only update proper list if above filter did *not* result in empty set
        if proposed:
            log.debug("Non-empty filtered list after location filter, checkpointing")
            templates = proposed

        log.debug("Filtered templates:")
        for t in templates:
            log.debug("\t{}".format(t))

        return templates

    @staticmethod
    def _add_template_to_message(message: Message, template_original: Template, all_messages: List[Message]) -> None:
        """
        Adds a matching template to a message, also adding the facts used by the template to the message.

        :param message: The message to be fitted with a template
        :param template_original: The template to be added to the message.
        :param all_messages: Other available messages, some of which will be needed to match possible secondary rules
               in the template.
        :return: Nothing
        """
        template = template_original.copy()
        used_facts = template.fill(message, all_messages)
        if used_facts:
            log.debug("Successfully linked template to message")
        else:
            log.error(
                "Chosen template '{}' for fact '{}' could not be used! "
                "Falling back to default templates".format(template.display_template(), message.main_fact)
            )
            template = DefaultTemplate("")
        message.template = template
        message.facts = used_facts


class TemplateMessageChecker(object):
    """
    Doesn't actually fill in templates, but just checks, for a given message (and a list of other available messages),
    whether there is a template that can be used to realise it.

    Init with templates taken from the registry for the relevant language.

    The checks are cached on message and location_required.

    """

    def __init__(self, templates: List[Template], all_messages: List[Message]) -> None:
        self.all_messages = all_messages
        self.templates = templates
        self._cache = {}

    @lru_cache(maxsize=1024)
    def exists_template_for_message(self, message: Message) -> bool:
        """
        Check for templates that apply to the given message. To make things faster, we don't try to find
        all available templates, but return as soon as we find one.
        """
        try:
            # Try getting the first template
            next(self.all_templates_for_message(message))
        except StopIteration:
            # No template found at all
            return False
        return True

    def all_templates_for_message(self, message: Message) -> Iterator[Template]:
        for template in self.templates:
            # See if the template can express this message (with the help of the other available messages)
            if template.check(message, self.all_messages):
                # Got a matching template: this message can be expressed
                yield template

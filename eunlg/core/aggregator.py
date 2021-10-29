import logging
from collections import defaultdict
from typing import List, Tuple

from numpy.random import Generator

from core.models import DocumentPlanNode, Literal, Message, Relation, Slot, Template, TemplateComponent, Fact
from core.pipeline import NLGPipelineComponent
from core.registry import Registry

log = logging.getLogger(__name__)


class Aggregator(NLGPipelineComponent):
    def run(
        self, registry: Registry, random: Generator, language: str, document_plan: DocumentPlanNode
    ) -> Tuple[DocumentPlanNode]:
        if log.isEnabledFor(logging.DEBUG):
            document_plan.print_tree()

        log.debug("Aggregating")
        self._aggregate(registry, language, document_plan)

        if log.isEnabledFor(logging.DEBUG):
            document_plan.print_tree()

        return (document_plan,)

    def _aggregate(self, registry: Registry, language: str, document_plan_node: DocumentPlanNode) -> DocumentPlanNode:
        log.debug("Visiting {}".format(document_plan_node))

        # Cannot aggregate a single Message
        if isinstance(document_plan_node, Message):
            return document_plan_node

        if document_plan_node.relation == Relation.ELABORATION:
            return self._aggregate_elaboration(registry, language, document_plan_node)
        elif document_plan_node.relation == Relation.LIST:
            return self._aggregate_list(registry, language, document_plan_node)
        return self._aggregate_sequence(registry, language, document_plan_node)

    def _aggregate_sequence(
        self, registry: Registry, language: str, document_plan_node: DocumentPlanNode
    ) -> DocumentPlanNode:
        log.debug("Visiting {}".format(document_plan_node))

        num_children = len(document_plan_node.children)
        new_children = []  # type: List[Message]

        for idx in range(0, num_children):
            if idx > 0:
                previous_child = new_children[-1]
            else:
                previous_child = None
            current_child = document_plan_node.children[idx]

            if not isinstance(current_child, Message):
                log.debug("This is not a message, we need to go deeper")
                new_children.append(self._aggregate(registry, language, current_child))
                continue

            # TODO: ^ I have no clue what the above logic is doing, but it seems to work so not gonna touch it.
            # TODO: current_child should be a Message but seems to be a DocumentPlanNode instead ¯\_(ツ)_/¯

            log.debug("Inspecting potential aggregation:")
            log.debug("\t{}".format(previous_child))
            log.debug("\t{}".format(current_child))

            if previous_child is None:
                log.debug("Can't aggregate first child, as there's nothing to aggregate with")
                new_children.append(current_child)
            elif previous_child.prevent_aggregation or current_child.prevent_aggregation:
                log.debug("Aggregation prevented, most likely previous child is a result of a previous aggregation.")
                new_children.append(current_child)
            elif self._same_prefix(previous_child, current_child):
                log.debug("Aggregation allowed, shared prefix")
                # Some slots might have an implicit time value, by virtue of not having a {time} slot.
                # In such cases, we need to consider the aggregation carefully. There are 5 maojr cases:
                # 1. "in April", "in April" -> This shouldn't happen, but we can just combine normally
                # 2. "in April", implicit -> We need to *SWAP* the elements for a better realization.
                # 3. implicit, implicit -> Combine as usual, if possible
                # 4. "in April", "in June" -> Combine as usual, if possible
                # 5. implicit, "in June" -> Should not be combined, as aggregation would make implicit refer to June
                #    rather than the previously mentioned entity.
                if not self._has_implicit_time(previous_child) and self._has_implicit_time(current_child):
                    # Case #2
                    log.debug("Swapping the location of two fragments for better time realization")
                    new_children[-1] = self._combine(registry, language, current_child, new_children[-1])
                elif self._has_implicit_time(previous_child) and not self._has_implicit_time(current_child):
                    # Case #5
                    log.debug("Incompatible time expressions, can't combine")
                    new_children.append(current_child)
                else:
                    # Cases #1, #3 and #4
                    new_children[-1] = self._combine(registry, language, new_children[-1], current_child)
            else:
                log.debug("No shared prefix, can't aggregate")
                new_children.append(current_child)

        document_plan_node.children.clear()
        document_plan_node.children.extend(new_children)
        return document_plan_node

    def _aggregate_elaboration(
        self, registry: Registry, language: str, document_plan_node: DocumentPlanNode
    ) -> DocumentPlanNode:
        # TODO: Re-implement this
        raise NotImplementedError

    def _aggregate_list(self, registry: Registry, language: str, document_plan_node: DocumentPlanNode) -> Message:
        # TODO: Re-implement this
        raise NotImplementedError

    def _same_prefix(self, first: Message, second: Message) -> bool:
        try:
            if first.template.components[0].value == second.template.components[0].value:
                log.debug("Shared prefix")
                return True
            else:
                log.debug("No shared prefix")
                return False
        except AttributeError:
            log.debug("AttributeError, assuming no shared prefix")
            return False

    def _has_implicit_time(self, message: Message) -> bool:
        return not message.template.has_slot_of_type("time")

    def _combine(self, registry: Registry, language: str, first: Message, second: Message) -> Message:
        log.debug("Combining two templates:")
        log.debug("\t{}".format([c.value for c in first.template.components]))
        log.debug("\t{}".format([c.value for c in second.template.components]))

        combined = [c for c in first.template.components]
        # TODO: 'idx' and 'other_component' are left uninitialized if second.template.components is empty.
        for idx, other_component in enumerate(second.template.components):
            if idx >= len(combined):
                break
            this_component = combined[idx]

            if not self._are_same(this_component, other_component):
                break

        # TODO At the moment everything is considered either positive or negative, which is sometimes weird.
        #  Add neutral sentences.
        conjunctions = registry.get("conjunctions").get(language, None)
        if not conjunctions:
            conjunctions = (defaultdict(lambda x: "NO-CONJUNCTION-DICT"),)

        if first.polarity != first.polarity:
            combined.append(Literal(conjunctions.get("inverse_combiner", "MISSING-INVERSE-CONJUCTION")))
        else:
            combined.append(Literal(conjunctions.get("default_combiner", "MISSING-DEFAULT-CONJUCTION")))
        combined.extend(second.template.components[idx:])
        log.debug("Combined thing is {}".format([c.value for c in combined]))
        new_message = Message(
            facts=first.facts + [fact for fact in second.facts if fact not in first.facts],
            importance_coefficient=first.importance_coefficient,
        )
        new_message.template = Template(combined)
        new_message.prevent_aggregation = True
        return new_message

    def _are_same(self, c1: TemplateComponent, c2: TemplateComponent) -> bool:
        if c1.value != c2.value:
            # Are completely different, are not same
            return False

        if isinstance(c1, Slot) and isinstance(c2, Slot):

            if not isinstance(c1.fact, Fact) or not isinstance(c2.fact, Fact):
                return c1.value == c2.value

            # Aggregating numbers is a mess, and can easily lead to sentences like "The search found 114385 articles in
            # French and from the newspaper L oeuvre", which implies that there is a set of 114385 articles s.t. every
            # article in the set is both in french and published in L'ouvre. Unfortunately, it's possible to end up in
            # this situation even if the underlying data actually says that there were two sets of size 114385 s.t.
            # in one all are in french and in the other all were published in L'ouvre. That is, we do now in fact know
            # whether the sets contain the same documents or not.
            if c1.slot_type == "value":
                return False

            # We check the actual underlying fact contets for simple slot_types. Non-simple slot_types are, f.e.x,
            # "time", "location" and "unit".
            if c1.slot_type in c1.fact._fields and c2.slot_type in c2.fact._fields:
                if getattr(c1.fact, c1.slot_type) != getattr(c2.fact, c2.slot_type):
                    return False

        # They are apparently same, check cases
        c1_case = "no-case"
        c2_case = "no-case"
        try:
            c1_case = c1.attributes.get("case", "")
        except AttributeError:
            pass
        try:
            c2_case = c2.attributes.get("case", "")
        except AttributeError:
            pass

        # False if different cases or one had attributes and other didn't
        return c1_case == c2_case

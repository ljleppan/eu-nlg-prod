import logging
import operator
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Union

log = logging.getLogger("root")


class Document(object):
    def __init__(self, language: str, document_plan: Optional["DocumentPlanNode"] = None):
        self.language = language
        self.document_plan = document_plan

    def messages(self):
        return self._recursively_find_messages(self.document_plan)

    def _recursively_find_messages(self, root: "DocumentPlanNode") -> List["Message"]:
        if isinstance(root, Message):
            yield root
        else:
            for child in root.children:
                yield from self._recursively_find_messages(child)


class Relation(Enum):
    """
    Defines possible relations between the children of a DocumentPlan node.
    """

    ELABORATION = 1
    EXEMPLIFICATION = 2
    CONTRAST = 3
    SEQUENCE = 4
    LIST = 5


class DocumentPlanNode(object):
    """
    A Node in the document plan. Has an ordered list of children, collectively connected by a Relation.
    """

    def __init__(
        self, children: Optional[List["DocumentPlanNode"]] = None, relation: Relation = Relation.SEQUENCE
    ) -> None:
        self._children = children if children else []
        self._relation = relation

    @property
    def children(self) -> List["DocumentPlanNode"]:
        return self._children

    @property
    def relation(self) -> Relation:
        return self._relation

    def __str__(self) -> str:
        return self.relation.name

    def print_tree(self, indent: str = "", last: str = "updown") -> None:
        """
        Prints the DocumentPlanNode as a tree.
        Modified from http://stackoverflow.com/a/30893896
        """

        def rec_count(node: DocumentPlanNode) -> int:
            count = 0
            if isinstance(node, Message) or isinstance(node, Template):
                return count
            for child in node.children:
                count += 1 + rec_count(child)
            return count

        up = []
        down = []
        # If the Message has already been assigned a Template, we will print that.
        # Otherwise, print the main Fact in the Message.
        if isinstance(self, Message):
            output = self.template if self.template is not None else self.main_fact
        else:
            output = self

            # Creation of balanced lists for "up" branch and "down" branch.
            branch_sizes = {child: rec_count(child) + 1 for child in self.children}
            up = list(self.children)
            while up and sum(branch_sizes[node] for node in down) < sum(branch_sizes[node] for node in up):
                down.insert(0, up.pop())

            # Printing of "up" branch.
            for child in up:
                next_last = "up" if up.index(child) == 0 else ""
                next_indent = "{0}{1}{2}".format(indent, " " if "up" in last else "│", " " * len(str(self)))
                child.print_tree(indent=next_indent, last=next_last)

        # Printing of current node.
        if last == "up":
            start_shape = "┌"
        elif last == "down":
            start_shape = "└"
        elif last == "updown":
            start_shape = " "
        else:
            start_shape = "├"

        if up:
            end_shape = "┤"
        elif down:
            end_shape = "┐"
        else:
            end_shape = ""

        print("{0}{1}{2}{3}".format(indent, start_shape, str(output), end_shape))

        if not isinstance(self, Message):
            # Printing of "down" branch.
            for child in down:
                next_last = "down" if down.index(child) == len(down) - 1 else ""
                next_indent = "{0}{1}{2}".format(indent, " " if "down" in last else "│", " " * len(str(self)))
                child.print_tree(indent=next_indent, last=next_last)


class Message(DocumentPlanNode):
    """
    Contains a list of Fact tuples, a template for presenting the facts, and various values that are computed based on
    the facts.

    _importance_coefficient: scales the importance of the message, allowing less relevant messages to be included in the
    article only if their importance is high enough to outweigh having a lower coefficient
    _polarity: tells whether the message is considered positive, neutral or negative. For now the value is -1, 0, or 1.
    _score: is the newsworthiness score, that is used to decide which messages to include in the news article
    _template: is a Template object that contains information on how to display the message

    """

    def __init__(
        self,
        facts: Union[List["Fact"], "Fact"],
        importance_coefficient: float = 1.0,
        score: float = 0.0,
        polarity: float = 0.0,
    ) -> None:
        super().__init__()

        self._facts = [facts] if isinstance(facts, Fact) else facts
        self._main_fact = self._facts[0]
        self._template = None  # type: Optional[Template]

        self.importance_coefficient = importance_coefficient
        self.score = score
        self.polarity = polarity
        self.prevent_aggregation = False  # type: bool

    @property
    def facts(self) -> List["Fact"]:
        return self._facts

    @facts.setter
    def facts(self, facts: Union[List["Fact"], "Fact"]) -> None:
        self._facts = [facts] if isinstance(facts, Fact) else facts
        self._main_fact = self._facts[0]

    # Added for backwards compatibility, returns by default the primary fact for this Message.
    @property
    def main_fact(self) -> "Fact":
        return self._main_fact

    @main_fact.setter
    def main_fact(self, fact: "Fact") -> None:
        self._main_fact = fact
        if fact not in self._facts:
            self._facts.insert(0, fact)

    @property
    def template(self) -> "Template":
        return self._template

    @template.setter
    def template(self, template: "Template") -> None:
        self._template = template

    @property
    def children(self) -> List["TemplateComponent"]:
        if self.template:
            return self.template.components
        else:
            return []

    def __repr__(self) -> str:
        if self.template:
            return "<Message: " + self.template.__repr__() + ">"
        elif self.main_fact:
            return "<Message: " + self.main_fact.__repr__() + ">"
        return "<Message>"

    def __str__(self) -> str:
        return self.__repr__()


# TODO: This has become project-specific and needs to be defined outside of Core. If it's needed within Core, some type
# of an injection thingymabob is needed.
class Fact(NamedTuple):
    location: str
    location_type: str
    value: Any
    value_type: str
    agent: Any
    agent_type: str
    timestamp: Any
    timestamp_type: str
    outlierness: float


class Template(DocumentPlanNode):
    """
    A template consisting of TemplateComponent elements and a list of rules about the facts that can be presented
    using the template.
    """

    def __init__(
        self,
        components: List["TemplateComponent"],
        rules: Optional[List[Tuple[List["Matcher"], List[int]]]] = None,
        slot_map: Optional[Dict[str, "Slot"]] = None,
    ) -> None:

        super().__init__()

        self._rules = rules if rules is not None else []
        self._facts = []
        self._slot_map = slot_map if slot_map is not None else {}
        self._components = components
        for c in self._components:
            c.parent = self
        self._slots = None

    def get_slot(self, slot_type: str) -> "Slot":
        """
        First version of the slot_map: here we are making an assumption that there is only one instance per slot type,
        which is clearly not true after aggregation. Whether this will be a problem is still a bit unclear.

        :param slot_type:
        :return:
        """
        if slot_type not in self._slot_map.keys():
            slot_of_correct_type = next((slot for slot in self.slots if slot.slot_type == slot_type), None)
            self._slot_map[slot_type] = slot_of_correct_type
        if self._slot_map[slot_type] is None:
            raise KeyError('No slot of type "{}" in Template {}'.format(slot_type, self))
        return self._slot_map[slot_type]

    def add_slot(self, idx: int, slot: "Slot") -> None:
        if len(self._components) > idx:
            self._components.insert(idx, slot)
        else:
            self._components.append(slot)
        slot.parent = self
        self.slots.append(slot)

    def move_slot(self, from_idx: int, to_idx: int) -> None:
        self.components.insert(to_idx, self.components.pop(from_idx))

    @property
    def components(self) -> List["TemplateComponent"]:
        return self._components

    @property
    def facts(self) -> List[Fact]:
        return self._facts

    def check(self, primary_message: Message, all_messages: List[Message], fill_slots: bool = False) -> List[Fact]:
        """
        Like fill(), but doesn't modify the template data structure, just checks whether the given message,
        with the support from other messages, is compatible with the template.

        :param primary_message: The message that the first rule in the template should match
        :param all_messages: A list of other available messages
        :param fill_slots:
        :return: True, if the template can be used for the primary_message. False otherwise.
        """
        # ToDo: Could we somehow cache the information about which messages to use in addition to the primary, so
        #  that we could then fill the message straight away without going through the messages again?
        # OR: Fill the templates in this phase and then just choose one of them. Filling shouldn't be that much
        # slower than checking.
        primary_fact = primary_message.main_fact

        # TODO: Had these happen a few time, better to crash early and explicitly
        assert not isinstance(primary_fact, str)

        used_facts = []

        # The first rule has to match the primary message
        if not all(matcher(primary_fact, used_facts) for matcher in self._rules[0][0]):
            return []

        if fill_slots:
            for slot_index in self._rules[0][1]:
                component = self._components[slot_index]
                if isinstance(component, Slot):
                    component.fact = primary_fact

        used_facts.append(primary_fact)

        # Check the other rules
        if len(self._rules) > 1:
            for (matchers, slot_indices) in self._rules[1:]:
                # Try each message in turn
                for mess in all_messages:
                    if all(matcher(mess.main_fact, used_facts) for matcher in matchers):
                        # Found a suitable message: fill the slots
                        if fill_slots:
                            for slot_index in slot_indices:
                                component = self._components[slot_index]
                                if isinstance(component, Slot):
                                    component.fact = mess.main_fact
                        if mess.main_fact not in used_facts:
                            used_facts.append(mess.main_fact)
                        # Move onto the next rule
                        break
                else:
                    # No available message matched the rule: we can't use this template:
                    return []

        if fill_slots:
            self._facts = used_facts

        return used_facts

    def fill(self, primary_message: Message, all_messages: List[Message]) -> List[Fact]:
        """
        Search for messages needed to fulfill all of the rules in the template, and link the Slot components to the
        matching Facts

        :param primary_message: The message that the first rule in the template should match
        :param all_messages: A list of other available messages
        :return: A list of the Facts that match the rules in the template
        """

        return self.check(primary_message, all_messages, fill_slots=True)

    @property
    def slots(self) -> List["Slot"]:
        # Cache the list of slots to avoid doing too many ifinstance checks
        # The slots are not guaranteed to be in the same order as they appear in the self._components
        if self._slots is None:
            self._slots = [c for c in self.components if isinstance(c, Slot)]
        return self._slots

    def has_slot_of_type(self, slot_type: str) -> bool:
        return any(isinstance(c, Slot) and c.slot_type == slot_type for c in self._components)

    def copy(self) -> "Template":
        """Makes a deep copy of this Template. The copy does not contain any messages."""
        component_copy = [c.copy() for c in self.components]
        return Template(component_copy, self._rules)

    def __str__(self) -> str:
        return "<Template: {}>".format(self.display_template())

    def __repr__(self) -> str:
        return str(self)

    def display_template(self) -> str:
        """String representation of whole template, mainly for debugging"""
        return " ".join(str(c) for c in self.components)


class DefaultTemplate(Template):
    def __init__(self, canned_text: str) -> None:
        super().__init__(components=[Literal(canned_text)])


class TemplateComponent(object):
    """An abstract TemplateComponent. Should not be used directly."""

    def __init__(self) -> None:
        self._parent = None

    @property
    def value(self):
        raise NotImplementedError

    @value.setter
    def value(self, value):
        raise NotImplementedError

    @property
    def parent(self) -> "TemplateComponent":
        return self._parent

    @parent.setter
    def parent(self, parent: "TemplateComponent") -> None:
        self._parent = parent

    def copy(self):
        raise NotImplementedError

    def __str__(self) -> str:
        return "[AbstractTemplateComponent]"


class Slot(TemplateComponent):
    """
    A TemplateComponent that can be filled by a Fact that fulfills a set of
    requirements.
    """

    # Todo: Are the values in "attributes" of a known type?
    def __init__(
        self, to_value: "SlotSource", attributes: Optional[Dict[str, Any]] = None, fact: Optional[Fact] = None
    ) -> None:
        """
        :param to_value: A callable that defines how to transform the message
            that fills this slot into a textual representation.
        """

        super().__init__()
        self.attributes = attributes or {}
        self._to_value = to_value
        self.fact = fact

    @property
    def slot_type(self) -> str:
        return self._to_value.field_name

    @property
    def value(self) -> Union[str, int, float]:
        return self._to_value(self.fact)

    @value.setter
    def value(self, f: Callable) -> None:
        self._to_value = f

    def copy(self, include_fact=False) -> "Slot":
        # TODO: Is it intended that Fact is not copied over?
        if not include_fact:
            return Slot(self._to_value, self.attributes.copy())
        else:
            return Slot(self._to_value, self.attributes.copy(), self.fact)

    def __str__(self) -> str:
        try:
            value = self.value
        except AttributeError:
            value = self._to_value
        return "Slot({}{})".format(value, "".join(", {}={}".format(k, v) for (k, v) in self.attributes.items()))


class LiteralSlot(Slot):
    def __init__(self, value: str, attributes: Optional[Dict[str, str]] = None) -> None:
        super().__init__(LiteralSource(value), attributes)


class Literal(TemplateComponent):
    """A string literal."""

    def __init__(self, string: str) -> None:
        super().__init__()
        self._string = string

    @property
    def slot_type(self) -> str:
        return "Literal"

    @property
    def value(self) -> str:
        return self._string

    def copy(self) -> "Literal":
        return Literal(self.value)

    def __str__(self) -> str:
        return self.value


class SlotSource(ABC):
    """ Source of the slot value """

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name

    @abstractmethod
    def __call__(self, fact: Fact) -> Union[str, int]:
        raise NotImplementedError("abstract slot source")


class FactFieldSource(SlotSource):
    def __init__(self, field_name: str) -> None:
        super().__init__(field_name)

    def __call__(self, fact: Fact) -> Union[str, int]:
        return getattr(fact, self.field_name)

    def __str__(self) -> str:
        return "fact.{}".format(self.field_name)


class LiteralSource(SlotSource):
    """Ignore the message and return a literal value"""

    def __init__(self, value: str) -> None:
        super().__init__("literal")
        self.value = value

    def __call__(self, fact: Fact) -> Union[str, int]:
        return self.value

    def __str__(self) -> str:
        return '"{}"'.format(self.value)


class TimeSource(SlotSource):
    """
    Special type of SlotSource for time entries.
    """

    def __init__(self) -> None:
        super().__init__("time")

    def __call__(self, fact: Fact) -> str:
        return "[TIME:{}:{}]".format(getattr(fact, "timestamp_type"), getattr(fact, "timestamp"))

    def __str__(self):
        return "fact.time"


class UnitSource(SlotSource):
    """
    Special type of SlotSource for time entries.
    """

    def __init__(self) -> None:
        super().__init__("unit")

    def __call__(self, fact: Fact) -> str:
        return "[UNIT:{}]".format(getattr(fact, "value_type"))

    def __str__(self):
        return "fact.unit"


class LhsExpr(object):
    """Symbolic representation of expressions on the LHS of message constraints.

    We could just represent these expressions using lambda expressions, but this symbolic representation makes
    it easier to view them after they've been read in, to debug template reading, view templates, and so on.

    The __call__ methods perform the actual processing of the message to get a value to compare to the RHS
    of the constraint.
    """

    def __call__(self, fact: "Fact", all_facts: List["Fact"]) -> None:
        # Required in subclasses
        raise NotImplementedError()

    def __str__(self) -> str:
        # Required in subclasses
        raise NotImplementedError

    def __repr__(self) -> str:
        return str(self)


class FactField(LhsExpr):
    def __init__(self, field_name: str) -> None:
        self.field_name = field_name

    def __call__(self, fact: "Fact", all_facts: List["Fact"]) -> str:
        return getattr(fact, self.field_name)

    def __str__(self) -> str:
        return "fact.{}".format(self.field_name)


class ReferentialExpr(object):
    # TODO: Is this also supposed to be an LhsExrp?
    def __init__(self, reference_idx: int, field_name: str) -> None:
        self.field_name = field_name
        self.reference_idx = reference_idx

    def __call__(self, fact: "Fact", all_references: List[object]) -> str:
        return getattr(all_references[self.reference_idx], self.field_name)

    def __str__(self) -> str:
        return "all[{}].{}".format(self.reference_idx, self.field_name)


def _equal_op(a: Any, b: Any) -> bool:
    if type(b) is str:
        return re.match("^" + b + "$", str(a)) is not None
    else:
        return operator.eq(a, b)


def _not_equal_op(a: Any, b: Any) -> bool:
    return not _equal_op(a, b)


class Matcher(object):
    OPERATORS = {
        "=": _equal_op,
        "!=": _not_equal_op,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
        "in": lambda a, b: operator.contains(b, a),
    }

    def __init__(self, lhs: LhsExpr, op: str, value: Any) -> None:
        if op not in Matcher.OPERATORS:
            raise ValueError(
                "invalid matcher operator '{}'. Must be one of: {}".format(op, ", ".join(Matcher.OPERATORS))
            )
        self.value = value
        self.op = op
        self.lhs = lhs

    def __call__(self, fact: Fact, all_facts: List[Fact]):
        # Process the LHS expression
        result = self.lhs(fact, all_facts)
        if callable(self.value):
            value = self.value(fact, all_facts)
        else:
            value = self.value
        # Perform the relevant comparison operator
        return Matcher.OPERATORS[self.op](result, value)

    def __str__(self):
        return "lambda msg, all: {} ({})     {}      {} ({})".format(
            self.lhs, type(self.lhs), self.op, self.value, type(self.value)
        )

    def __repr__(self):
        return str(self)

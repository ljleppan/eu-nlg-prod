"""
This is a new version of the template reading code for multilingual template files -- files
with many languages' templates specified together.

I've copied the entire module, to allow us to phase in its use as we convert the templates
and avoid breaking the existing code and disabling Valtteri at a critical time!

The key difference from the old format is that fact constraint lines now start with a "|".

You can specify what language templates are for by starting the template line with "<lang_id>: ".
If you don't give a language for a template, it defaults to the previous one used.
A single line in a block (i.e. surrounded by blank lines) containing such an identifier, with nothing after
it, changes the current language -- i.e. the default language for everything that follows.

What happens if we want to use a colon after the first word of a template, so that it looks like a
language id?
If you're specifying a language, there's no problem, as we've already got it by the time we get to
your colon.
Otherwise, you can simply start the template line with a colon, which causes the current default
language to be used.

For each template block, we detect whether this template is specified in the new or old format, and ignore templates
using the old format.

Optional template parts
=======================
You can compactly specify alternative versions of a template by enclosing part of it in square brackets.
When it is read in, it will be expanded out into two templates, one with the optional part and one
without.

You may include multiple optional parts in the same template and all combinations will be
generated in expansion. However, you may not nest brackets.

This is exactly equivalent to putting the expanded templates explicitly on consecutive lines (all with
the same language specifier).

"""
import logging
import re
import warnings
from typing import Dict, List, Optional, Tuple

from .models import (
    FactField,
    FactFieldSource,
    Literal,
    LiteralSource,
    Matcher,
    ReferentialExpr,
    Slot,
    Template,
    TimeSource,
    UnitSource,
)

log = logging.getLogger("root")


def canonical_map(map_dict):
    return dict(
        (alt_val, canonical) for (canonical, alt_vals) in map_dict.items() for alt_val in ([canonical] + alt_vals)
    )


FACT_FIELD_ALIASES = {
    "location_type": [],
    "location": [],
    "timestamp": [],
    "timestamp_type": [],
    "value_type": [],
    "value": [],
    "time": [],
    "unit": [],
}
FACT_FIELD_MAP = canonical_map(FACT_FIELD_ALIASES)
LOCATION_TYPES = {"C": ["country"], "D": ["district"], "M": ["municipality", "mun"]}
LOCATION_TYPE_MAP = canonical_map(LOCATION_TYPES)
FACT_FIELDS = FACT_FIELD_ALIASES.keys()

RULE_PREFIX = "|"

field_name_re = re.compile(r"[^ |=]+")
rhs_value_re = re.compile(r"[^,]+")

value_groups = {}

"""
Referential values start with 1 or more numerals, followed by a dot.
The dot is followed by any one of the strings "who", "where" or "what",
or their variants with "_type" appended.

1st capture group is the part before the dot.
2nd capture group is the part after the dot.
"""
referential_value_re = re.compile(r"^(\d+)\.((?:who|where|what)(?:_type)?|when(?:_1|_2|_type))$")
# TODO: referential_value_re needs to be either more generic or dynamically built from the fields of Fact

lang_spec_re = re.compile(r"(?P<lang>\S*):\s(?P<template>.*)")
multi_space_re = re.compile(r"\s+")


def read_templates_file(filename: str, initial_language: Optional[str] = None, return_what_types: bool = False):
    """
    Read in template specifications from a file. The file is assumed to be utf-8 encoded.

    :param initial_language: language id to assume for templates at the beginning of the text before a language
        has been specified
    :param filename: path to file
    :param return_what_types: if True, return a tuple of (templates, seen_what_types)
    :return: list of Template objects
    """
    with open(filename, "r", encoding="utf-8") as f:
        return read_templates(f.read(), initial_language=initial_language, return_what_types=return_what_types)


def read_templates(
    data: str, initial_language: Optional[str] = None, return_what_types: bool = False
) -> Tuple[Dict[str, List[Template]], Optional[List[str]]]:
    """
    Parse the template specifications in the given string.


    :param data: text
    :param initial_language: language id to assume for templates at the beginning of the text before a language
        has been specified
    :param return_what_types: if True, return a tuple of (templates, seen_what_types)
    :return: dict containing a list Template objects for each language
    """
    templates = {}
    seen_what_types = set()
    current_language = initial_language

    group_definitions = [line for line in data.splitlines() if line.startswith("$")]
    for line in group_definitions:
        group_name, _, rest = line[1:].partition(":")
        if group_name[0] != "{" or group_name[-1] != "}":
            raise TemplateReadingError(
                "invalid group name '{}' for use in template definitions\n"
                "Group names need to be within curly brackets".format(group_name)
            )
        rest = rest.strip()
        group_values = set([value.strip() for value in rest.split(",")])
        value_groups[group_name] = group_values

    # Remove all comment lines, beginning with a '#', and group definition lines, starting with a '$'
    lines = [line for line in data.splitlines() if not (line.startswith("#") or line.startswith("$"))]

    # Split on blank lines to separate the templates
    for line_group in blank_line_split(lines):
        # Parse each group of lines to get a load of template and add them to the dictionary
        # Update the default language to the last one used in the group
        new_templates, current_language, new_what_types = read_template_group(
            line_group, current_language=current_language
        )
        seen_what_types = seen_what_types.union(new_what_types)

        for lang, lang_templates in new_templates.items():
            templates.setdefault(lang, []).extend(lang_templates)

    if return_what_types:
        return templates, seen_what_types
    else:
        return templates, None


def read_template_group(
    template_spec: List[str], current_language: Optional[str] = None, warn_on_old_format: bool = True
):
    """
    Parse a template group: one block that shares fact constraints and may specify multiple templates
    (for different languages, or the same).

    :param template_spec: text of block, split into lines
    :param current_language: default language to start with
    :param warn_on_old_format: output warnings when the old template format is used. This is the default,
        since the old format is deprecated when using this function, but if you know you're reading an old
        file, you can suppress the warnings
    :return: dict of language -> template list, new default language after group
    """
    # Allow either a string (block) or a list of lines as input
    if isinstance(template_spec, str):
        template_spec = template_spec.splitlines()

    # For readability, lines may be spread over multiple lines of the file, indenting after the first
    # This applies to the template text and fact constraints
    lines = list(group_indented_lines(template_spec))

    # Allow changing the current language without any templates
    # This is mostly used to specify a monolingual set of templates, defining the language and letting it carry through
    lang_name, colon, rest = "".join(lines).strip().partition(":")
    if colon and len(rest) == 0:
        # Return no templates and update the current language
        return {}, lang_name

    # Detect whether this template is specified in the new or old format. Templates using the old format are
    # ignored.
    if not any(line.startswith(RULE_PREFIX) for line in lines):
        # If there are no fact constraint lines (now explicitly marked), assume this is the old format
        if warn_on_old_format:
            warnings.warn("no fact constraint lines found in template: assuming old format")
        return {}, current_language

    # Something has to be specified
    if len(lines) == 0:
        raise TemplateReadingError("empty template definition", raw_text="\n".join(template_spec))

    # Split up the lines into template lines (potentially with a language specifier, but not necessarily) and
    # constraint lines
    template_lines = [line for line in lines if not line.startswith(RULE_PREFIX)]
    # The rest of the lines each define a fact associated with the templates, along with constraints
    constraint_lines = [line[len(RULE_PREFIX) :].lstrip() for line in lines if line.startswith(RULE_PREFIX)]

    # FACT CONSTRAINTS
    # Read in the fact constraints first to get a list of rules that will be associated with the template
    rules = []  # type: List[List[Matcher]]
    seen_what_types = []
    for constraint_line in constraint_lines:
        # Every part of this line represents a constraint on the facts that may match
        matchers = []
        for lhs, op, value in parse_matcher_expr(constraint_line):
            if "value_type" in lhs.field_name:
                # Keep track of all what_types we've seen for reference
                # ToDo: What to do with the regexes?
                if type(value) is set:
                    seen_what_types.extend(value)
                else:
                    seen_what_types.append(value)

            matchers.append(Matcher(lhs, op, value))
        rules.append(matchers)

    # Every template is associated with at least one rule
    # If no constraints were given (very usual), create one rule with no constraints
    if len(rules) == 0:
        rules.append([])

    # TEMPLATES
    # Now we parse the template lines themselves
    templates = {}
    for template_line in template_lines:
        # Work out what language this template is for
        lang_id_match = lang_spec_re.match(template_line)
        if lang_id_match is None:
            # No language spec for this template: use the default language
            pass
        else:
            language, template_line = lang_id_match.groups()
            # Make language specifiers case insensitive
            language = language.lower()
            # If empty language spec, use default language (and strip away the colon prefix)
            if len(language) > 0:
                # Otherwise, switch the current language, so it gets used for this template and becomes the default
                current_language = language

        # Allow alternative versions of a template to be specified using the [] notation for optional parts
        for expanded_template_line in expand_alternatives(template_line):
            components = []  # type: List['TemplateComponent']

            # Generate list for mapping rules into template Slots
            rule_to_slot = []  # type: List[List[int]]
            for idx in range(len(rules)):
                rule_to_slot.append([])

            rest = expanded_template_line.strip()
            while len(rest.strip()):
                # Look for the next opening brace marking a substitution
                literal_part, __, rest = rest.partition("{")
                # Everything up to the brace is a literal
                if len(literal_part) > 0:
                    # To make life easier for the aggregator, literals are split on whitespace here
                    for literal in literal_part.split():
                        components.append(Literal(literal))
                # If no brace was found, we're done
                if len(rest) > 0:
                    # Look for the closing brace
                    subst, closer, rest = rest.partition("}")
                    if not closer:
                        raise TemplateReadingError("closing brace missing in {}".format(expanded_template_line))
                    # Split up the substitution spec on commas, to allow various attributes and filters to be included
                    subst_parts = [p.strip() for p in subst.split(",")]

                    # First check if the first part is actually a literal.
                    if subst_parts[0][0] in ['"', "'"]:
                        if subst_parts[0][-1] != subst_parts[0][0]:
                            raise TemplateReadingError("closing quote missing in {}".format(expanded_template_line))
                        field_name = subst_parts[0]
                        rule_ref = None
                    else:
                        # The first thing is the base value to substitute, which should be one of the fact fields
                        # or the new {time} slot, which refers to both when-fields
                        field_name = subst_parts[0]

                        # It may specify which of the facts it's referring to, though this is not required
                        # (default to first)
                        if "." in field_name:
                            rule_ref, __, field_name = field_name.partition(".")
                            # Use 1-indexed fact numbering in templates: makes more sense for anyone but
                            # computer scientists
                            rule_ref = int(rule_ref) - 1
                            if rule_ref < 0:
                                raise TemplateReadingError(
                                    "Rule references use 1-index numbering. Found reference to rule "
                                    "0: did you mean 1?"
                                )
                        else:
                            # Default to referring to the first rule, since there's usually only one
                            rule_ref = 0

                        # Map alternative field names to their canonical form used internally
                        try:
                            field_name = FACT_FIELD_MAP[field_name]
                        except KeyError:
                            raise TemplateReadingError(
                                "unknown fact field '{}' used in substitution ({})".format(field_name, subst)
                            )

                        # Only some of the field names are allowed to be used in templates
                        # TODO: Remove or reinstate with allowed things received as params from "somewhere"
                        if field_name not in FACT_FIELDS:
                            raise TemplateReadingError(
                                "invalid field name '{}' for use in a template: {}".format(
                                    field_name, expanded_template_line
                                )
                            )

                        if rule_ref >= len(rules):
                            raise TemplateReadingError(
                                "Substitution '{}' refers to rule {}, but template only has {} "
                                "rules".format(subst, rule_ref + 1, len(rules))
                            )

                    attributes = {}
                    # Read each of the attribute specifications
                    for subst_part in subst_parts[1:]:
                        if "=" in subst_part:
                            # Attributes specify things like case, to be used in realisation
                            att, __, val = subst_part.partition("=")
                            attributes[att.strip()] = val.strip()
                        else:
                            # Key-only attributes such as "abs" or "ord" are also possible
                            attributes[subst_part] = True
                            log.info(
                                "Found an attribute with no value specified. "
                                "Possibly a leftover old style filter? {}".format(subst_part)
                            )

                    if field_name[0] in ["'", '"']:
                        to_value = LiteralSource(field_name[1:-1])
                    elif field_name == "time":
                        to_value = TimeSource()
                    elif field_name == "unit":
                        to_value = UnitSource()
                    else:
                        to_value = FactFieldSource(field_name)

                    # Postprocess attributes
                    attributes = process_attributes(attributes)

                    # len(components) is the index for the next component to be added
                    if rule_ref is not None:
                        rule_to_slot[rule_ref].append(len(components))
                    new_slot = Slot(to_value, attributes=attributes)
                    components.append(new_slot)

            template = Template(components, list(zip(rules, rule_to_slot)))
            # Add this template to the list for the relevant language
            templates.setdefault(current_language, []).append(template)

    return templates, current_language, set(seen_what_types)


def parse_matcher_expr(constraint_line: str):
    rest = constraint_line
    while rest.strip():
        rest = rest.strip()
        # First part should be a LHS expr
        lhs, rest = parse_matcher_lhs(rest)
        # The next thing is the operator between the LHS and RHS
        try:
            op = next(opr for opr in Matcher.OPERATORS if rest.startswith(opr))
        except StopIteration:
            raise TemplateReadingError(
                "unrecognised operator at start of '{}'. Should be one of {}".format(rest, ", ".join(Matcher.OPERATORS))
            )
        rest = rest[len(op) :].strip()

        # The value is now everything up to the next , or the end
        value_match = rhs_value_re.match(rest)
        value, rest = rest[: value_match.end()], rest[value_match.end() + 1 :].strip()

        if len(value) == 0:
            raise TemplateReadingError("missing value part of constraint in: {}".format(constraint_line))

        # If the field name (name = value) isn't one we know, we assume that it's a shorthand for:
        #  what_type = name, what = value
        if lhs.field_name not in FACT_FIELD_MAP:
            # First yield the what_type=name constraint
            yield FactField("value_type"), "=", lhs.field_name
            # Continue with parsing the RHS as if we'd got a what specifier
            lhs = FactField("value")

        # For certain fields, we only allow string values and limit them to a given set
        # We also map them from a set of alternatives onto a canonical form
        if lhs.field_name == "location_type":
            try:
                value = LOCATION_TYPE_MAP[value]
            except KeyError:
                log.info(
                    "Unknown where_type '{}'. Expected one of: {}. It better be a valid regex!".format(
                        value, ", ".join("'{}'".format(v) for v in LOCATION_TYPE_MAP.keys())
                    )
                )
        elif lhs.field_name != "value_type":
            # Don't do RHS parsing for what_type
            # Special case: value references another fact???
            matches = referential_value_re.match(value)
            if matches:
                idx, field = matches.group(1), matches.group(2)
                # Translate from 1-based indexing to 0-based indexing
                idx = int(idx) - 1
                value = ReferentialExpr(idx, field)
            elif value in FACT_FIELD_MAP:
                value = FactField(value)
            else:
                # It's a normal value
                # Allow ints and floats to be written without any special typing: just detect them
                value = detect_types(value)
                # You don't need to put strings in quotes, but if someone wants to, let them do so
                if type(value) is str and (
                    (value[0] == "'" and value[-1] == "'") or (value[0] == '"' and value[-1] == '"')
                ):
                    value = value[1:-1]
        yield lhs, op, value_groups.get(value, value)


def parse_matcher_lhs(text: str):
    """
    Parse an expression on the LHS of a matcher. The provided text may be the whole matcher, or anything that
    starts with the LHS expression. The remainder of the text is returned.

    """
    # The first part of the text must specify a field of the fact, which may then be passed through filters
    field_match = field_name_re.match(text)
    if field_match is None:
        raise TemplateReadingError("matcher must begin with field name; could not parse: %s" % text)
    field_end = field_match.end()
    field_name, rest = text[:field_end], text[field_end + 1 :].strip()

    # Allow the alternative forms
    # If the field name is unknown, this will be assumed to be a shorthand for what_type=field_name, what=value
    field_name = FACT_FIELD_MAP.get(field_name, field_name)

    # Create the base LHS expression
    field_expr = FactField(field_name)

    if rest.startswith("|"):
        # There are filters applied to this value, but we've not implemented that yet
        # In the special case of what_type/what expansion above, the filters would be applied to the what expr
        raise NotImplementedError("not implemented filters yet")

    return field_expr, rest


# Defines alternative, equivalent names for cases, so we can be flexible with the templates
CASE_NAMES = {
    "nominative": ["nominatiivi", "nom"],
    "genitive": ["genitiivi", "gen"],
    "partitive": ["partitiivi", "par"],
    "accusative": ["akkusatiivi", "acc"],
    "inessive": ["inessiivi", "ine", "ssa"],
    "elative": ["elatiivi", "ela", "sta"],
    "illative": ["illatiivi", "ill"],
    "adessive": ["adessiivi", "ade", "lla"],
    "ablative": ["ablatiivi", "abl", "lta"],
    "allative": ["allatiivi", "all", "lle"],
    "essive": ["essiivi", "ess"],
    "translative": ["translatiivi", "tra"],
}


def process_attributes(attrs):
    """Post-processing of attribute dictionaries for slots"""
    proc_attrs = {}
    for attr, val in attrs.items():
        if attr == "case":
            # Look for the case in the dict of alternative names
            try:
                case_name = next(case for (case, alts) in CASE_NAMES.items() if case == val or val in alts)
            except StopIteration:
                log.info(
                    "unknown case name '{}', using the given form and hoping that Omorfi recognizes it".format(val)
                )
                case_name = val
            proc_attrs[attr] = case_name
        else:
            proc_attrs[attr] = val
    return proc_attrs


def detect_types(value):
    if value == "True":
        return True
    if value == "False":
        return False
    try:
        value = int(value)
    except ValueError:
        # Not an int, try float
        try:
            value = float(value)
        except ValueError:
            # Not a float either: just treat as a string
            pass
    return value


def blank_line_split(seq):
    """
    Group subseqences of the given string sequence, split by blank lines.
    """
    group = []
    for line in seq:
        if len(line) == 0:
            # Ignore consecutive blank lines (empty group)
            if len(group):
                yield group
                group = []
        else:
            group.append(line)
    # Yield the final group
    if len(group):
        yield group


def group_indented_lines(seq):
    group = [seq[0].strip()]
    for line in seq[1:]:
        if re.match(r"\s", line):
            # Indented line, group with the previous
            group.append(line.strip())
        else:
            # Yield the previous, now completed, group and start a new
            yield " ".join(group)
            group = [line.strip()]
    yield " ".join(group)


def expand_alternatives(line):
    """
    Expand out a template line containing optional parts delimited by []s into multiple template lines
    for the different versions.

    :param line: raw line
    :return: list of alternatives
    """
    alts = [""]

    def add_to_alts(old_alts, new_alts):
        return ["{}{}".format(old_alt, new_alt) for old_alt in old_alts for new_alt in new_alts]

    rest = line
    while len(rest):
        before_bracket, bracket, rest = rest.partition("[")
        # Add everything up to the next bracket to every existing alternative
        alts = add_to_alts(alts, [before_bracket])
        if bracket:
            # We found an opening bracket: look for the closing one
            in_bracket, closing_bracket, rest = rest.partition("]")
            if not closing_bracket:
                raise TemplateReadingError("unmatched square bracket in template line: {}".format(line))
            # Expand out all the alternatives we've already got to versions that add the contents of the brackets
            # and versions that don't
            alts = add_to_alts(alts, [in_bracket, ""])
    # Strip whitespace, so we don't have to worry about spaces before optional parts ending up at the end of templates
    alts = [x.strip() for x in alts]
    # Also replace any strings of multiple spaces with single spaces
    # This is because it's not intuitive to write "I [really ]want", but rather "I [really] want", even though the
    #  latter strictly speaking should have two consecutive spaces in the version without the optional text
    alts = [multi_space_re.sub(" ", alt) for alt in alts]
    return alts


class TemplateReadingError(Exception):
    def __init__(self, *args, **kwargs):
        self.raw_text = kwargs.pop("raw_text", None)
        super().__init__(*args, **kwargs)

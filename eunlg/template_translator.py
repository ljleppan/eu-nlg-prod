import functools
import logging
import re
from collections import Counter
from typing import List, Union, Dict, Optional

from nltk.tokenize import WordPunctTokenizer
from nltk.tokenize.treebank import TreebankWordDetokenizer
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils_base import PreTrainedTokenizerBase
from transformers import MarianTokenizer, MarianMTModel

import example_message_fetcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Token:
    def __init__(self, text: Optional[str] = None, is_placeholder: Optional[bool] = None):
        self._text: str = text
        self._is_placeholder: bool = is_placeholder

    def __str__(self):
        return "Token({}, {})".format(self._text, self._is_placeholder)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if type(other) == Token and str(other) == str(self):
            return True
        return False

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text: str):
        self._text = text

    @property
    def is_placeholder(self):
        return self._is_placeholder

    @is_placeholder.setter
    def is_placeholder(self, is_placeholder):
        self._is_placeholder = is_placeholder

    def lower(self):
        return Token(text=self._text.lower(), is_placeholder=self._is_placeholder)


class Replacement:
    def __init__(self, entity_name: Optional[str] = None, entity_value: Optional[str] = None):
        self._entity_name: str = entity_name
        self._entity_value: str = entity_value

    def __str__(self):
        return "Replacement({}, {})".format(self._entity_name, self._entity_value)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if type(other) == Replacement and str(other) == str(self):
            return True
        return False

    @property
    def entity_name(self):
        return self._entity_name

    @entity_name.setter
    def entity_name(self, entity_name: str):
        self._entity_name = entity_name

    @property
    def entity_value(self):
        return self._entity_value

    @entity_value.setter
    def entity_value(self, new_value):
        self._entity_value = new_value


class ReplacementSet:
    def __init__(self, replacements: Optional[Union[List[Replacement], Dict[str, str]]] = None):
        self._replacements: List[Replacement] = []
        if replacements:
            if type(replacements) == list:
                self._replacements = replacements
            elif type(replacements) == dict:
                self.parse_dict(replacements)

    def __str__(self):
        return "ReplacementSet({})".format(", ".join(str(replacement) for replacement in self._replacements))

    def __repr__(self):
        return str(self)

    def __len__(self):
        return len(self._replacements)

    def __eq__(self, other):
        if (
            type(other) == ReplacementSet
            and len(self) == len(other)
            and all(
                replacement_1 == replacement_2
                for (replacement_1, replacement_2) in zip(
                    sorted(self.replacements, key=lambda x: x.entity_name),
                    sorted(other.replacements, key=lambda x: x.entity_name),
                )
            )
        ):
            return True
        return False

    @property
    def replacements(self):
        return self._replacements

    @replacements.setter
    def replacements(self, replacements):
        self._replacements = replacements

    def parse_dict(self, replacement_dict: Dict[str, str]) -> None:
        self._replacements = []
        for k, v in replacement_dict.items():
            replacement = Replacement()
            replacement.entity_name, replacement.entity_value = k, v
            self._replacements.append(replacement)


class Tokenizer:
    def __init__(self):
        self._slot_delimiters = ("{", "}")
        self._regex_slot = re.compile(r"{}+\w+{}".format(*self._slot_delimiters))
        self._wp_tokenizer = WordPunctTokenizer()
        self._detokenizer = TreebankWordDetokenizer()
        self._slot_placeholder = "THISISASLOT_"

    def tokenize_sequence(self, string_sequence: str) -> List[Token]:
        def check_slots(text: str) -> bool:
            if self._regex_slot.search(text):
                return True
            return False

        string_tmpl_processed = string_sequence
        slot_counter = 0
        slot_placeholders = {}
        # find all slots and replace with placeholders
        while check_slots(string_tmpl_processed):
            placeholder = self._slot_placeholder + str(slot_counter)
            slot_key = self._regex_slot.findall(string_tmpl_processed)[0]
            string_tmpl_processed = self._regex_slot.sub(placeholder, string_tmpl_processed, 1)
            slot_placeholders[placeholder] = slot_key
            slot_counter += 1
        logger.debug("processed string: {}".format(string_tmpl_processed))
        logger.debug("slots found: {}".format(slot_placeholders))
        # tokenize the processed string
        string_tmpl_tokenized = self._wp_tokenizer.tokenize(string_tmpl_processed)
        logger.debug("tokenized sequence: {}".format(string_tmpl_tokenized))
        out = []
        for t in string_tmpl_tokenized:
            token_obj = Token()
            if t.startswith(self._slot_placeholder):
                logger.debug("slot token object {}".format(t))
                token_obj.text = slot_placeholders[t][1:-1]
                token_obj.is_placeholder = True
            else:
                logger.debug("text token object {}".format(t))
                token_obj.text = t
                token_obj.is_placeholder = False
            out.append(token_obj)

        return out

    def detokenize(self, source: List[Token]) -> str:
        text_tokens = [(("{" + token.text + "}") if token.is_placeholder else token.text) for token in source]
        return self._detokenizer.detokenize(text_tokens)


class TokenSequence:
    def __init__(self, tokens: Optional[List[Token]] = None):
        self._tokens: List[Token] = tokens if tokens else []

    def __len__(self):
        return len(self.tokens)

    def __eq__(self, other):
        if (
            type(other) == TokenSequence
            and len(self) == len(other)
            and all(token_1 == token_2 for (token_1, token_2) in zip(self.tokens, other._tokens))
        ):
            return True
        return False

    def __repr__(self):
        return "[" + ", ".join(str(token) for token in self.tokens) + "]"

    @property
    def tokens(self):
        return self._tokens

    @tokens.setter
    def tokens(self, tokens):
        self._tokens = tokens

    def from_string(self, sequence_string: str, tokenizer: Tokenizer) -> "TokenSequence":
        self._tokens = tokenizer.tokenize_sequence(sequence_string)
        return self

    def as_string(self, tokenizer: Tokenizer) -> str:
        return tokenizer.detokenize(self.tokens)

    def lower(self):
        return TokenSequence([token.lower() for token in self._tokens])

    def lexicalize(self, replacements: ReplacementSet) -> List[Token]:
        slot_entities = [t.text for t in self._tokens if t.is_placeholder]
        logger.debug("sequence has slots: {}".format(slot_entities))
        out = self._tokens.copy()
        for replacement in replacements.replacements:
            if replacement.entity_name in slot_entities:
                logger.debug("realizing slot {}".format(replacement))
                index_token_to_be_replaced = [t.text for t in out].index(replacement.entity_name)
                new_token = Token()
                new_token.text = replacement.entity_value
                new_token.is_placeholder = False
                out[index_token_to_be_replaced] = new_token
            else:
                logger.debug("replacement {} not found in sequence".format(replacement))
        return out

    def startswith(self, other) -> bool:
        return self.tokens[: len(other._tokens)] == other._tokens

    def match_subtokens(self, other, case_sensitive: Optional[bool] = True) -> bool:
        def _match_subtokens(sequence_1: TokenSequence, sequence_2: TokenSequence):
            if len(sequence_1.tokens) <= len(sequence_2.tokens):
                return sequence_1.tokens == sequence_2.tokens
            elif sequence_1.startswith(sequence_2):
                return True
            else:
                return _match_subtokens(TokenSequence(sequence_1.tokens[1:]), sequence_2)

        if not case_sensitive:
            return _match_subtokens(self.lower(), other.lower())
        else:
            return _match_subtokens(self, other)

    def match_subtokens_with_index(self, other, case_sensitive: Optional[bool] = True) -> int:
        def _match_subtokens_acc(sequence_1: TokenSequence, sequence_2: TokenSequence, accumulator: int) -> int:
            if len(sequence_1.tokens) <= len(sequence_2.tokens):
                return accumulator if sequence_1.tokens == sequence_2.tokens else -1
            elif sequence_1.startswith(sequence_2):
                return accumulator
            else:
                return _match_subtokens_acc(TokenSequence(sequence_1.tokens[1:]), sequence_2, accumulator + 1,)

        if not case_sensitive:
            return _match_subtokens_acc(self.lower(), other.lower(), 0)
        else:
            return _match_subtokens_acc(self, other, 0)


class Template:
    def __init__(
        self, tokens: Optional[TokenSequence] = None, replacement_sets: Optional[List[ReplacementSet]] = None,
    ):
        self._tokens: TokenSequence = tokens if tokens else TokenSequence()
        self._replacement_sets: List[ReplacementSet] = replacement_sets if replacement_sets else []

    @property
    def tokens(self):
        return self._tokens

    @tokens.setter
    def tokens(self, tokens: TokenSequence):
        self._tokens = tokens

    @property
    def replacement_sets(self):
        return self._replacement_sets

    @replacement_sets.setter
    def replacement_sets(self, replacement_sets: List[ReplacementSet]):
        self._replacement_sets = replacement_sets

    def parse_nlg_format(
        self, message: str, replacement_set: ReplacementSet, tokenizer: Tokenizer, case_sensitive: Optional[bool] = True
    ) -> bool:
        parsed_tokens = tokenizer.tokenize_sequence(message)
        self._replacement_sets = [replacement_set]
        # replace tokens with placeholder tokens by matching the values of the given replacement set
        for replacement in replacement_set.replacements:
            # TODO: the following code is a duplicate from Translator._translate_template, so it can be improved
            tokens_search = TokenSequence(tokenizer.tokenize_sequence(replacement.entity_value))
            matching_index = TokenSequence(parsed_tokens).match_subtokens_with_index(tokens_search, case_sensitive)
            if matching_index == -1:
                return False
            else:
                for i in range(matching_index, matching_index + len(tokens_search)):
                    parsed_tokens[i].text = replacement.entity_name
                    parsed_tokens[i].is_placeholder = True
                parsed_tokens = (
                    parsed_tokens[: matching_index + 1] + parsed_tokens[matching_index + len(tokens_search) :]
                )

        self._tokens = TokenSequence(parsed_tokens)
        return True

    def get_realizations(
        self, as_text: Optional[bool] = False, tokenizer: Optional[Tokenizer] = None
    ) -> Union[List[TokenSequence], List[str]]:
        realizations = [
            TokenSequence(self._tokens.lexicalize(replacements=replacement_set))
            for replacement_set in self._replacement_sets
        ]
        if as_text:
            if tokenizer:
                return [tokenizer.detokenize(realization.tokens) for realization in realizations]
            else:
                raise ValueError("tokenizer must be defined if as_text is True")
        else:
            return realizations


class Translator:

    _cache_size = 0
    # TODO: fix cache problem so that it can be safely reactivated and change cache size to >0!

    def __init__(
        self,
        tokenizer: Optional[PreTrainedTokenizerBase] = None,
        model: Optional[PreTrainedModel] = None,
        concat_placeholder: Optional[str] = ">>>CONCAT<<<",
    ):
        self._mt_tokenizer = tokenizer
        self._model = model
        self._concat_placeholder = concat_placeholder
        self._tokenizer = Tokenizer()

    def _concat_list(self, input_list: List[str]) -> str:
        return self._concat_placeholder.join(input_list)

    def _extract_list(self, input_concat: str) -> List[str]:
        return input_concat.split(self._concat_placeholder)

    def _translate_list_values(self, input_list: List[str]) -> List[str]:
        translated = self._model.generate(**self._mt_tokenizer(input_list, return_tensors="pt", padding=True))
        out_text = [self._mt_tokenizer.decode(t, skip_special_tokens=True) for t in translated]
        return out_text

    @functools.lru_cache(maxsize=_cache_size)
    def _translate_cached(self, input_sentences_concat: str) -> List[str]:
        sentences_list = self._extract_list(input_sentences_concat)
        return self._translate_list_values(sentences_list)

    def _translate_list_str(self, source: List[str]) -> List[str]:
        sentence_concat = self._concat_list(source)
        return self._translate_cached(sentence_concat)

    def _translate_token_seq(self, source: TokenSequence) -> TokenSequence:
        placeholder_tokens = []
        actual_tokens = []
        logger.debug("separating placeholders from actual _tokens")
        for token in source.tokens:
            if token.is_placeholder:
                placeholder_tokens.append(token)
            else:
                actual_tokens.append(token)
        logger.debug("placeholder Tokens: {}".format(placeholder_tokens))
        logger.debug("actual Tokens: {}".format(actual_tokens))
        # translated only the actual _tokens - placeholders are not translated
        source_text = [token.text for token in actual_tokens]
        logger.debug("translating text of actual Tokens: {}".format(source_text))
        translated_tokens = self.translate(source_text)
        logger.debug("translated text _tokens {}".format(translated_tokens))
        assert len(source_text) == len(
            translated_tokens
        ), "something went wrong in the translation (cache problem? try to set _cache_size to 0)"
        translation = []
        for i, token in enumerate(source.tokens):
            logger.debug("appending translation of source token {}".format(token))
            if token.is_placeholder:
                translation.append(placeholder_tokens.pop(0))
            else:
                translated_token = translated_tokens.pop(0)
                translation.append(Token(text=translated_token, is_placeholder=False))
        logger.debug("leftover _tokens {}, {}".format(placeholder_tokens, translated_tokens))
        assert len(placeholder_tokens) == 0, "some placeholder _tokens where not appended to the final output"
        assert len(translated_tokens) == 0, "some _tokens where translated and not appended to the final output"
        return TokenSequence(translation)

    def _translate_replacement(self, source: Replacement) -> Replacement:
        translation = Replacement(
            entity_name=source.entity_name, entity_value=self.translate([source.entity_value])[0],
        )
        return translation

    def _translate_replacementset(self, source: ReplacementSet) -> ReplacementSet:
        translated_values = self.translate([replacement.entity_value for replacement in source.replacements])
        translation = ReplacementSet()
        translation.replacements = [
            Replacement(entity_name=replacement.entity_name, entity_value=translated_entity_value,)
            for replacement, translated_entity_value in zip(source.replacements, translated_values)
        ]
        return translation

    def _translate_template(self, source: Template, case_sensitive: Optional[bool] = True) -> List[Template]:
        lexicalizations = source.get_realizations(as_text=True, tokenizer=self._tokenizer)
        # TODO: optimize translation so that it is done by a single call to translator
        translated_lexicalizations = self._translate_list_str(lexicalizations)
        translated_replacements = [
            self._translate_replacementset(replacement_set) for replacement_set in source._replacement_sets
        ]
        tokenized_trans_lexicalizations = [
            self._tokenizer.tokenize_sequence(translated_lex) for translated_lex in translated_lexicalizations
        ]
        out = []  # will contain all the lexicalization for which it is possible to extract a translated template
        for tokenized_trans_lex, trans_rep_set in zip(tokenized_trans_lexicalizations, translated_replacements):
            logger.debug("looking for translated values in the translated lex {}".format(tokenized_trans_lex))
            translation_success = True  # bookkeeping to add only successfully translated lexicalization to the final
            # output
            for trans_rep in trans_rep_set.replacements:
                # look for the token with the text matching with the value of the replacement
                tokens_search = TokenSequence(self._tokenizer.tokenize_sequence(trans_rep.entity_value))
                matching_index = TokenSequence(tokenized_trans_lex).match_subtokens_with_index(
                    tokens_search, case_sensitive
                )
                if matching_index == -1:
                    logger.debug("not able to find the translated values {}".format(tokens_search))
                    translation_success = False
                    break
                else:
                    logger.debug(
                        "found translated value {} at index {}. updating tokenized translation".format(
                            tokens_search, matching_index
                        )
                    )
                    for i in range(matching_index, matching_index + len(tokens_search)):
                        tokenized_trans_lex[i].text = trans_rep.entity_name
                        tokenized_trans_lex[i].is_placeholder = True
                    tokenized_trans_lex = (
                        tokenized_trans_lex[: matching_index + 1]
                        + tokenized_trans_lex[matching_index + len(tokens_search) :]
                    )
            if translation_success:
                translated_template = Template(TokenSequence(tokenized_trans_lex), [trans_rep_set])
                out.append(translated_template)

        return out

    def translate(
        self,
        source: Union[List[str], Replacement, ReplacementSet, TokenSequence, Template],
        case_sensitive: Optional[bool] = True,
    ) -> Union[List[str], Replacement, ReplacementSet, TokenSequence, List[Template]]:
        """
        Translate the input object. When translating a Replacement object, only the entity_value get translated (the
        entity name is not translated).
        :param source: Object to be translated :return: New object, with translated values
        """
        if type(source) == list:
            return self._translate_list_str(source)
        elif type(source) == Replacement:
            return self._translate_replacement(source)
        elif type(source) == ReplacementSet:
            return self._translate_replacementset(source)
        elif type(source) == TokenSequence:
            return self._translate_token_seq(source)
        elif type(source) == Template:
            return self._translate_template(source, case_sensitive)
        else:
            raise TypeError("Unsupported source type {}".format(type(source)))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Obtain machine-translated templates for a new language")
    parser.add_argument("--dataset", type=str, required=True, help="Dataset to translate the templates of")
    parser.add_argument("--source_language", type=str, required=True, help="Language code of source language")
    parser.add_argument("--target_language", type=str, required=True, help="Language code of target language")
    parser.add_argument("--model", type=str, required=True, help="MarianMT model to use, defines output language")
    args = parser.parse_args()

    logger.info(
        f"Translating dataset {args.dataset} from '{args.source_language}' to "
        f"'{args.target_language}' using the MarianMT model {args.model}"
    )
    mt_tokenizer = MarianTokenizer.from_pretrained(args.model)
    mt_model = MarianMTModel.from_pretrained(args.model)
    translator = Translator(tokenizer=mt_tokenizer, model=mt_model)
    tokenizer = Tokenizer()

    print("Fetching messages...")
    templates_and_messages = example_message_fetcher.obtain_example_messages_for_all_templates(
        args.dataset, args.source_language
    )
    print(f"Obtained {len(templates_and_messages)} templates")

    print("Transforming to token sequences and replacement sets...")
    token_seqs_and_replacement_sets = [
        (
            TokenSequence().from_string(example_message_fetcher.template_as_string_approximation(template), tokenizer),
            [
                ReplacementSet(example_message_fetcher.msg_as_realized_dict(msg, template, args.source_language))
                for msg in messages
            ],
        )
        for (template, messages) in templates_and_messages
    ]
    print("Translating token sequences...")
    all_results = []
    for idx in range(len(templates_and_messages)):
        print(f"\t{idx+1}/{len(templates_and_messages)}")
        token_seq, replacement_sets = token_seqs_and_replacement_sets[idx]

        tmpl = Template(tokens=token_seq, replacement_sets=replacement_sets)
        all_results.append(translator.translate(tmpl, case_sensitive=False))

    rules_to_templates = {}

    for idx in range(len(templates_and_messages)):
        template, messages = templates_and_messages[idx]
        results = all_results[idx]

        if results:
            try:
                most_common = Counter(result.tokens.as_string(tokenizer) for result in results).most_common(1)[0][0]

                if template.rules_str not in rules_to_templates:
                    rules_to_templates[template.rules_str] = []
                rules_to_templates[template.rules_str].append(most_common)
            except Exception as ex:
                print(f"ERROR, skipping: {ex}")

    print("TRANSLATED TEMPLATES:")
    print("-" * 15)
    for rule, templates in rules_to_templates.items():
        for template in templates:
            print(f"{args.target_language}: {template}")
        print("| " + rule.replace("\n", "\n| "))
        print()
    print("-" * 15)


if __name__ == "__main__":
    main()

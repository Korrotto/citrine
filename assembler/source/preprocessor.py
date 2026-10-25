from ..common.models import TranslationSpec
from ..common.translationparser import InvalidTranslationError, TranslationParser
from ..common.utils import convert_to_integer, is_integer_literal, is_valid_instruction
from .constants import (
    AS_KEYWORD,
    DEFINE_DIRECTIVE,
    DEFINE_LENGTH,
    KIND_ALIAS,
    KIND_INSTRUCTION,
    KIND_LABEL,
    KIND_PSEUDO,
    LABEL,
    PSEUDO_DIRECTIVE,
    PSEUDO_LENGTH,
    TO_KEYWORD,
    USED_DIRECTIVE,
    USED_LENGTH,
)
from .models import AssemblerContext, TokenizedLine
from .utils import is_valid_alias, is_valid_label, name_kind


class Preprocessor:
    def __init__(self, context: AssemblerContext) -> None:
        self.context: AssemblerContext = context

    def process_lines(self, lines: list[TokenizedLine]) -> list[TokenizedLine]:
        context: AssemblerContext = self.context
        instruction_lines: list[TokenizedLine] = self.dispatch_lines(lines)

        for alias in context.get_undefined_aliases():
            context.log_error("SRC-001", name_kind(alias), alias)

        for used_alias in context.get_used_aliases():
            if used_alias not in context.aliases:
                context.log_error("SRC-001", name_kind(used_alias), used_alias)

        return instruction_lines

    def dispatch_lines(self, lines: list[TokenizedLine]) -> list[TokenizedLine]:
        current_address: int = 0
        instruction_lines: list[TokenizedLine] = []

        for line in lines:
            if line.line_type == DEFINE_DIRECTIVE:
                self.process_define_directive(line)
            elif line.line_type == USED_DIRECTIVE:
                self.process_used_directive(line)
            elif line.line_type == PSEUDO_DIRECTIVE:
                self.process_pseudo_directive(line)
            elif line.line_type == LABEL:
                self.process_label(line, current_address)
            else:
                instruction_lines.append(line)
                current_address += 1
        return instruction_lines

    def process_define_directive(self, line: TokenizedLine) -> None:
        context: AssemblerContext = self.context
        tokens: tuple[str, ...] = line.tokens

        if len(tokens) != DEFINE_LENGTH or tokens[2] != AS_KEYWORD:
            return context.log_error("SRC-002", "DEFINE", line=line)

        alias_name: str = tokens[1]
        alias_value: str = tokens[3]

        if not is_valid_alias(alias_name):
            return context.log_error("SRC-003", KIND_ALIAS, alias_name, line=line)

        if alias_name in context.aliases:
            return context.log_error("SRC-004", KIND_ALIAS.capitalize(), alias_name, line=line)

        if is_integer_literal(alias_value):
            context.aliases[alias_name] = convert_to_integer(alias_value)
            return None

        if not (
            alias_value in context.aliases
            or is_valid_alias(alias_value)
            or is_valid_label(alias_value)
        ):
            return context.log_error("SRC-005", alias_value, line=line)

        context.aliases[alias_name] = alias_value

    def process_used_directive(self, line: TokenizedLine) -> None:
        context: AssemblerContext = self.context
        tokens: tuple[str, ...] = line.tokens

        if len(tokens) != USED_LENGTH:
            return context.log_error("SRC-002", "USED", line=line)

        label: str = tokens[1]

        if not is_valid_label(label):
            return context.log_error("SRC-003", KIND_LABEL, label, line=line)

        context.used_aliases.add(label)

    def process_pseudo_directive(self, line: TokenizedLine) -> None:
        context: AssemblerContext = self.context
        tokens: tuple[str, ...] = line.tokens

        if len(tokens) < PSEUDO_LENGTH or tokens[2] != TO_KEYWORD:
            return context.log_error("SRC-002", "PSEUDO", line=line)

        names = self.validate_pseudo_target(line)
        if names is None:
            return None
        pseudo_name, base_name = names
        widths: tuple[int, ...] = context.instruction_variable_widths[base_name]

        try:
            spec: TranslationSpec = TranslationSpec(tokens[4:], widths, pseudo_name)
            slots, warnings = TranslationParser.parse(spec)
        except InvalidTranslationError as error:
            return context.log_error(error.code, *error.params, line=line)

        for warning_code, warning_params in warnings:
            context.log_warning(warning_code, *warning_params, line=line)

        context.pseudo_set[pseudo_name] = (base_name, slots)

    def validate_pseudo_target(self, line: TokenizedLine) -> tuple[str, str] | None:
        context: AssemblerContext = self.context
        pseudo_name, base_name = line.tokens[1], line.tokens[3]

        if not is_valid_instruction(pseudo_name):
            context.log_error("SRC-003", KIND_PSEUDO, pseudo_name, line=line)
        elif pseudo_name in context.instruction_set:
            context.log_error("SRC-004", KIND_INSTRUCTION.capitalize(), pseudo_name, line=line)
        elif pseudo_name in context.pseudo_set:
            context.log_error("SRC-004", KIND_PSEUDO.capitalize(), pseudo_name, line=line)
        elif base_name not in context.instruction_set:
            context.log_error("SRC-006", base_name, line=line)
        else:
            return (pseudo_name, base_name)
        return None

    def process_label(self, line: TokenizedLine, current_address: int) -> None:
        context: AssemblerContext = self.context
        tokens: tuple[str, ...] = line.tokens
        label_name: str = tokens[0]

        if len(tokens) != 1:
            return context.log_error("SRC-007", line=line)

        if not is_valid_label(label_name):
            return context.log_error("SRC-003", KIND_LABEL, label_name, line=line)

        if label_name in context.aliases:
            return context.log_error("SRC-004", KIND_LABEL.capitalize(), label_name, line=line)

        context.aliases[label_name] = current_address

    def mark_used_aliases(self, instruction_lines: list[TokenizedLine]) -> None:
        for instruction_line in instruction_lines:
            for token in instruction_line.tokens[1:]:
                self.mark_used_alias_chain(token)

        for name in self.context.get_unused_aliases():
            self.context.log_warning("SRC-010", name_kind(name).capitalize(), name)

    def mark_used_alias_chain(self, name: str) -> None:
        context: AssemblerContext = self.context

        while name in context.aliases and name not in context.used_aliases:
            context.used_aliases.add(name)

            alias_value: int | str | None = context.aliases.get(name)
            if not isinstance(alias_value, str):
                return

            name = alias_value

    def mark_used_pseudo_instructions(self, lines: list[TokenizedLine]) -> None:
        context: AssemblerContext = self.context

        for line in lines:
            head: str = line.tokens[0]
            if head in context.pseudo_set:
                context.used_pseudo_instructions.add(head)

        for name in context.get_unused_pseudo_instructions():
            context.log_warning("SRC-010", KIND_PSEUDO.capitalize(), name)

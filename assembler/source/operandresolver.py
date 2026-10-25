from collections.abc import Iterable, Iterator
from typing import cast

from ..common.utils import convert_to_integer, is_integer_literal
from .constants import KIND_ALIAS, KIND_LABEL
from .models import AssemblerContext, ResolvedLine, TokenizedLine
from .utils import is_label_name


class OperandResolver:
    def __init__(self, context: AssemblerContext) -> None:
        self.context = context
        self.resolved_values: dict[str, int] = {}

    def resolve_operands(self, lines: Iterable[TokenizedLine]) -> Iterator[ResolvedLine]:
        for line in lines:
            opcode, *operand_tokens = line.tokens
            operands = tuple(self.resolve_single_operand(token, line) for token in operand_tokens)
            yield ResolvedLine(line, opcode, operands)

    def resolve_single_operand(self, token: str, line: TokenizedLine) -> int | None:
        if token in self.resolved_values:
            return self.resolved_values[token]

        if token in self.context.aliases:
            return self.resolve_alias(token, line)
        return self.resolve_literal(token, line)

    def resolve_literal(self, token: str, line: TokenizedLine) -> int | None:
        if not is_integer_literal(token):
            kind = KIND_LABEL if is_label_name(token) else KIND_ALIAS
            self.context.log_error("SRC-001", kind, token, line=line)
            return None

        value = self.resolved_values[token] = convert_to_integer(token)
        return value

    def resolve_alias(self, token: str, line: TokenizedLine) -> int | None:
        chain: list[str] = [token]
        value = self.lookup(token)

        while isinstance(value, str):
            if value in chain:
                self.context.log_error("SRC-009", token, line=line)
                return None

            chain.append(value)
            next_value = self.lookup(value)

            if next_value is None:
                self.context.log_error("SRC-001", KIND_ALIAS, value, line=line)
                return None

            value = next_value

        self.resolved_values.update(dict.fromkeys(chain, cast(int, value)))
        return value

    def lookup(self, name: str) -> int | str | None:
        if name in self.resolved_values:
            return self.resolved_values[name]
        return self.context.aliases.get(name)

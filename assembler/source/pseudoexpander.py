from collections.abc import Iterable, Iterator
from typing import cast

from ..common.models import LiteralSlot, PseudoSlot
from .models import AssemblerContext, ExpandedLine, ResolvedLine
from .utils import apply_operation


class PseudoExpander:
    def __init__(self, context: AssemblerContext) -> None:
        self.context = context

    def expand_pseudo_instructions(self, lines: Iterable[ResolvedLine]) -> Iterator[ExpandedLine]:
        for line in lines:
            if line.instruction_name in self.context.instruction_set:
                operand_values = cast(tuple[int, ...], line.operand_values)
                yield ExpandedLine(line.instruction_name, operand_values)
            else:
                yield self.expand_pseudo(line)

    def expand_pseudo(self, line: ResolvedLine) -> ExpandedLine:
        base_name, translation = self.context.pseudo_set[line.instruction_name]
        widths = self.context.instruction_variable_widths[base_name]
        operands = tuple(
            self.transform_slot(slot, width, line.operand_values)
            for slot, width in zip(translation, widths, strict=True)
        )
        return ExpandedLine(base_name, operands)

    def transform_slot(
        self, slot: PseudoSlot, width: int, operand_values: tuple[int | None, ...]
    ) -> int:
        if isinstance(slot, LiteralSlot):
            return slot.value

        operand_value: int = cast(int, operand_values[slot.index])
        return apply_operation(slot.operation, operand_value, width)

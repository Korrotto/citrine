from collections import defaultdict
from collections.abc import Iterable

from ..common.models import PlaceholderSlot, PseudoTranslation
from ..common.utils import fits_in_width, mask_to_width
from .models import AssemblerContext, OperandWidths, ResolvedLine
from .utils import is_label_line


class InstructionValidator:
    def __init__(self, context: AssemblerContext) -> None:
        self.context = context

    def validate_instructions(self, resolved_lines: Iterable[ResolvedLine]) -> None:
        widths_by_instruction = self.get_instruction_operand_widths()
        for resolved_line in resolved_lines:
            self.validate_line(
                resolved_line,
                widths_by_instruction.get(resolved_line.instruction_name),
            )

    def get_instruction_operand_widths(self) -> dict[str, OperandWidths]:
        context = self.context
        real_instructions = {
            name: [frozenset((width,)) for width in context.instruction_variable_widths[name]]
            for name in context.instruction_set
        }
        pseudo_instructions = {
            name: self.extract_pseudo_operand_widths(translation)
            for name, translation in context.pseudo_set.items()
        }
        return real_instructions | pseudo_instructions

    def validate_line(self, line: ResolvedLine, expected_widths: OperandWidths | None) -> None:
        name = line.instruction_name
        tokenized_line = line.tokenized_line

        if expected_widths is None:
            if is_label_line(name):
                self.context.log_error("SRC-007", line=tokenized_line)
            else:
                self.context.log_error("SRC-006", name, line=tokenized_line)
        elif len(line.operand_values) != len(expected_widths):
            self.context.log_error("SRC-008", name, line=tokenized_line)
        else:
            self.warn_on_truncation(line, expected_widths)

    def extract_pseudo_operand_widths(self, translation: PseudoTranslation) -> OperandWidths:
        base_name, operand_slots = translation
        base_widths = self.context.instruction_variable_widths[base_name]

        widths_by_operand: defaultdict[int, set[int]] = defaultdict(set)
        for base_width, slot in zip(base_widths, operand_slots, strict=True):
            if isinstance(slot, PlaceholderSlot):
                widths_by_operand[slot.index].add(base_width)

        return [frozenset(widths) for _, widths in sorted(widths_by_operand.items())]

    def warn_on_truncation(self, line: ResolvedLine, operand_widths: OperandWidths) -> None:
        truncated_pairs: tuple[tuple[int, int], ...] = tuple(
            (value, width)
            for value, widths in zip(line.operand_values, operand_widths, strict=True)
            if value is not None
            for width in sorted(widths)
            if not fits_in_width(value, width)
        )

        for value, width in truncated_pairs:
            self.context.log_warning(
                "SRC-011",
                value,
                width,
                mask_to_width(value, width),
                line=line.tokenized_line,
            )

from collections.abc import Iterable

from ..architecture.models import BitField, InstructionSet, VariableBits
from ..common.utils import mask_to_width
from .models import AssemblerContext, ExpandedLine


class CodeGenerator:
    def __init__(self, context: AssemblerContext) -> None:
        self.context: AssemblerContext = context

    def generate_machine_code(self, expanded_lines: Iterable[ExpandedLine]) -> list[int]:
        instruction_set: InstructionSet = self.context.instruction_set
        return [
            self.generate_instruction(
                instruction_set[expanded_line.instruction_name],
                expanded_line.operand_values,
            )
            for expanded_line in expanded_lines
        ]

    def generate_instruction(
        self, instruction_format: tuple[BitField, ...], values: tuple[int, ...]
    ) -> int:
        code: int = 0
        operand_index: int = 0

        for field in instruction_format:
            if isinstance(field, VariableBits):
                value: int = mask_to_width(values[operand_index], field.width)
                operand_index += 1
            else:
                value = field.value

            code = (code << field.width) | value

        return code

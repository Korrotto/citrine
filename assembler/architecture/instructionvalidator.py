from typing import cast

from ..common.constants import MAX_INSTRUCTION_LENGTH
from ..common.utils import is_valid_instruction, is_variable_field, normalize, parse_decimal
from .constants import INSTRUCTION_FORMAT_LENGTH, INSTRUCTION_LENGTH, INSTRUCTION_SET
from .utils import is_binary_string
from .validationcontext import ValidationContext


class InstructionSetValidator:
    def __init__(self, context: ValidationContext) -> None:
        self.context = context

    def validate(self, seen_names: set[str]) -> None:
        instructions = self.require_instruction_dict()
        if instructions is None:
            return
        used_opcodes = self.validate_all_instructions(instructions, seen_names)
        self.check_opcode_width_consistency(used_opcodes)

    def require_instruction_dict(self) -> dict[object, object] | None:
        if not self.context.require(INSTRUCTION_SET, "ARCH-002"):
            return None
        instructions = self.context.raw_data[INSTRUCTION_SET]
        if not isinstance(instructions, dict):
            self.context.log_error("ARCH-003", INSTRUCTION_SET)
            return None
        if not instructions:
            self.context.log_error("ARCH-005", INSTRUCTION_SET, "instruction")
            return None
        return instructions

    def validate_all_instructions(
        self, instructions: dict[object, object], seen_names: set[str]
    ) -> set[str]:
        used_opcodes: set[str] = set()
        for name, instruction_format in instructions.items():
            if not self.claim_instruction_name(name, seen_names):
                continue
            instruction_name = cast(str, name)
            if not self.validate_instruction_format(instruction_name, instruction_format):
                continue
            format_fields = cast(list[object], instruction_format)
            opcode = format_fields[0]
            if self.claim_instruction_opcode(instruction_name, opcode, used_opcodes):
                self.validate_instruction_body(instruction_name, format_fields)
        return used_opcodes

    def claim_instruction_name(self, name: object, seen_names: set[str]) -> bool:
        if not isinstance(name, str) or not is_valid_instruction(name):
            self.context.log_error("ARCH-006", INSTRUCTION_SET, name)
            return False
        if normalize(name) in seen_names:
            self.context.log_error("ARCH-007", INSTRUCTION_SET, name)
            return False
        seen_names.add(normalize(name))
        return True

    def claim_instruction_opcode(self, name: str, opcode: object, used_opcodes: set[str]) -> bool:
        if not isinstance(opcode, str) or not is_binary_string(opcode):
            self.context.log_error("ARCH-010", name)
            return False
        if opcode in used_opcodes:
            self.context.log_error("ARCH-011", name, opcode)
        used_opcodes.add(opcode)
        return True

    def check_opcode_width_consistency(self, used_opcodes: set[str]) -> None:
        if len({len(opcode) for opcode in used_opcodes}) > 1:
            self.context.log_error("ARCH-012")

    def validate_instruction_format(self, name: str, instruction_format: object) -> bool:
        if (
            not isinstance(instruction_format, list)
            or len(instruction_format) != INSTRUCTION_FORMAT_LENGTH
        ):
            self.context.log_error("ARCH-009", name)
        elif not isinstance(instruction_format[0], str):
            self.context.log_error("ARCH-010", name)
        else:
            return True
        return False

    def validate_instruction_body(self, name: str, instruction_format: list[object]) -> None:
        body = instruction_format[1]
        if not isinstance(body, str) or not body.strip():
            return self.context.log_error("ARCH-013", name)

        opcode = cast(str, instruction_format[0])
        measured = self.measure_body_width(name, body, len(opcode))
        self.check_body_width(name, *measured)

    def measure_body_width(self, name: str, body: str, base_width: int) -> tuple[int, bool]:
        total_width = base_width
        is_valid = True
        for token in body.split():
            width = self.token_width(name, token)
            if width is None:
                is_valid = False
            else:
                total_width += width
        return total_width, is_valid

    def token_width(self, name: str, token: str) -> int | None:
        if is_variable_field(token):
            return self.variable_token_width(name, token)
        if is_binary_string(token):
            return len(token)
        self.context.log_error("ARCH-014", name)
        return None

    def variable_token_width(self, name: str, token: str) -> int | None:
        width = parse_decimal(token[1:])
        if width is not None and 0 < width <= MAX_INSTRUCTION_LENGTH:
            return width
        self.context.log_error("ARCH-014", name)
        return None

    def check_body_width(self, name: str, total_width: int, is_valid: bool) -> None:
        if not is_valid:
            return
        expected = self.context.raw_data.get(INSTRUCTION_LENGTH)
        if type(expected) is int and total_width != expected:
            self.context.log_error("ARCH-015", name)

from ..common.constants import MAX_INSTRUCTION_LENGTH
from ..common.utils import is_integer_literal, is_not_reserved, is_variable_field, parse_decimal
from .constants import (
    BINARY_STRING_PATTERN,
    DEFAULT_ALIAS_NAME_PATTERN,
    FILE_EXTENSION_PATTERN,
    PSEUDO_FORMAT_LENGTH,
)
from .models import BitField, VariableBits


def is_binary_string(string: str) -> bool:
    return bool(BINARY_STRING_PATTERN.fullmatch(string))


def is_valid_default_alias(name: str) -> bool:
    return (
        bool(DEFAULT_ALIAS_NAME_PATTERN.fullmatch(name))
        and not is_integer_literal(name)
        and is_not_reserved(name)
    )


def is_valid_file_extension(name: str) -> bool:
    return bool(FILE_EXTENSION_PATTERN.fullmatch(name))


def is_valid_target_format(target_format: object) -> bool:
    return (
        isinstance(target_format, list)
        and len(target_format) == PSEUDO_FORMAT_LENGTH
        and isinstance(target_format[1], str)
    )


def parse_operand_widths(format_string: str) -> list[int]:
    widths: list[int] = []
    for slot in format_string.split():
        if not is_variable_field(slot):
            continue
        width = parse_decimal(slot[1:])
        if width is not None and width <= MAX_INSTRUCTION_LENGTH:
            widths.append(width)
    return widths


def variable_widths(instruction_fields: tuple[BitField, ...]) -> tuple[int, ...]:
    return tuple(field.width for field in instruction_fields if isinstance(field, VariableBits))

from ..common.constants import OPERAND_OPERATIONS
from ..common.utils import is_not_reserved, mask_to_width
from .constants import (
    ALIAS_NAME_PATTERN,
    DIRECTIVES,
    INSTRUCTION,
    KIND_ALIAS,
    KIND_LABEL,
    LABEL,
    LABEL_NAME_PATTERN,
)


def is_label_line(line: str) -> bool:
    return line.endswith(":") and line.startswith(".")


def is_valid_alias(name: str) -> bool:
    return bool(ALIAS_NAME_PATTERN.fullmatch(name)) and is_not_reserved(name)


def is_valid_label(name: str) -> bool:
    return bool(LABEL_NAME_PATTERN.fullmatch(name)) and is_not_reserved(name)


def is_label_name(name: str) -> bool:
    return name.startswith(".")


def name_kind(name: str) -> str:
    return KIND_LABEL if is_label_name(name) else KIND_ALIAS


def line_type(head: str, is_label: bool) -> str:
    if head in DIRECTIVES:
        return head
    elif is_label:
        return LABEL
    else:
        return INSTRUCTION


def apply_operation(operation: str, operand: int, width: int) -> int:
    value = mask_to_width(operand, width)
    if not operation:
        return value
    return mask_to_width(OPERAND_OPERATIONS[operation](value, width), width)

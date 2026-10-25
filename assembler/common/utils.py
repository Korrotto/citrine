from .constants import (
    BIT_MASKS,
    ERROR,
    INSTRUCTION_NAME_PATTERN,
    INTEGER_LITERAL_PATTERN,
    RESERVED_NAMES,
    WARNING,
    WIDTH_BOUNDS,
)
from .message import make_message


def normalize(text: str) -> str:
    return text.lower()


def log(severity: str, message: str, position: tuple[int | None, str | None] = (None, None)) -> str:
    line, text = position
    parts: list[str] = [severity]
    if line is not None:
        parts.append(f"| line {line}")
    parts.append(f"| {message}")
    if text:
        parts.append(f"| {text}")
    return " ".join(parts)


def log_error(
    code: str, *args: object, position: tuple[int | None, str | None] = (None, None)
) -> str:
    return log(ERROR, make_message(code, *args), position)


def log_warning(
    code: str, *args: object, position: tuple[int | None, str | None] = (None, None)
) -> str:
    return log(WARNING, make_message(code, *args), position)


def is_integer_literal(literal: str) -> bool:
    return bool(INTEGER_LITERAL_PATTERN.fullmatch(literal))


def parse_decimal(digits: str) -> int | None:
    if not digits.isdecimal():
        return None
    return int(digits.lstrip("0") or "0")


def convert_to_integer(literal: str) -> int:
    if literal.startswith("-"):
        return -parse_numeric_literal(literal[1:])
    if literal.startswith("+"):
        return parse_numeric_literal(literal[1:])
    return parse_numeric_literal(literal)


def parse_numeric_literal(literal: str) -> int:
    match normalize(literal[:2]):
        case "0b":
            return int(literal[2:], 2)
        case "0o":
            return int(literal[2:], 8)
        case "0d":
            return int(literal[2:])
        case "0x":
            return int(literal[2:], 16)
        case _:
            return int(literal)


def is_variable_field(field: str) -> bool:
    return normalize(field[:1]) == "x" and field[1:].isdecimal() and field[1:].isascii()


def is_not_reserved(name: str) -> bool:
    return normalize(name) not in RESERVED_NAMES


def is_valid_instruction(name: str) -> bool:
    return bool(INSTRUCTION_NAME_PATTERN.fullmatch(name)) and is_not_reserved(name)


def mask_to_width(value: int, width: int) -> int:
    if width <= 0:
        raise ValueError(f"Invalid bit width: {width}")
    return value & BIT_MASKS[width - 1]


def fits_in_width(value: int, width: int) -> bool:  # [signed_min, unsigned_max[
    if width <= 0:
        raise ValueError(f"Invalid bit width: {width}")
    lower_bound, upper_bound = WIDTH_BOUNDS[width - 1]
    return lower_bound <= value < upper_bound


def check_input_types(source_code: str, architecture_data: dict[str, object]) -> None:
    if not isinstance(architecture_data, dict):
        type_name = type(architecture_data).__name__
        raise TypeError(make_message("API-001", "architecture_data", "dict", type_name))
    if not isinstance(source_code, str):
        type_name = type(source_code).__name__
        raise TypeError(make_message("API-001", "source_code", "str", type_name))

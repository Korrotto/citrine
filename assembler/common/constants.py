from collections.abc import Callable
from re import IGNORECASE, Pattern, escape
from re import compile as re_compile

# Severity type
ERROR: str = "ERROR"
WARNING: str = "WARNING"

# Reserved names
RESERVED_NAMES: frozenset[str] = frozenset({"define", "used", "pseudo", "as", "to"})

# Operand Operation
OPERAND_OPERATIONS: dict[str, Callable[[int, int], int]] = {
    "-": lambda value, width: -value,  # Arithmetic Negation
    "~": lambda value, width: ~value,  # Bitwise NOT
    "<": lambda value, width: (value << 1) | (value >> (width - 1)),  # Rotate Left
    ">": lambda value, width: (value >> 1) | (value << (width - 1)),  # Rotate Right
    "@": lambda value, width: int(f"{value:0{width}b}"[::-1], 2),  # Bit Reversal
}
VALID_OPERAND_PREFIXES: frozenset[str] = frozenset(OPERAND_OPERATIONS)

# Regex pattern
INSTRUCTION_NAME_PATTERN: Pattern[str] = re_compile(r"^[A-Za-z]+$", IGNORECASE)
INTEGER_LITERAL_PATTERN: Pattern[str] = re_compile(
    r"^[+-]?(?:[0-9]+|0b[01]+|0o[0-7]+|0d[0-9]+|0x[0-9a-fA-F]+)$",
    IGNORECASE,
)
PSEUDO_PLACEHOLDER_PATTERN: Pattern[str] = re_compile(
    rf"^({'|'.join(escape(prefix) for prefix in sorted(VALID_OPERAND_PREFIXES))})?"
    r"{([0-9]+)}$"
)

# Instruction Length
MAX_INSTRUCTION_LENGTH: int = 128
BIT_MASKS: tuple[int, ...] = tuple(
    (1 << width) - 1 for width in range(1, MAX_INSTRUCTION_LENGTH + 1)
)
WIDTH_BOUNDS: tuple[tuple[int, int], ...] = tuple(
    (-(1 << width), 1 << (width + 1)) for width in range(MAX_INSTRUCTION_LENGTH)
)

from re import IGNORECASE, Pattern
from re import compile as re_compile
from typing import Final, Literal

# Architecture field names
ARCHITECTURE_NAME: Final[Literal["architecture_name"]] = "architecture_name"
INSTRUCTION_LENGTH: Final[Literal["instruction_length"]] = "instruction_length"
FILE_EXTENSION: Final[Literal["file_extension"]] = "file_extension"
ALIASES: Final[Literal["aliases"]] = "aliases"
INSTRUCTION_SET: Final[Literal["instruction_set"]] = "instruction_set"
PSEUDO_SET: Final[Literal["pseudo_instruction_set"]] = "pseudo_instruction_set"

KNOWN_ARCHITECTURE_FIELDS: frozenset[str] = frozenset(
    {ARCHITECTURE_NAME, INSTRUCTION_LENGTH, FILE_EXTENSION, ALIASES, INSTRUCTION_SET, PSEUDO_SET}
)

# Format lengths
INSTRUCTION_FORMAT_LENGTH: Final[int] = 2
PSEUDO_FORMAT_LENGTH: Final[int] = 2

# Regex pattern
DEFAULT_ALIAS_NAME_PATTERN: Pattern[str] = re_compile(
    r"^(?!\.)[\x21-\x2B\x2D-\x2E\x30-\x39\x3B-\x7E]+$", IGNORECASE
)
FILE_EXTENSION_PATTERN: Pattern[str] = re_compile(r"^\.[a-zA-Z0-9]+$", IGNORECASE)
BINARY_STRING_PATTERN: Pattern[str] = re_compile(r"^[01]+$")

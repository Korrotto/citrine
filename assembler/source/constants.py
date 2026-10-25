from re import IGNORECASE, Pattern
from re import compile as re_compile

# Line type
DEFINE_DIRECTIVE: str = "define"
USED_DIRECTIVE: str = "used"
PSEUDO_DIRECTIVE: str = "pseudo"
LABEL: str = "label"
INSTRUCTION: str = "instruction"

DIRECTIVES: frozenset[str] = frozenset({DEFINE_DIRECTIVE, USED_DIRECTIVE, PSEUDO_DIRECTIVE})

# Directive length
DEFINE_LENGTH = 4
USED_LENGTH = 2
PSEUDO_LENGTH = 4

# Directive keywords
AS_KEYWORD: str = "as"
TO_KEYWORD: str = "to"

# Diagnostic kinds
KIND_ALIAS: str = "alias"
KIND_LABEL: str = "label"
KIND_INSTRUCTION: str = "instruction"
KIND_PSEUDO: str = "pseudo-instruction"

# Regex pattern
ALIAS_NAME_PATTERN: Pattern[str] = re_compile(r"^[A-Za-z_][A-Za-z0-9_]*$", IGNORECASE)
LABEL_NAME_PATTERN: Pattern[str] = re_compile(r"^\.[A-Za-z0-9_]+$", IGNORECASE)

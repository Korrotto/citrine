from dataclasses import dataclass

from ..architecture.models import ArchitectureData, InstructionSet
from ..architecture.utils import variable_widths
from ..common.models import AliasValue, PseudoInstructionsSet
from ..common.utils import log_error, log_warning

type OperandWidths = list[frozenset[int]]


@dataclass(slots=True)
class TokenizedLine:
    line_number: int
    text: str
    tokens: tuple[str, ...]
    line_type: str


@dataclass(slots=True)
class ResolvedLine:
    tokenized_line: TokenizedLine
    instruction_name: str
    operand_values: tuple[int | None, ...]


@dataclass(slots=True)
class ExpandedLine:
    instruction_name: str
    operand_values: tuple[int, ...]


@dataclass(slots=True)
class AssemblyResult:
    machine_code: list[int]
    errors: list[str]
    warnings: list[str]
    instruction_lines: list[TokenizedLine]


class AssemblerContext:
    def __init__(self, architecture_data: ArchitectureData) -> None:
        default_aliases: dict[str, int] = architecture_data.aliases or {}
        self.default_alias_names: frozenset[str] = frozenset(default_aliases)
        self.aliases: dict[str, AliasValue] = dict(default_aliases)
        self.used_aliases: set[str] = set()
        self.used_pseudo_instructions: set[str] = set()
        default_pseudo_set: PseudoInstructionsSet = architecture_data.pseudo_set or {}
        self.default_pseudo_instruction_names: frozenset[str] = frozenset(default_pseudo_set)
        self.pseudo_set: PseudoInstructionsSet = dict(default_pseudo_set)
        self.instruction_set: InstructionSet = dict(architecture_data.instruction_set)
        self.instruction_variable_widths: dict[str, tuple[int, ...]] = {
            name: variable_widths(instruction_format)
            for name, instruction_format in self.instruction_set.items()
        }
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def get_unused_aliases(self) -> list[str]:
        return sorted(set(self.aliases) - self.default_alias_names - self.used_aliases)

    def get_unused_pseudo_instructions(self) -> list[str]:
        return sorted(
            set(self.pseudo_set)
            - self.default_pseudo_instruction_names
            - self.used_pseudo_instructions
        )

    def get_undefined_aliases(self) -> list[str]:
        return sorted(
            value
            for value in self.aliases.values()
            if isinstance(value, str) and value not in self.aliases
        )

    def get_used_aliases(self) -> list[str]:
        return sorted(self.used_aliases)

    @staticmethod
    def get_line_info(line: TokenizedLine | None) -> tuple[int | None, str | None]:
        return (line.line_number, line.text) if line is not None else (None, None)

    def log_error(self, code: str, *args: object, line: TokenizedLine | None = None) -> None:
        self.errors.append(log_error(code, *args, position=self.get_line_info(line)))

    def log_warning(self, code: str, *args: object, line: TokenizedLine | None = None) -> None:
        self.warnings.append(log_warning(code, *args, position=self.get_line_info(line)))

from ..common.constants import MAX_INSTRUCTION_LENGTH
from ..common.utils import normalize
from .constants import (
    ALIASES,
    ARCHITECTURE_NAME,
    FILE_EXTENSION,
    INSTRUCTION_LENGTH,
    KNOWN_ARCHITECTURE_FIELDS,
)
from .instructionvalidator import InstructionSetValidator
from .pseudovalidator import PseudoSetValidator
from .utils import is_valid_default_alias, is_valid_file_extension
from .validationcontext import ValidationContext


class ArchitectureValidator:
    def __init__(self, raw_data: dict[str, object]) -> None:
        self.context = ValidationContext(raw_data)
        self.instruction_set_validator = InstructionSetValidator(self.context)
        self.pseudo_set_validator = PseudoSetValidator(self.context)

    def get_errors(self) -> list[str]:
        return self.context.errors

    def has_errors(self) -> bool:
        return bool(self.context.errors)

    def validate_architecture_data(self) -> None:
        seen_names: set[str] = set()
        self.validate_unknown_fields()
        self.validate_architecture_name()
        self.validate_instruction_length()
        self.validate_file_extension()
        self.validate_aliases()
        self.instruction_set_validator.validate(seen_names)
        self.pseudo_set_validator.validate(seen_names)

    def validate_unknown_fields(self) -> None:
        for field in sorted(self.context.raw_data.keys() - KNOWN_ARCHITECTURE_FIELDS, key=str):
            self.context.log_error("ARCH-001", field)

    def validate_architecture_name(self) -> None:
        if self.context.require(ARCHITECTURE_NAME, "ARCH-002"):
            name = self.context.raw_data[ARCHITECTURE_NAME]
            if not isinstance(name, str) or not name.strip():
                self.context.log_error("ARCH-004", ARCHITECTURE_NAME, "name")

    def validate_instruction_length(self) -> None:
        if self.context.require(INSTRUCTION_LENGTH, "ARCH-002"):
            length = self.context.raw_data[INSTRUCTION_LENGTH]
            if type(length) is not int or not 0 < length <= MAX_INSTRUCTION_LENGTH:
                self.context.log_error("ARCH-004", INSTRUCTION_LENGTH, "integer")

    def validate_file_extension(self) -> None:
        if self.context.require(FILE_EXTENSION, "ARCH-002"):
            extension = self.context.raw_data[FILE_EXTENSION]
            if not isinstance(extension, str) or not is_valid_file_extension(extension):
                self.context.log_error("ARCH-004", FILE_EXTENSION, "file extension")

    def validate_aliases(self) -> None:
        if ALIASES not in self.context.raw_data:
            return

        aliases = self.context.raw_data[ALIASES]
        if not isinstance(aliases, dict):
            return self.context.log_error("ARCH-003", ALIASES)

        seen_aliases: set[str] = set()
        for alias, value in aliases.items():
            self.validate_single_alias(alias, value, seen_aliases)

    def validate_single_alias(self, alias: object, value: object, seen_aliases: set[str]) -> None:
        if not isinstance(alias, str) or not is_valid_default_alias(alias):
            return self.context.log_error("ARCH-006", ALIASES, alias)
        if normalize(alias) in seen_aliases:
            self.context.log_error("ARCH-007", ALIASES, alias)

        seen_aliases.add(normalize(alias))
        if type(value) is not int:
            self.context.log_error("ARCH-008", alias)

from ..common.models import PseudoInstructionsSet, TranslationSpec
from ..common.translationparser import TranslationParser
from ..common.utils import is_variable_field, normalize, parse_decimal
from .constants import (
    ALIASES,
    ARCHITECTURE_NAME,
    FILE_EXTENSION,
    INSTRUCTION_LENGTH,
    INSTRUCTION_SET,
    PSEUDO_SET,
)
from .models import (
    ArchitectureData,
    BitField,
    FixedBits,
    InstructionSet,
    ValidatedArchitectureData,
    VariableBits,
)
from .utils import variable_widths


class ArchitectureConstructor:
    def __init__(self, validated_data: ValidatedArchitectureData) -> None:
        self.validated_data: ValidatedArchitectureData = validated_data

    def construct_architecture_data(self) -> ArchitectureData:
        validated_data: ValidatedArchitectureData = self.validated_data
        instruction_set: InstructionSet = self.construct_instruction_set()

        return ArchitectureData(
            validated_data[ARCHITECTURE_NAME],
            validated_data[INSTRUCTION_LENGTH],
            instruction_set,
            validated_data[FILE_EXTENSION],
            self.construct_aliases(),
            self.construct_pseudo_set(instruction_set),
        )

    def construct_aliases(self) -> dict[str, int] | None:
        if (default_aliases := self.validated_data.get(ALIASES)) is None:
            return None
        return {normalize(name): value for name, value in default_aliases.items()}

    def construct_instruction_set(self) -> InstructionSet:
        instruction_set = self.validated_data[INSTRUCTION_SET]
        return {
            normalize(name): tuple(
                map(self.parse_bit_field, (instruction_format[0], *instruction_format[1].split()))
            )
            for name, instruction_format in instruction_set.items()
        }

    @staticmethod
    def parse_bit_field(token: str) -> BitField:
        if is_variable_field(token):
            width = parse_decimal(token[1:])
            if width is None:
                raise ValueError(f"Invalid variable field: {token!r}")
            return VariableBits(width)
        return FixedBits(int(token, 2), len(token))

    def construct_pseudo_set(self, instruction_set: InstructionSet) -> PseudoInstructionsSet | None:
        if (default_pseudo_set := self.validated_data.get(PSEUDO_SET)) is None:
            return None

        pseudo_set: PseudoInstructionsSet = {}

        for name, translation_text in default_pseudo_set.items():
            translation_tokens: tuple[str, ...] = tuple(normalize(translation_text).split())
            base_name: str = translation_tokens[0]
            base_operand_widths: tuple[int, ...] = variable_widths(instruction_set[base_name])
            pseudo_slots, _ = TranslationParser.parse(
                TranslationSpec(translation_tokens[1:], base_operand_widths, normalize(name))
            )
            pseudo_set[normalize(name)] = (base_name, pseudo_slots)

        return pseudo_set

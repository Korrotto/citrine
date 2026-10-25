from typing import cast

from ..common.models import InvalidIndex, InvalidToken, PlaceholderSlot
from ..common.translationparser import has_contiguous_indices, parse_slot_token
from ..common.utils import fits_in_width, is_valid_instruction, normalize
from .constants import INSTRUCTION_SET, PSEUDO_SET
from .utils import is_valid_target_format, parse_operand_widths
from .validationcontext import ValidationContext


class PseudoSetValidator:
    def __init__(self, context: ValidationContext) -> None:
        self.context = context

    def validate(self, seen_names: set[str]) -> None:
        if PSEUDO_SET not in self.context.raw_data:
            return
        tables = self.require_pseudo_tables()
        if tables is None:
            return
        lowered_targets, pseudo_instructions = tables
        self.validate_all_pseudos(pseudo_instructions, seen_names, lowered_targets)

    def require_pseudo_tables(
        self,
    ) -> tuple[dict[str, object], dict[object, object]] | None:
        instructions = self.context.raw_data.get(INSTRUCTION_SET)
        if not isinstance(instructions, dict):
            self.context.log_error("ARCH-016")
            return None
        pseudo_instructions = self.context.raw_data[PSEUDO_SET]
        if not isinstance(pseudo_instructions, dict):
            self.context.log_error("ARCH-003", PSEUDO_SET)
            return None
        lowered_targets = {
            normalize(name): fmt for name, fmt in instructions.items() if isinstance(name, str)
        }
        return lowered_targets, pseudo_instructions

    def validate_all_pseudos(
        self,
        pseudo_instructions: dict[object, object],
        seen_names: set[str],
        lowered_targets: dict[str, object],
    ) -> None:
        seen_pseudo_names: set[str] = set()
        for pseudo_name, translation in pseudo_instructions.items():
            if not self.claim_pseudo_name(pseudo_name, seen_names, seen_pseudo_names):
                continue
            self.validate_pseudo_translation(cast(str, pseudo_name), translation, lowered_targets)

    def claim_pseudo_name(
        self, pseudo_name: object, seen_names: set[str], seen_pseudo_names: set[str]
    ) -> bool:
        if not isinstance(pseudo_name, str) or not is_valid_instruction(pseudo_name):
            self.context.log_error("ARCH-006", PSEUDO_SET, pseudo_name)
            return False
        key = normalize(pseudo_name)
        if key in seen_names:
            self.context.log_error("ARCH-017", pseudo_name)
        if key in seen_pseudo_names:
            self.context.log_error("ARCH-007", PSEUDO_SET, pseudo_name)
        seen_pseudo_names.add(key)
        return True

    def validate_pseudo_translation(
        self, pseudo_name: str, translation: object, targets: dict[str, object]
    ) -> None:
        if not isinstance(translation, str):
            self.context.log_error("ARCH-018", pseudo_name)
            return
        self.validate_translation(pseudo_name, translation, targets)

    def validate_translation(
        self, pseudo_name: str, translation: str, targets: dict[str, object]
    ) -> None:
        parsed = self.split_translation(translation, pseudo_name)
        if parsed is None:
            return None
        target_name, arguments = parsed
        format_string = self.target_format_string(target_name, targets, pseudo_name)
        if format_string is None:
            return None
        widths = parse_operand_widths(format_string)
        if len(arguments) != len(widths):
            return self.context.log_error("ARCH-021", pseudo_name, target_name)

        seen_indices = self.validate_translation_arguments(
            arguments, widths, pseudo_name, target_name
        )
        self.check_placeholder_order(seen_indices, pseudo_name)

    def split_translation(self, translation: str, pseudo_name: str) -> tuple[str, list[str]] | None:
        tokens = normalize(translation).split()
        if not tokens:
            self.context.log_error("ARCH-018", pseudo_name)
            return None
        return tokens[0], tokens[1:]

    def target_format_string(
        self, target_name: str, targets: dict[str, object], pseudo_name: str
    ) -> str | None:
        if target_name not in targets:
            self.context.log_error("ARCH-019", pseudo_name)
            return None
        if not is_valid_target_format(targets[target_name]):
            self.context.log_error("ARCH-020", pseudo_name)
            return None
        target_format = cast(list[object], targets[target_name])
        return cast(str, target_format[1])

    def validate_translation_arguments(
        self, arguments: list[str], widths: list[int], pseudo_name: str, target_name: str
    ) -> set[int]:
        seen_indices: set[int] = set()
        for argument, width in zip(arguments, widths, strict=True):
            parsed_slot = parse_slot_token(argument)
            if isinstance(parsed_slot, InvalidIndex):
                self.context.log_error("ARCH-022", pseudo_name)
            elif isinstance(parsed_slot, InvalidToken):
                self.context.log_error("ARCH-022", pseudo_name)
            elif isinstance(parsed_slot, PlaceholderSlot):
                seen_indices.add(parsed_slot.index)
            else:
                self.validate_literal(parsed_slot.value, width, pseudo_name, target_name)
        return seen_indices

    def validate_literal(self, value: int, width: int, pseudo_name: str, target_name: str) -> None:
        if width <= 0:
            self.context.log_error("ARCH-023", pseudo_name, target_name)
        elif not fits_in_width(value, width):
            self.context.log_error("TRN-004", value, width)

    def check_placeholder_order(self, seen_indices: set[int], pseudo_name: str) -> None:
        if not has_contiguous_indices(seen_indices):
            self.context.log_error("ARCH-024", pseudo_name)

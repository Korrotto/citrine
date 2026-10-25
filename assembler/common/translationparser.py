from .constants import MAX_INSTRUCTION_LENGTH, PSEUDO_PLACEHOLDER_PATTERN
from .message import make_message
from .models import (
    InvalidIndex,
    InvalidToken,
    LiteralSlot,
    ParsedSlot,
    ParsedTranslation,
    PlaceholderSlot,
    PseudoSlot,
    TranslationSpec,
    TranslationWarning,
)
from .utils import (
    convert_to_integer,
    fits_in_width,
    is_integer_literal,
    mask_to_width,
    parse_decimal,
)


def parse_placeholder(token: str) -> tuple[str, int] | None:
    if not (match := PSEUDO_PLACEHOLDER_PATTERN.fullmatch(token)):
        return None
    index = parse_decimal(match.group(2))
    if index is None:
        return None
    return match.group(1) or "", index


def parse_slot_token(token: str) -> ParsedSlot:
    if (placeholder := parse_placeholder(token)) is not None:
        operation, index = placeholder
        if 0 <= index < MAX_INSTRUCTION_LENGTH:
            return PlaceholderSlot(operation, index)
        return InvalidIndex(index)

    if is_integer_literal(token):
        return LiteralSlot(convert_to_integer(token))

    return InvalidToken(token)


def has_contiguous_indices(indices: set[int]) -> bool:
    return not indices or len(indices) == max(indices) + 1


class InvalidTranslationError(ValueError):
    def __init__(self, code: str, *args: object) -> None:
        super().__init__(make_message(code, *args))
        self.code = code
        self.params = args


class TranslationParser:
    @staticmethod
    def parse(spec: TranslationSpec) -> ParsedTranslation:
        slots = [TranslationParser.parse_slot(token, spec) for token in spec.tokens]

        if len(slots) != len(spec.widths):
            raise TranslationParser.error("TRN-003", spec.pseudo_name)

        TranslationParser.check_indices(slots, spec)
        return TranslationParser.mask_literals(slots, spec)

    @staticmethod
    def error(code: str, *args: object) -> InvalidTranslationError:
        return InvalidTranslationError(code, *args)

    @staticmethod
    def parse_slot(token: str, spec: TranslationSpec) -> PseudoSlot:
        parsed_slot = parse_slot_token(token)

        if isinstance(parsed_slot, InvalidIndex):
            raise TranslationParser.error("TRN-001", parsed_slot.index, spec.pseudo_name)
        if isinstance(parsed_slot, InvalidToken):
            raise TranslationParser.error("TRN-002", parsed_slot.token)
        return parsed_slot

    @staticmethod
    def check_indices(slots: list[PseudoSlot], spec: TranslationSpec) -> None:
        indices = {slot.index for slot in slots if isinstance(slot, PlaceholderSlot)}
        if not has_contiguous_indices(indices):
            raise TranslationParser.error("TRN-001", max(indices), spec.pseudo_name)

    @staticmethod
    def mask_literals(slots: list[PseudoSlot], spec: TranslationSpec) -> ParsedTranslation:
        masked: list[PseudoSlot] = []
        warnings: list[TranslationWarning] = []

        for slot, width in zip(slots, spec.widths, strict=True):
            if isinstance(slot, PlaceholderSlot):
                masked.append(slot)
                continue

            if not fits_in_width(slot.value, width):
                warnings.append(("TRN-004", (slot.value, width)))
            masked.append(LiteralSlot(mask_to_width(slot.value, width)))

        return tuple(masked), warnings

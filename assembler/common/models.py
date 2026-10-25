from dataclasses import dataclass

type AliasValue = str | int


@dataclass(slots=True)
class LiteralSlot:
    value: int


@dataclass(slots=True)
class PlaceholderSlot:
    operation: str
    index: int


@dataclass(slots=True)
class InvalidToken:
    token: str


@dataclass(slots=True)
class InvalidIndex:
    index: int


type PseudoSlot = LiteralSlot | PlaceholderSlot
type SlotError = InvalidToken | InvalidIndex
type ParsedSlot = PseudoSlot | SlotError
type PseudoTranslation = tuple[str, tuple[PseudoSlot, ...]]
type TranslationWarning = tuple[str, tuple[object, ...]]
type ParsedTranslation = tuple[tuple[PseudoSlot, ...], list[TranslationWarning]]
type PseudoInstructionsSet = dict[str, PseudoTranslation]


@dataclass(slots=True)
class TranslationSpec:
    tokens: tuple[str, ...]
    widths: tuple[int, ...]
    pseudo_name: str

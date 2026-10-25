from dataclasses import dataclass
from typing import NotRequired, ReadOnly, TypedDict

from ..common.models import PseudoInstructionsSet


@dataclass(slots=True)
class FixedBits:
    value: int
    width: int


@dataclass(slots=True)
class VariableBits:
    width: int


type BitField = FixedBits | VariableBits
type InstructionSet = dict[str, tuple[BitField, ...]]


class ValidatedArchitectureData(TypedDict):
    architecture_name: ReadOnly[str]
    instruction_length: ReadOnly[int]
    instruction_set: ReadOnly[dict[str, list[str]]]
    file_extension: ReadOnly[str]
    aliases: ReadOnly[NotRequired[dict[str, int]]]
    pseudo_instruction_set: ReadOnly[NotRequired[dict[str, str]]]


@dataclass(slots=True)
class ArchitectureData:
    architecture_name: str
    instruction_length: int
    instruction_set: InstructionSet
    file_extension: str
    aliases: dict[str, int] | None = None
    pseudo_set: PseudoInstructionsSet | None = None

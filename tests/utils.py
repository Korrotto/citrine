"""Example architecture and shortcuts shared by the tests."""

from copy import deepcopy
from typing import cast

from assembler.architecture.constructor import ArchitectureConstructor
from assembler.architecture.models import ArchitectureData, ValidatedArchitectureData
from assembler.architecture.validator import ArchitectureValidator
from assembler.pipeline import assemble_program
from assembler.source.models import (
    AssemblerContext,
    AssemblyResult,
    ResolvedLine,
    TokenizedLine,
)
from assembler.source.operandresolver import OperandResolver
from assembler.source.preprocessor import Preprocessor
from assembler.source.tokenizer import Tokenizer

BASE_ARCHITECTURE: dict[str, object] = {
    "architecture_name": "Test Core",
    "instruction_length": 8,
    "instruction_set": {
        "ADD": ["00", "x2 x2 x2"],
        "JMP": ["01", "x6"],
        "HLT": ["11", "000000"],
    },
    "aliases": {"R1": 1, "R2": 2, "ZERO": 0},
    "file_extension": ".tst",
}

BASE_ARCHITECTURE_WITH_PSEUDO: dict[str, object] = BASE_ARCHITECTURE | {
    "pseudo_instruction_set": {
        "NEG": "ADD 0 -{0} 0",
        "REV": "ADD 0 @{0} 0",
        "INC": "ADD {0} {0} 1",
    }
}


def make_architecture(**overrides: object) -> dict[str, object]:
    return deepcopy(BASE_ARCHITECTURE) | overrides


def make_pseudo_architecture(**overrides: object) -> dict[str, object]:
    return deepcopy(BASE_ARCHITECTURE_WITH_PSEUDO) | overrides


def build_architecture(data: dict[str, object]) -> ArchitectureData:
    constructor = ArchitectureConstructor(cast(ValidatedArchitectureData, data))
    return constructor.construct_architecture_data()


def build_context(data: dict[str, object] | None = None) -> AssemblerContext:
    return AssemblerContext(build_architecture(data if data is not None else make_architecture()))


def validate_architecture(data: dict[str, object]) -> list[str]:
    validator = ArchitectureValidator(data)
    validator.validate_architecture_data()
    return validator.get_errors()


def assemble(source: str, data: dict[str, object] | None = None) -> AssemblyResult:
    return assemble_program(source, data if data is not None else make_architecture())


def to_instruction_lines(source: str, context: AssemblerContext) -> list[TokenizedLine]:
    preprocessor = Preprocessor(context)
    lines = preprocessor.process_lines(Tokenizer.tokenize_source_code(source))
    preprocessor.mark_used_aliases(lines)
    preprocessor.mark_used_pseudo_instructions(lines)
    return lines


def to_resolved_lines(source: str, context: AssemblerContext) -> list[ResolvedLine]:
    return list(OperandResolver(context).resolve_operands(to_instruction_lines(source, context)))

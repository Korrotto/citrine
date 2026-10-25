from typing import cast

from assembler.common.utils import check_input_types

from .architecture.constructor import ArchitectureConstructor
from .architecture.models import ValidatedArchitectureData
from .architecture.validator import ArchitectureValidator
from .source.codegenerator import CodeGenerator
from .source.instructionvalidator import InstructionValidator
from .source.models import AssemblerContext, AssemblyResult, ResolvedLine, TokenizedLine
from .source.operandresolver import OperandResolver
from .source.preprocessor import Preprocessor
from .source.pseudoexpander import PseudoExpander
from .source.tokenizer import Tokenizer


def assemble_program(source_code: str, architecture_data: dict[str, object]) -> AssemblyResult:
    pipeline = AssemblerPipeline(source_code, architecture_data)
    return pipeline.assemble()


class AssemblerPipeline:
    def __init__(self, source_code: str, architecture_data: dict[str, object]) -> None:
        check_input_types(source_code, architecture_data)
        self.source_code = source_code
        self.architecture_data = architecture_data
        self.context: AssemblerContext
        self.instruction_lines: list[TokenizedLine] = []
        self.resolved_lines: list[ResolvedLine] = []

    def assemble(self) -> AssemblyResult:
        built = self.build_context()
        if isinstance(built, AssemblyResult):
            return built
        self.context = built

        self.instruction_lines = self.preprocess_source()
        self.resolved_lines = self.resolve_instructions()

        if self.context.errors:
            return AssemblyResult(
                [], self.context.errors, self.context.warnings, self.instruction_lines
            )

        return AssemblyResult(
            self.generate_output(), [], self.context.warnings, self.instruction_lines
        )

    def build_context(self) -> AssemblerContext | AssemblyResult:
        architecture_validator = ArchitectureValidator(self.architecture_data)
        architecture_validator.validate_architecture_data()
        if architecture_validator.has_errors():
            return AssemblyResult([], architecture_validator.get_errors(), [], [])
        validated_data = cast(ValidatedArchitectureData, self.architecture_data)
        constructor = ArchitectureConstructor(validated_data)
        return AssemblerContext(constructor.construct_architecture_data())

    def preprocess_source(self) -> list[TokenizedLine]:
        tokenized_lines = Tokenizer.tokenize_source_code(self.source_code)
        preprocessor = Preprocessor(self.context)
        instruction_lines = preprocessor.process_lines(tokenized_lines)
        preprocessor.mark_used_aliases(instruction_lines)
        preprocessor.mark_used_pseudo_instructions(instruction_lines)
        return instruction_lines

    def resolve_instructions(self) -> list[ResolvedLine]:
        resolver = OperandResolver(self.context)
        resolved_iterable = resolver.resolve_operands(self.instruction_lines)
        resolved_lines = list(resolved_iterable)
        validator = InstructionValidator(self.context)
        validator.validate_instructions(resolved_lines)
        return resolved_lines

    def generate_output(self) -> list[int]:
        expander = PseudoExpander(self.context)
        expanded_lines = expander.expand_pseudo_instructions(self.resolved_lines)
        generator = CodeGenerator(self.context)
        return generator.generate_machine_code(expanded_lines)

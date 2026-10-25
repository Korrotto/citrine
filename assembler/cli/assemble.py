from argparse import Namespace
from pathlib import Path

from assembler import assemble_program
from assembler.architecture.constants import FILE_EXTENSION, INSTRUCTION_LENGTH
from assembler.cli.constants import EXIT_OK, STDIN
from assembler.cli.utils import (
    ENCODERS,
    read_architecture,
    read_source,
    report,
    write_code,
    write_list,
)
from assembler.common.utils import log_warning
from assembler.source import AssemblyResult


class AssemblerCommand:
    def __init__(self, args: Namespace) -> None:
        self.args = args
        self.file_name = Path(self.args.source).name
        self.instruction_length: int = 0

    def execute(self) -> int:
        source_code: str = read_source(self.args.source)
        architecture_data: dict[str, object] = read_architecture(self.args.architecture)
        self.instruction_length = self.get_instruction_length(architecture_data)
        result: AssemblyResult = assemble_program(source_code, architecture_data)
        extension_warning: str | None = self.get_extension_warning(architecture_data)

        if extension_warning is not None:
            result.warnings.append(extension_warning)

        exit_code: int = report(result.errors, result.warnings, self.args, self.file_name)

        if exit_code != EXIT_OK or self.args.check:
            return exit_code

        words: list[str] = self.encode_machine_code(result)
        if not words:
            return EXIT_OK

        write_code(self.args, "\n".join(words), self.file_name)
        self.write_listing(result, words)

        return EXIT_OK

    def get_instruction_length(self, architecture_data: dict[str, object]) -> int:
        length: object = architecture_data.get(INSTRUCTION_LENGTH)
        return length if isinstance(length, int) else 0

    def get_extension_warning(self, architecture_data: dict[str, object]) -> str | None:
        if self.args.source == STDIN:
            return None

        extension: object = architecture_data.get(FILE_EXTENSION)
        source_extension: str = Path(self.args.source).suffix

        if not isinstance(extension, str) or source_extension.lower() == extension.lower():
            return None

        return log_warning("SRC-012", source_extension, extension)

    def encode_machine_code(self, result: AssemblyResult) -> list[str]:
        args = self.args
        return ENCODERS[args.format](result.machine_code, self.instruction_length, args.no_pad)

    def write_listing(self, result: AssemblyResult, words: list[str]) -> None:
        if self.args.listing is None:
            return

        write_list(self.args, self.format_listing(result, words), self.file_name)

    def format_listing(self, result: AssemblyResult, words: list[str]) -> str:
        address_width: int = max(7, len(f"{len(words) - 1:x}"))
        word_width: int = max((len(word) for word in words), default=4)

        rows: list[str] = [f"{'ADDRESS':<{address_width}}  {'WORD':<{word_width}}  SOURCE"]

        for address, (word, source) in enumerate(zip(words, result.instruction_lines, strict=True)):
            rows.append(f"{address:0{address_width}x}  {word:>{word_width}}  {source.text}")

        return "\n".join(rows)

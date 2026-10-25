import sys
from argparse import Namespace
from json import dumps
from pathlib import Path
from typing import cast

from assembler.architecture import (
    ArchitectureConstructor,
    ArchitectureData,
    ArchitectureValidator,
    ValidatedArchitectureData,
)
from assembler.cli.constants import EXIT_ERRORS, EXIT_OK
from assembler.cli.utils import read_json, report


class ArchitectureCommand:
    def __init__(self, args: Namespace) -> None:
        self.args = args
        self.file_name = Path(self.args.arch).name
        self.is_valid_architecture_data = False
        self.architecture_data: ArchitectureData | None = None

    def execute(self) -> int:
        self.build_architecture_data()
        if self.args.architecture_command == "validate":
            return self.validate_architecture()
        return self.show_architecture()

    def validate_architecture(self) -> int:
        if not self.is_valid_architecture_data:
            return EXIT_ERRORS

        print(f"{self.args.arch}: ok")
        return EXIT_OK

    def show_architecture(self) -> int:
        if self.architecture_data is None:
            return EXIT_ERRORS

        architecture = self.architecture_data

        summary: dict[str, object] = {
            "architecture_name": architecture.architecture_name,
            "file_extension": architecture.file_extension,
            "instruction_length": architecture.instruction_length,
            "instructions": len(architecture.instruction_set),
            "pseudo_instructions": (
                len(architecture.pseudo_set) if architecture.pseudo_set is not None else 0
            ),
        }

        print(dumps(summary, indent=2))
        return EXIT_OK

    def build_architecture_data(self) -> None:
        data: object = read_json(self.args.arch)

        if not isinstance(data, dict):
            print("citrine architecture: architecture JSON file must be an object", file=sys.stderr)
            return None

        architecture_data = cast(dict[str, object], data)

        validator = ArchitectureValidator(architecture_data)
        validator.validate_architecture_data()

        exit_code = report(validator.get_errors(), [], self.args, self.file_name)

        if exit_code != EXIT_OK:
            return None

        validated_data = cast(ValidatedArchitectureData, architecture_data)
        constructor = ArchitectureConstructor(validated_data)

        self.architecture_data = constructor.construct_architecture_data()
        self.is_valid_architecture_data = True

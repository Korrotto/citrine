import sys
from argparse import ArgumentParser, Namespace

from assembler.cli.architecture import ArchitectureCommand
from assembler.cli.assemble import AssemblerCommand
from assembler.cli.constants import (
    EXIT_USAGE,
    KNOWN_COMMANDS,
    SPECIAL_OPTIONS,
)
from assembler.cli.parser import Parser


def dispatch(args: Namespace) -> int:
    if args.command in {"arch", "architecture"}:
        return ArchitectureCommand(args).execute()

    return AssemblerCommand(args).execute()


def default_to_assemble(argv: list[str]) -> list[str]:
    if argv and argv[0] not in KNOWN_COMMANDS | SPECIAL_OPTIONS:
        return ["assemble", *argv]

    return argv


def main() -> int:
    argv: list[str] = default_to_assemble(sys.argv[1:])
    parser: ArgumentParser = Parser.build_parser()
    args: Namespace = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return EXIT_USAGE

    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())

from argparse import ArgumentParser

from assembler.cli.constants import STDERR, STDIN, STDOUT
from assembler.cli.utils import package_version


class Parser:
    @staticmethod
    def build_parser() -> ArgumentParser:
        parser = ArgumentParser(
            prog="citrine", description="Generic assembler controlled by an architecture file."
        )
        parser.add_argument(
            "-v", "--version", action="version", version=f"citrine {package_version()}"
        )
        subparsers = parser.add_subparsers(dest="command")

        Parser.add_assemble(subparsers.add_parser("assemble", help="Assemble a source file"))
        Parser.add_arch(
            subparsers.add_parser("arch", aliases=["architecture"], help="Architecture operation")
        )

        return parser

    @staticmethod
    def add_assemble(parser: ArgumentParser) -> None:
        parser.add_argument("source", metavar="source", help=f"Source file, '{STDIN}' for stdin")
        parser.add_argument(
            "-a", "--architecture", required=True, metavar="PATH", help="Architecture file"
        )
        parser.add_argument(
            "-o",
            "--output",
            metavar="PATH",
            default=STDOUT,
            help=f"Output file, '{STDOUT}' for stdout",
        )
        parser.add_argument(
            "-f", "--format", choices=["dec", "hex", "bin"], default="bin", help="Output format"
        )
        parser.add_argument(
            "-c", "--check", action="store_true", help="Assemble without write file"
        )
        parser.add_argument(
            "-l", "--listing", metavar="PATH", help=f"Listing output file, '{STDOUT}' for stdout"
        )
        parser.add_argument("-p", "--no-pad", action="store_true", help="Disable line padding")
        parser.add_argument("-q", "--quiet", action="store_true", help="Hide warnings")
        parser.add_argument("-s", "--strict", action="store_true", help="Warnings = Errors")
        Parser.add_diagnostics(parser)

    @staticmethod
    def add_diagnostics(parser: ArgumentParser) -> None:
        parser.add_argument(
            "-d",
            "--diagnostics",
            choices=["text", "json"],
            default="text",
            help="Diagnostics format",
        )
        parser.add_argument(
            "-D",
            "--diagnostics-output",
            metavar="PATH",
            default=STDERR,
            help=f"Diagnostics output file, '{STDERR}' for stderr",
        )

    @staticmethod
    def add_arch(parser: ArgumentParser) -> None:
        actions = parser.add_subparsers(dest="architecture_command", required=True)
        validate = actions.add_parser("validate", help="Architecture validation")
        validate.add_argument("arch", metavar="Architecture file")
        Parser.add_diagnostics(validate)
        show = actions.add_parser("show", help="Architecture information")
        show.add_argument("arch", metavar="Architecture file")
        Parser.add_diagnostics(show)

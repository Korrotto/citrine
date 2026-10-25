import io
import json
import sys
from argparse import Namespace
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest
from assembler.cli.architecture import ArchitectureCommand
from assembler.cli.assemble import AssemblerCommand
from assembler.cli.cli import default_to_assemble
from assembler.cli.constants import (
    EXIT_ERRORS,
    EXIT_IO,
    EXIT_OK,
    EXIT_USAGE,
    FALLBACK_VERSION,
    STDERR,
    STDIN,
    STDOUT,
)
from assembler.cli.parser import Parser, package_version
from assembler.cli.utils import (
    ENCODERS,
    binary_encode,
    decimal_encode,
    hexa_encode,
    read_architecture,
    read_json,
    read_source,
    report,
    write_file,
)

from tests.utils import make_architecture, make_pseudo_architecture

INVALID_ARGUMENTS = [
    pytest.param(["assemble", "src.tst"], id="missing-architecture"),
    pytest.param(["assemble", "-a", "arch.json"], id="missing-source"),
    pytest.param(["assemble", "src.tst", "-a", "arch.json", "-f", "base64"], id="invalid-format"),
    pytest.param(["assemble", "src.tst", "-a", "arch.json", "--nope"], id="unknown-option"),
    pytest.param(["arch"], id="missing-arch-action"),
    pytest.param(["arch", "frobnicate", "arch.json"], id="invalid-arch-action"),
    pytest.param(["frobnicate"], id="unknown-command"),
]

DEFAULT_TO_ASSEMBLE_CASES = [
    pytest.param([], [], id="empty"),
    pytest.param(
        ["prog.tst", "-a", "arch.json"],
        ["assemble", "prog.tst", "-a", "arch.json"],
        id="assemble-default",
    ),
    pytest.param(["-", "-a", "arch.json"], ["assemble", "-", "-a", "arch.json"], id="stdin"),
    pytest.param(["arch", "validate", "arch.json"], ["arch", "validate", "arch.json"], id="arch"),
    pytest.param(["-h"], ["-h"], id="help"),
    pytest.param(["--version"], ["--version"], id="version"),
]


def make_args(**overrides: object) -> Namespace:
    defaults: dict[str, object] = {
        "source": "prog.tst",
        "architecture": "arch.json",
        "output": "-",
        "format": "bin",
        "check": False,
        "listing": None,
        "no_pad": False,
        "quiet": False,
        "strict": False,
        "diagnostics": "text",
        "diagnostics_output": "-",
        "architecture_command": "validate",
        "arch": "arch.json",
    }
    return Namespace(**(defaults | overrides))


def write_project(tmp_path: Path) -> tuple[Path, Path]:
    architecture_file = tmp_path / "arch.json"
    architecture_file.write_text(json.dumps(make_architecture()), encoding="utf-8")
    source_file = tmp_path / "prog.tst"
    source_file.write_text("ADD R1 R2 ZERO\nHLT\n", encoding="utf-8")
    return source_file, architecture_file


def run_command(source_file: Path | str, architecture_file: Path, **overrides: object) -> int:
    args = make_args(
        source=str(source_file),
        architecture=str(architecture_file),
        **overrides,
    )
    return AssemblerCommand(args).execute()


@pytest.fixture
def parser() -> Parser:
    return Parser.build_parser()


@pytest.fixture
def project(tmp_path) -> tuple[Path, Path]:
    return write_project(tmp_path)


def test_parser_defaults_and_all_options(parser):
    args = parser.parse_args(["assemble", "prog.tst", "-a", "arch.json"])
    assert (args.command, args.source, args.architecture) == ("assemble", "prog.tst", "arch.json")
    assert (args.output, args.format, args.check, args.listing) == ("-", "bin", False, None)
    assert (args.no_pad, args.quiet, args.strict) == (False, False, False)
    assert (args.diagnostics, args.diagnostics_output) == ("text", "-")

    args = parser.parse_args(
        [
            "assemble",
            "src.tst",
            "-a",
            "arch.json",
            "-o",
            "out.bin",
            "-f",
            "hex",
            "-c",
            "-l",
            "prog.lst",
            "-p",
            "-q",
            "-s",
            "-d",
            "json",
            "-D",
            "diag.json",
        ]
    )
    assert (args.output, args.format, args.check, args.listing) == (
        "out.bin",
        "hex",
        True,
        "prog.lst",
    )
    assert (args.no_pad, args.quiet, args.strict) == (True, True, True)
    assert (args.diagnostics, args.diagnostics_output) == ("json", "diag.json")

    for argv in (["arch", "validate", "arch.json"], ["architecture", "show", "arch.json"]):
        command = parser.parse_args(argv)
        assert command.command == argv[0]
        assert command.architecture_command == argv[1]
        assert command.arch == "arch.json"


@pytest.mark.parametrize("argv", INVALID_ARGUMENTS)
def test_parser_rejects_invalid_arguments(argv, parser):
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(argv)
    assert excinfo.value.code == EXIT_USAGE


def test_package_version_falls_back_without_metadata(monkeypatch):
    def missing(_: str) -> str:
        raise PackageNotFoundError("citrine-assembler")

    monkeypatch.setattr("assembler.cli.utils.version", missing)
    assert package_version() == FALLBACK_VERSION


@pytest.mark.parametrize(("argv", "expected"), DEFAULT_TO_ASSEMBLE_CASES)
def test_default_to_assemble(argv, expected):
    assert default_to_assemble(argv) == expected


def test_exit_codes_and_stream_constants():
    assert (EXIT_OK, EXIT_ERRORS, EXIT_USAGE, EXIT_IO) == (0, 1, 2, 3)
    assert (STDIN, STDOUT, STDERR) == ("-", "-", "-")


def test_encoders():
    assert binary_encode([5, 255], 8, False) == ["00000101", "11111111"]
    assert binary_encode([5], 8, True) == ["101"]
    assert hexa_encode([255, 16, 0x8000], 18, False) == ["000ff", "00010", "08000"]
    assert decimal_encode([5, 255], 8, False) == ["005", "255"]
    assert ENCODERS == {"bin": binary_encode, "hex": hexa_encode, "dec": decimal_encode}


def test_read_helpers(tmp_path, monkeypatch, capsys):
    doc = tmp_path / "doc.json"
    doc.write_text('{"x": 1}', encoding="utf-8")
    assert read_json(str(doc)) == {"x": 1}
    assert read_architecture(str(doc)) == {"x": 1}

    bom_doc = tmp_path / "bom.json"
    bom_doc.write_text('\ufeff{"x": 1}', encoding="utf-8")
    assert read_json(str(bom_doc)) == {"x": 1}

    source = tmp_path / "prog.tst"
    source.write_text("HLT\n", encoding="utf-8")
    assert read_source(str(source)) == "HLT\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO("HLT\n"))
    assert read_source("-") == "HLT\n"

    non_object = tmp_path / "array.json"
    non_object.write_text("[1]", encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        read_architecture(str(non_object))
    assert excinfo.value.code == EXIT_ERRORS
    assert "must be an object" in capsys.readouterr().err

    with pytest.raises(SystemExit) as excinfo:
        read_json(str(tmp_path / "absent.json"))
    assert excinfo.value.code == EXIT_IO
    assert "cannot read" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        pytest.param("bad.json", "{invalide", "invalid JSON", id="invalid-json"),
        pytest.param("huge.json", '{"x": ' + "9" * 5000 + "}", "cannot read", id="huge-integer"),
    ],
)
def test_read_json_reports_invalid_files(tmp_path, capsys, name, content, message):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        read_json(str(path))
    assert excinfo.value.code == EXIT_IO
    assert message in capsys.readouterr().err


def test_read_json_handles_recursion_errors(tmp_path, monkeypatch, capsys):
    path = tmp_path / "deep.json"
    path.write_text("{}", encoding="utf-8")

    def fail(*args: object, **kwargs: object) -> object:
        raise RecursionError("too deeply nested")

    monkeypatch.setattr("assembler.cli.utils.load", fail)
    with pytest.raises(SystemExit) as excinfo:
        read_json(str(path))
    assert excinfo.value.code == EXIT_IO
    assert "invalid JSON" in capsys.readouterr().err


def test_write_file(tmp_path):
    write_file(str(tmp_path / "out"), "data", "prog.tst", ".mc", io.StringIO())
    assert (tmp_path / "out").read_text(encoding="utf-8") == "data\n"
    assert not (tmp_path / "out.mc").exists()

    directory = tmp_path / "dir"
    directory.mkdir()
    write_file(str(directory), "data", "prog.tst", ".lst", io.StringIO())
    assert (directory / "prog.lst").read_text(encoding="utf-8") == "data\n"

    write_file(str(tmp_path / "a" / "b" / "out"), "data", "prog.tst", ".mc", io.StringIO())
    assert (tmp_path / "a" / "b" / "out").read_text(encoding="utf-8") == "data\n"

    stream = io.StringIO()
    write_file("-", "data", "prog.tst", ".mc", stream)
    assert stream.getvalue() == "data\n"


def test_report(tmp_path, capsys):
    assert report([], [], make_args(), "prog.tst") == EXIT_OK
    assert capsys.readouterr().err == ""

    assert report(["E1"], [], make_args(), "prog.tst") == EXIT_ERRORS
    assert "E1" in capsys.readouterr().err

    assert report([], ["W1"], make_args(), "prog.tst") == EXIT_OK
    assert "W1" in capsys.readouterr().err

    assert report([], ["W1"], make_args(quiet=True), "prog.tst") == EXIT_OK
    assert capsys.readouterr().err == ""

    assert report([], ["W1"], make_args(strict=True), "prog.tst") == EXIT_ERRORS
    assert "W1" in capsys.readouterr().err

    assert report([], ["W1"], make_args(quiet=True, strict=True), "prog.tst") == EXIT_ERRORS
    assert capsys.readouterr().err == ""

    report(["E1"], ["W1"], make_args(diagnostics="json"), "prog.tst")
    assert json.loads(capsys.readouterr().err) == {"errors": ["E1"], "warnings": ["W1"]}

    diagnostics_file = tmp_path / "diag"
    args = make_args(diagnostics_output=str(diagnostics_file))
    assert report(["E1"], [], args, "prog.tst") == EXIT_ERRORS
    assert capsys.readouterr().err == ""
    assert diagnostics_file.read_text(encoding="utf-8") == "E1\n"


def test_assembler_command_outputs(project, tmp_path, monkeypatch, capsys):
    source_file, architecture_file = project

    assert run_command(source_file, architecture_file) == EXIT_OK
    assert capsys.readouterr().out == "00011000\n11000000\n"

    assert run_command(source_file, architecture_file, format="hex") == EXIT_OK
    assert capsys.readouterr().out == "18\nc0\n"

    assert run_command(source_file, architecture_file, no_pad=True) == EXIT_OK
    assert capsys.readouterr().out == "11000\n11000000\n"

    output = tmp_path / "out"
    assert run_command(source_file, architecture_file, output=str(output)) == EXIT_OK
    assert capsys.readouterr().out == ""
    assert output.read_text(encoding="utf-8") == "00011000\n11000000\n"

    listing = tmp_path / "prog"
    assert run_command(source_file, architecture_file, listing=str(listing)) == EXIT_OK
    assert listing.read_text(encoding="utf-8") == (
        "ADDRESS  WORD      SOURCE\n0000000  00011000  ADD R1 R2 ZERO\n0000001  11000000  HLT\n"
    )
    capsys.readouterr()

    checked = tmp_path / "checked"
    assert run_command(source_file, architecture_file, check=True, output=str(checked)) == EXIT_OK
    assert not checked.exists()

    monkeypatch.setattr(sys, "stdin", io.StringIO("HLT\n"))
    assert run_command("-", architecture_file) == EXIT_OK
    assert capsys.readouterr().out == "11000000\n"


def test_assembler_command_warnings_and_empty_programs(project, tmp_path, monkeypatch, capsys):
    _, architecture_file = project
    monkeypatch.setattr(sys, "stdin", io.StringIO("HLT\n"))
    assert run_command("-", architecture_file, strict=True) == EXIT_OK
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("11000000\n", "")

    empty = tmp_path / "empty.tst"
    empty.write_text("", encoding="utf-8")
    output, listing = tmp_path / "out.mc", tmp_path / "out.lst"
    assert (
        run_command(empty, architecture_file, output=str(output), listing=str(listing)) == EXIT_OK
    )
    assert not output.exists() and not listing.exists()

    output_dir = tmp_path / "out"
    output_dir.mkdir()
    monkeypatch.setattr(sys, "stdin", io.StringIO("HLT\n"))
    assert run_command("-", architecture_file, output=str(output_dir) + "/") == EXIT_OK
    assert (output_dir / "-.mc").read_text(encoding="utf-8") == "11000000\n"


def test_assembler_command_helpers():
    command = AssemblerCommand(make_args(source="prog.tst"))
    assert command.get_extension_warning({"file_extension": ".tst"}) is None
    assert command.get_extension_warning({"file_extension": ".txt"}) is not None
    assert AssemblerCommand(make_args(source="-")).get_extension_warning({}) is None
    assert command.get_instruction_length({"instruction_length": 18}) == 18
    assert command.get_instruction_length({"instruction_length": "18"}) == 0


def test_architecture_command(tmp_path, capsys):
    valid = tmp_path / "arch.json"
    valid.write_text(json.dumps(make_architecture()), encoding="utf-8")
    assert ArchitectureCommand(make_args(arch=str(valid))).execute() == EXIT_OK
    assert capsys.readouterr().out == f"{valid}: ok\n"

    show_args = make_args(arch=str(valid), architecture_command="show")
    assert ArchitectureCommand(show_args).execute() == EXIT_OK
    assert json.loads(capsys.readouterr().out) == {
        "architecture_name": "Test Core",
        "file_extension": ".tst",
        "instruction_length": 8,
        "instructions": 3,
        "pseudo_instructions": 0,
    }

    pseudo = tmp_path / "pseudo.json"
    pseudo.write_text(json.dumps(make_pseudo_architecture()), encoding="utf-8")
    pseudo_args = make_args(arch=str(pseudo), architecture_command="show")
    assert ArchitectureCommand(pseudo_args).execute() == EXIT_OK
    assert json.loads(capsys.readouterr().out)["pseudo_instructions"] == 3

    invalid_data = make_architecture()
    del invalid_data["architecture_name"]
    del invalid_data["file_extension"]
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps(invalid_data), encoding="utf-8")
    diagnostics = tmp_path / "diag"
    args = make_args(arch=str(invalid), diagnostics_output=str(diagnostics))
    assert ArchitectureCommand(args).execute() == EXIT_ERRORS
    assert capsys.readouterr().err == ""
    contents = diagnostics.read_text(encoding="utf-8")
    assert "architecture_name field is required" in contents
    assert "file_extension field is required" in contents

    non_object = tmp_path / "array.json"
    non_object.write_text("[1]", encoding="utf-8")
    assert ArchitectureCommand(make_args(arch=str(non_object))).execute() == EXIT_ERRORS
    assert "must be an object" in capsys.readouterr().err

    with pytest.raises(SystemExit) as excinfo:
        ArchitectureCommand(make_args(arch=str(tmp_path / "absent.json"))).execute()
    assert excinfo.value.code == EXIT_IO

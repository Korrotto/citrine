"""End-to-end tests: public API, CLI, and the committed Garnet examples."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest
from assembler.pipeline import assemble_program

from tests.utils import assemble, make_architecture, make_pseudo_architecture

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
GARNET_FILE = ROOT / "architecture" / "garnetCoreV3.json"
GARNET_V2_FILE = ROOT / "architecture" / "garnetCoreV2.json"
GARNET: dict[str, object] = json.loads(GARNET_FILE.read_text(encoding="utf-8"))


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "assembler", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_examples_match_committed_artifacts():
    source = (EXAMPLES / "test_program.grt3").read_text(encoding="utf-8")
    expected_code = (EXAMPLES / "test_program.mc").read_text(encoding="utf-8").splitlines()
    result = assemble_program(source, GARNET)

    assert result.errors == []
    assert result.warnings == []
    assert result.machine_code == [int(line, 2) for line in expected_code]
    assert len(result.machine_code) == 14

    source = (EXAMPLES / "errors_program.grt3").read_text(encoding="utf-8")
    expected_log = (EXAMPLES / "errors_program.log").read_text(encoding="utf-8").splitlines()
    result = assemble_program(source, GARNET)

    assert result.machine_code == []
    assert result.errors + result.warnings == expected_log
    assert (len(result.errors), len(result.warnings)) == (18, 4)


def test_garnet_v2_and_pseudo_pipeline():
    architecture = json.loads(GARNET_V2_FILE.read_text(encoding="utf-8"))
    result = assemble_program("LDI R1 5\nADD R1 R2 R3\nJMP 0\nHLT\n", architecture)
    assert result.errors == []
    assert result.machine_code == [
        0b0110_0001_0000_0101,
        0b0000_0001_0010_0011,
        0b1000_0000_0000_0000,
        0b1111_0000_0000_0000,
    ]

    labels = assemble("JMP .end\nHLT\n.end:")
    assert labels.errors == []
    assert labels.machine_code == [0b01000010, 0b11000000]

    pseudo = assemble("INC R2\nNEG R1\nHLT", make_pseudo_architecture())
    assert pseudo.errors == []
    assert pseudo.machine_code == [0b00101001, 0b00001100, 0b11000000]


def test_pipeline_diagnostics():
    data = make_architecture()
    del data["architecture_name"]
    result = assemble("HLT", data)
    assert result.machine_code == []
    assert result.errors == ["ERROR | The architecture_name field is required"]
    assert result.instruction_lines == []

    bad = assemble("FOO R1")
    assert bad.machine_code == []
    assert bad.errors == ["ERROR | line 1 | Unsupported instruction 'foo' | FOO R1"]
    assert len(bad.instruction_lines) == 1

    warned = assemble("DEFINE X AS 1\nHLT")
    assert warned.machine_code == [0b11000000]
    assert warned.warnings == ["WARNING | Alias 'x' is defined but never used"]


@pytest.mark.parametrize(
    ("source", "architecture", "message"),
    [
        pytest.param(
            cast(str, 123),
            {},
            "source_code argument must be a str, got int",
            id="source-code",
        ),
        pytest.param(
            "HLT",
            cast(dict, []),
            "architecture_data argument must be a dict, got list",
            id="architecture-data",
        ),
    ],
)
def test_api_rejects_wrong_input_types(source, architecture, message):
    with pytest.raises(TypeError, match=message):
        assemble_program(source, architecture)


def test_cli_end_to_end_writes_code_and_listing(tmp_path):
    code = tmp_path / "prog.mc"
    listing = tmp_path / "prog.lst"
    process = run_cli(
        "assemble",
        str(EXAMPLES / "test_program.grt3"),
        "-a",
        str(GARNET_FILE),
        "-o",
        str(code),
        "-l",
        str(listing),
    )

    assert process.returncode == 0
    assert process.stdout == ""
    assert code.read_text(encoding="utf-8") == (EXAMPLES / "test_program.mc").read_text(
        encoding="utf-8"
    )
    assert listing.read_text(encoding="utf-8") == (EXAMPLES / "test_program.lst").read_text(
        encoding="utf-8"
    )


def test_cli_arch_commands_versions_and_errors():
    validate = run_cli("arch", "validate", str(GARNET_FILE))
    assert validate.returncode == 0
    assert validate.stdout == f"{GARNET_FILE}: ok\n"

    show = run_cli("architecture", "show", str(GARNET_FILE))
    assert show.returncode == 0
    assert json.loads(show.stdout) == {
        "architecture_name": "Garnet Core V3",
        "file_extension": ".grt3",
        "instruction_length": 18,
        "instructions": 16,
        "pseudo_instructions": 29,
    }

    faulty = run_cli(
        "assemble", str(EXAMPLES / "errors_program.grt3"), "-a", str(GARNET_FILE), "-c"
    )
    assert faulty.returncode == 1
    assert faulty.stdout == ""
    assert "ERROR" in faulty.stderr

    assert run_cli("frobnicate").returncode == 2
    version = run_cli("--version")
    assert version.returncode == 0
    assert version.stdout.startswith("citrine ")

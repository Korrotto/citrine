import pytest
from assembler.architecture.models import FixedBits, VariableBits
from assembler.common.models import LiteralSlot, PlaceholderSlot
from assembler.common.translationparser import InvalidTranslationError
from assembler.common.utils import log_error

from tests.utils import (
    build_architecture,
    make_architecture,
    make_pseudo_architecture,
    validate_architecture,
)

INVALID_GLOBALS = [
    pytest.param(
        {"architecture_name": "   "},
        [log_error("ARCH-004", "architecture_name", "name")],
        id="blank-name",
    ),
    pytest.param(
        {"instruction_length": 0},
        [
            log_error("ARCH-004", "instruction_length", "integer"),
            log_error("ARCH-015", "ADD"),
            log_error("ARCH-015", "JMP"),
            log_error("ARCH-015", "HLT"),
        ],
        id="zero-length",
    ),
    pytest.param(
        {"instruction_length": True},
        [log_error("ARCH-004", "instruction_length", "integer")],
        id="boolean-length",
    ),
    pytest.param(
        {"file_extension": "grt3"},
        [log_error("ARCH-004", "file_extension", "file extension")],
        id="bad-extension",
    ),
]

INVALID_INSTRUCTION_SETS = [
    pytest.param(
        {"instruction_set": {"1ADD": ["00", "x6"]}},
        [log_error("ARCH-006", "instruction_set", "1ADD")],
        id="invalid-name",
    ),
    pytest.param(
        {"instruction_set": {"ADD": ["00", "x2 x2 x2"], "add": ["01", "x6"]}},
        [log_error("ARCH-007", "instruction_set", "add")],
        id="duplicate-name",
    ),
    pytest.param(
        {"instruction_set": {"ADD": ["2", "x6"]}},
        [log_error("ARCH-010", "ADD")],
        id="bad-opcode",
    ),
    pytest.param(
        {"instruction_set": {"ADD": ["00", "x6"], "SUB": ["00", "x6"]}},
        [log_error("ARCH-011", "SUB", "00")],
        id="duplicate-opcode",
    ),
    pytest.param(
        {"instruction_set": {"ADD": ["00", "x6"], "HLT": ["111", "00000"]}},
        [log_error("ARCH-012")],
        id="inconsistent-opcode-width",
    ),
    pytest.param(
        {"instruction_set": {"ADD": "00 x6"}},
        [log_error("ARCH-009", "ADD")],
        id="format-not-list",
    ),
    pytest.param(
        {"instruction_set": {"ADD": [0, "x6"]}},
        [log_error("ARCH-010", "ADD")],
        id="opcode-not-string",
    ),
    pytest.param(
        {"instruction_set": {"ADD": ["00", "   "]}},
        [log_error("ARCH-013", "ADD")],
        id="empty-format",
    ),
    pytest.param(
        {"instruction_set": {"ADD": ["00", "x0"]}},
        [log_error("ARCH-014", "ADD")],
        id="zero-width",
    ),
    pytest.param(
        {"instruction_set": {"ADD": ["00", "x129"]}},
        [log_error("ARCH-014", "ADD")],
        id="too-wide",
    ),
    pytest.param(
        {"instruction_set": {"ADD": ["00", "x2 abc"]}},
        [log_error("ARCH-014", "ADD")],
        id="invalid-token",
    ),
    pytest.param(
        {"instruction_set": {"ADD": ["00", "x2 x2"]}},
        [log_error("ARCH-015", "ADD")],
        id="wrong-total-width",
    ),
]

INVALID_PSEUDO_SETS = [
    pytest.param(
        {"pseudo_instruction_set": {"HLT": "ADD {0} {0} 0"}},
        [log_error("ARCH-017", "HLT")],
        id="shadows-instruction",
    ),
    pytest.param(
        {"pseudo_instruction_set": {"P": "ADD {0} {0} 0", "p": "ADD {0} 0 {0}"}},
        [log_error("ARCH-007", "pseudo_instruction_set", "p")],
        id="duplicate-name",
    ),
    pytest.param(
        {"pseudo_instruction_set": {"1P": "ADD {0} {0} 0"}},
        [log_error("ARCH-006", "pseudo_instruction_set", "1P")],
        id="invalid-name",
    ),
    pytest.param(
        {"pseudo_instruction_set": {"P": "NOPE {0}"}},
        [log_error("ARCH-019", "P")],
        id="unknown-target",
    ),
    pytest.param(
        {"pseudo_instruction_set": {"P": "ADD {0}"}},
        [log_error("ARCH-021", "P", "add")],
        id="operand-count",
    ),
    pytest.param(
        {"pseudo_instruction_set": {"P": "ADD 7 {0} 0"}},
        [log_error("TRN-004", 7, 2)],
        id="constant-too-wide",
    ),
    pytest.param(
        {"pseudo_instruction_set": {"P": "ADD 0 -{0} @{0}"}},
        [],
        id="valid-placeholders",
    ),
    pytest.param(
        {"pseudo_instruction_set": {"P": "ADD {1} {1} 0"}},
        [log_error("ARCH-024", "P")],
        id="non-contiguous",
    ),
    pytest.param(
        {"pseudo_instruction_set": {"P": "ADD {x} 0 0"}},
        [log_error("ARCH-022", "P")],
        id="invalid-placeholder",
    ),
    pytest.param(
        {"pseudo_instruction_set": {"P": "ADD {128} 0 0"}},
        [log_error("ARCH-022", "P")],
        id="placeholder-too-large",
    ),
]


def test_valid_architecture(architecture):
    assert validate_architecture(architecture) == []


def test_missing_required_fields_are_all_reported():
    missing = make_architecture()
    for field in ("architecture_name", "instruction_length", "file_extension"):
        del missing[field]

    assert validate_architecture(missing) == [
        log_error("ARCH-002", "architecture_name"),
        log_error("ARCH-002", "instruction_length"),
        log_error("ARCH-002", "file_extension"),
    ]


def test_unknown_fields_are_rejected():
    assert validate_architecture({"unknown": 1, "instruction_set": {}}) == [
        log_error("ARCH-001", "unknown"),
        log_error("ARCH-002", "architecture_name"),
        log_error("ARCH-002", "instruction_length"),
        log_error("ARCH-002", "file_extension"),
        log_error("ARCH-005", "instruction_set", "instruction"),
    ]


@pytest.mark.parametrize(("overrides", "expected"), INVALID_GLOBALS)
def test_invalid_global_values_are_reported(overrides, expected):
    assert validate_architecture(make_architecture(**overrides)) == expected


@pytest.mark.parametrize(("overrides", "expected"), INVALID_INSTRUCTION_SETS)
def test_instruction_set_validation(overrides, expected):
    assert validate_architecture(make_architecture(**overrides)) == expected


def test_valid_alias_names():
    architecture = make_architecture(
        aliases={"==": 0, "'A'": 65, "R0": 0, ">=": 1, "_free": 2, "1UP": 3}
    )
    assert validate_architecture(architecture) == []


@pytest.mark.parametrize("name", ["", ".label", "used", "a,b", "1" * 513, 42], ids=repr)
def test_invalid_alias_names(name):
    assert validate_architecture(make_architecture(aliases={name: 1})) == [
        log_error("ARCH-006", "aliases", name)
    ]


def test_duplicate_alias_names_are_rejected():
    architecture = make_architecture(aliases={"r1": 1, "R1": 2})
    assert validate_architecture(architecture) == [log_error("ARCH-007", "aliases", "R1")]


@pytest.mark.parametrize("value", ["1", 1.0, True, None], ids=repr)
def test_alias_values_must_be_integers(value):
    architecture = make_architecture(aliases={"X": value})
    assert validate_architecture(architecture) == [log_error("ARCH-008", "X")]


@pytest.mark.parametrize(("overrides", "expected"), INVALID_PSEUDO_SETS)
def test_pseudo_set_validation(overrides, expected):
    assert validate_architecture(make_architecture(**overrides)) == expected


def test_constructor_builds_and_normalizes_architecture(pseudo_architecture):
    long_field = "x" + "0" * 5000 + "2"
    long_architecture = make_architecture(instruction_set={"HLT": ["11", long_field + " 0000"]})
    assert validate_architecture(long_architecture) == []
    assert build_architecture(long_architecture).instruction_set["hlt"] == (
        FixedBits(0b11, 2),
        VariableBits(2),
        FixedBits(0, 4),
    )

    data = build_architecture(pseudo_architecture)
    assert data.architecture_name == "Test Core"
    assert (data.instruction_length, data.file_extension) == (8, ".tst")
    assert set(data.instruction_set) == {"add", "jmp", "hlt"}
    assert data.aliases == {"r1": 1, "r2": 2, "zero": 0}
    assert data.instruction_set["hlt"] == (FixedBits(0b11, 2), FixedBits(0, 6))
    assert data.pseudo_set == {
        "neg": ("add", (LiteralSlot(0), PlaceholderSlot("-", 0), LiteralSlot(0))),
        "rev": ("add", (LiteralSlot(0), PlaceholderSlot("@", 0), LiteralSlot(0))),
        "inc": ("add", (PlaceholderSlot("", 0), PlaceholderSlot("", 0), LiteralSlot(1))),
    }

    without_aliases = make_architecture()
    del without_aliases["aliases"]
    assert build_architecture(without_aliases).aliases is None
    assert build_architecture(make_architecture()).pseudo_set is None

    masked = make_pseudo_architecture(pseudo_instruction_set={"P": "ADD 7 {0} 0"})
    assert build_architecture(masked).pseudo_set == {
        "p": ("add", (LiteralSlot(0b11), PlaceholderSlot("", 0), LiteralSlot(0)))
    }
    invalid = make_pseudo_architecture(pseudo_instruction_set={"P": "ADD 0 abc 0"})
    with pytest.raises(InvalidTranslationError, match="Invalid translation operand 'abc'"):
        build_architecture(invalid)

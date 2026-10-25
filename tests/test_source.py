import pytest
from assembler.architecture.models import FixedBits, VariableBits
from assembler.common.models import LiteralSlot, PlaceholderSlot
from assembler.common.utils import log_error, log_warning
from assembler.source.codegenerator import CodeGenerator
from assembler.source.instructionvalidator import InstructionValidator
from assembler.source.models import ExpandedLine, ResolvedLine, TokenizedLine
from assembler.source.operandresolver import OperandResolver
from assembler.source.preprocessor import Preprocessor
from assembler.source.pseudoexpander import PseudoExpander
from assembler.source.tokenizer import Tokenizer

from tests.utils import (
    build_context,
    make_architecture,
    make_pseudo_architecture,
    to_instruction_lines,
    to_resolved_lines,
)

DEFINE_ERRORS = [
    pytest.param(
        "DEFINE X 5",
        log_error("SRC-002", "DEFINE", position=(1, "DEFINE X 5")),
        id="syntax",
    ),
    pytest.param(
        "DEFINE 1X AS 5",
        log_error("SRC-003", "alias", "1x", position=(1, "DEFINE 1X AS 5")),
        id="invalid-name",
    ),
    pytest.param(
        "DEFINE TO AS 1",
        log_error("SRC-003", "alias", "to", position=(1, "DEFINE TO AS 1")),
        id="reserved-name",
    ),
    pytest.param(
        "DEFINE X AS 1\nDEFINE X AS 2",
        log_error("SRC-004", "Alias", "x", position=(2, "DEFINE X AS 2")),
        id="duplicate",
    ),
    pytest.param(
        "DEFINE BAD AS 1+2",
        log_error("SRC-005", "1+2", position=(1, "DEFINE BAD AS 1+2")),
        id="bad-value",
    ),
    pytest.param(
        "DEFINE X AS PHANTOM",
        log_error("SRC-001", "alias", "phantom"),
        id="undefined-alias",
    ),
]

USED_ERRORS = [
    pytest.param("USED", log_error("SRC-002", "USED", position=(1, "USED")), id="syntax"),
    pytest.param(
        "USED x", log_error("SRC-003", "label", "x", position=(1, "USED x")), id="invalid-label"
    ),
    pytest.param("USED .absent", log_error("SRC-001", "label", ".absent"), id="undefined-label"),
]

PSEUDO_ERRORS = [
    pytest.param(
        "PSEUDO NEG ADD 0 {0} 0",
        log_error("SRC-002", "PSEUDO", position=(1, "PSEUDO NEG ADD 0 {0} 0")),
        id="syntax",
    ),
    pytest.param(
        "PSEUDO 1N TO ADD {0} {0} 0",
        log_error(
            "SRC-003",
            "pseudo-instruction",
            "1n",
            position=(1, "PSEUDO 1N TO ADD {0} {0} 0"),
        ),
        id="invalid-name",
    ),
    pytest.param(
        "PSEUDO ADD TO ADD {0} {0} 0",
        log_error(
            "SRC-004",
            "Instruction",
            "add",
            position=(1, "PSEUDO ADD TO ADD {0} {0} 0"),
        ),
        id="instruction-name",
    ),
    pytest.param(
        "PSEUDO X TO NOPE {0}",
        log_error("SRC-006", "nope", position=(1, "PSEUDO X TO NOPE {0}")),
        id="unknown-target",
    ),
]

TRANSLATION_ERRORS = [
    pytest.param(
        "PSEUDO X TO ADD {0}",
        log_error("TRN-003", "x", position=(1, "PSEUDO X TO ADD {0}")),
        id="format",
    ),
    pytest.param(
        "PSEUDO X TO ADD 0 abc 0",
        log_error("TRN-002", "abc", position=(1, "PSEUDO X TO ADD 0 abc 0")),
        id="operand",
    ),
    pytest.param(
        "PSEUDO X TO ADD {1} {1} {1}",
        log_error("TRN-001", 1, "x", position=(1, "PSEUDO X TO ADD {1} {1} {1}")),
        id="indices",
    ),
    pytest.param(
        "PSEUDO X TO ADD {128} {0} {0}",
        log_error("TRN-001", 128, "x", position=(1, "PSEUDO X TO ADD {128} {0} {0}")),
        id="index",
    ),
]

LABEL_ERRORS = [
    pytest.param(".l: .m:", log_error("SRC-007", position=(1, ".l: .m:")), id="not-alone"),
    pytest.param(
        ".bad-name:",
        log_error("SRC-003", "label", ".bad-name", position=(1, ".bad-name:")),
        id="invalid-name",
    ),
    pytest.param(
        ".l:\n.l:", log_error("SRC-004", "Label", ".l", position=(2, ".l:")), id="duplicate"
    ),
]

ALIAS_ERRORS = [
    pytest.param(
        {"a": "a"},
        log_error("SRC-009", "a", position=(1, "JMP A")),
        id="self-reference",
    ),
    pytest.param(
        {"a": "b", "b": "a"},
        log_error("SRC-009", "a", position=(1, "JMP A")),
        id="cycle",
    ),
    pytest.param(
        {"a": "absent"},
        log_error("SRC-001", "alias", "absent", position=(1, "JMP A")),
        id="missing-target",
    ),
]


def preprocess(source: str, context) -> list[TokenizedLine]:
    return Preprocessor(context).process_lines(Tokenizer.tokenize_source_code(source))


def test_tokenizer_normalizes_and_classifies_lines():
    source = "\ufeffADD R1, R2, ZERO // sum\r\n\n// comment\n\tHLT\n"
    lines = Tokenizer.tokenize_source_code(source)

    assert [(line.line_number, line.tokens, line.text) for line in lines] == [
        (1, ("add", "r1", "r2", "zero"), "ADD R1, R2, ZERO"),
        (4, ("hlt",), "HLT"),
    ]
    assert Tokenizer.tokenize_source_code("") == []
    assert Tokenizer.tokenize_source_code(",, ,") == []

    lines = Tokenizer.tokenize_source_code(
        "DEFINE X AS 5\nUSED .x\nPSEUDO P TO ADD {0} {0} 0\n.loop:\n.loop: HLT\nHLT"
    )
    assert [line.line_type for line in lines] == [
        "define",
        "used",
        "pseudo",
        "label",
        "instruction",
        "instruction",
    ]
    assert lines[3].tokens == (".loop",)
    assert lines[4].tokens == (".loop:", "hlt")


def test_define_directives(context):
    preprocess(
        "DEFINE FIVE AS 5\nDEFINE A AS B\nDEFINE B AS 3\nDEFINE TARGET AS .end\n.end:",
        context,
    )
    assert context.aliases == {
        "r1": 1,
        "r2": 2,
        "zero": 0,
        "five": 5,
        "a": "b",
        "b": 3,
        "target": ".end",
        ".end": 0,
    }
    assert context.errors == []


@pytest.mark.parametrize(("source", "expected"), DEFINE_ERRORS)
def test_define_directive_errors(source, expected, context):
    preprocess(source, context)
    assert context.errors == [expected]


def test_used_directive(context):
    preprocess("USED .main\n.main:", context)
    assert context.errors == []
    assert context.used_aliases == {".main"}


@pytest.mark.parametrize(("source", "expected"), USED_ERRORS)
def test_used_directive_errors(source, expected, context):
    preprocess(source, context)
    assert context.errors == [expected]


def test_pseudo_directive(context):
    preprocess("PSEUDO NEG TO ADD 0 -{0} 0", context)
    assert context.errors == []
    assert context.pseudo_set["neg"] == (
        "add",
        (LiteralSlot(0), PlaceholderSlot("-", 0), LiteralSlot(0)),
    )


@pytest.mark.parametrize(("source", "expected"), PSEUDO_ERRORS)
def test_pseudo_directive_errors(source, expected, context):
    preprocess(source, context)
    assert context.errors == [expected]


@pytest.mark.parametrize(
    ("source", "data", "expected"),
    [
        pytest.param(
            "PSEUDO X TO ADD {0} {0} 0\nPSEUDO X TO ADD 0 {0} 0",
            None,
            log_error(
                "SRC-004", "Pseudo-instruction", "x", position=(2, "PSEUDO X TO ADD 0 {0} 0")
            ),
            id="local-duplicate",
        ),
        pytest.param(
            "PSEUDO NEG TO ADD 0 {0} 0",
            make_pseudo_architecture(),
            log_error(
                "SRC-004",
                "Pseudo-instruction",
                "neg",
                position=(1, "PSEUDO NEG TO ADD 0 {0} 0"),
            ),
            id="architecture-duplicate",
        ),
    ],
)
def test_pseudo_directive_rejects_duplicates(source, data, expected):
    context = build_context(data) if data is not None else build_context()
    preprocess(source, context)
    assert context.errors == [expected]


@pytest.mark.parametrize(("source", "expected"), TRANSLATION_ERRORS)
def test_pseudo_translation_errors(source, expected, context):
    preprocess(source, context)
    assert context.errors == [expected]


def test_pseudo_constant_truncation(context):
    preprocess("PSEUDO X TO ADD 7 {0} 0", context)
    assert context.errors == []
    assert context.warnings == [
        log_warning("TRN-004", 7, 2, position=(1, "PSEUDO X TO ADD 7 {0} 0"))
    ]
    assert context.pseudo_set["x"][1][0] == LiteralSlot(0b11)


def test_labels_track_instruction_addresses(context):
    preprocess("HLT\n.l1:\nDEFINE X AS 1\nUSED .l1\n.l2:\nHLT", context)
    assert context.aliases[".l1"] == 1
    assert context.aliases[".l2"] == 1
    assert context.errors == []


@pytest.mark.parametrize(("source", "expected"), LABEL_ERRORS)
def test_label_errors(source, expected, context):
    preprocess(source, context)
    assert context.errors == [expected]


def test_unused_name_warnings(context, pseudo_context):
    to_instruction_lines("DEFINE X AS 1\nPSEUDO LOCAL TO ADD {0} {0} 0\n.end:\nHLT", context)
    assert context.warnings == [
        log_warning("SRC-010", "Label", ".end"),
        log_warning("SRC-010", "Alias", "x"),
        log_warning("SRC-010", "Pseudo-instruction", "local"),
    ]

    to_instruction_lines("HLT", pseudo_context)
    assert pseudo_context.warnings == []


def test_alias_chains_mark_all_operands_used(context):
    to_instruction_lines("DEFINE A AS B\nDEFINE B AS 3\nADD A R2 ZERO\nHLT", context)
    assert context.get_used_aliases() == ["a", "b", "r2", "zero"]
    assert context.warnings == []


def test_operand_resolver(context):
    resolved = to_resolved_lines("JMP .end\nHLT\n.end:", context)
    assert resolved[0].operand_values == (2,)
    assert resolved[0].tokenized_line.text == "JMP .end"

    resolver = OperandResolver(context)
    line = resolved[0].tokenized_line
    literals = {"5": 5, "+5": 5, "-5": -5, "0b101": 5, "0o17": 15, "0d42": 42, "0x2A": 42}
    for literal, expected in literals.items():
        assert resolver.resolve_single_operand(literal, line) == expected
    assert resolver.resolved_values["5"] == 5

    assert resolver.resolve_single_operand("r1", line) == 1
    context.aliases["r1"] = 99
    assert resolver.resolve_single_operand("r1", line) == 1

    context.aliases["a"] = "b"
    context.aliases["b"] = 7
    assert to_resolved_lines("JMP A", context)[0].operand_values == (7,)


def test_operand_resolver_reports_unknown_aliases(context):
    resolved = to_resolved_lines("ADD R1 UNKNOWN ZERO", context)
    assert resolved[0].operand_values == (1, None, 0)
    assert context.errors == [
        log_error("SRC-001", "alias", "unknown", position=(1, "ADD R1 UNKNOWN ZERO"))
    ]


@pytest.mark.parametrize(("aliases", "expected"), ALIAS_ERRORS)
def test_operand_resolver_reports_broken_alias_chains(aliases, expected, context):
    context.aliases |= aliases
    resolver = OperandResolver(context)
    line = Tokenizer.tokenize_source_code("JMP A")[0]
    assert resolver.resolve_single_operand("a", line) is None
    assert context.errors == [expected]


def test_operand_resolver_reports_missing_labels(context):
    resolved = to_resolved_lines("JMP .missing\nHLT", context)
    assert resolved[0].operand_values == (None,)
    assert context.errors == [
        log_error("SRC-001", "label", ".missing", position=(1, "JMP .missing"))
    ]


def test_instruction_validator_reports_invalid_lines(context):
    InstructionValidator(context).validate_instructions(
        to_resolved_lines("FOO R1\nADD R1 R2\nHLT R1", context)
    )
    assert context.errors == [
        log_error("SRC-006", "foo", position=(1, "FOO R1")),
        log_error("SRC-008", "add", position=(2, "ADD R1 R2")),
        log_error("SRC-008", "hlt", position=(3, "HLT R1")),
    ]

    label_context = build_context()
    line = TokenizedLine(1, ".end: HLT", (".end:", "hlt"), "instruction")
    InstructionValidator(label_context).validate_instructions(
        [ResolvedLine(line, ".end:", (None,))]
    )
    assert label_context.errors == [log_error("SRC-007", position=(1, ".end: HLT"))]


def test_instruction_validator_warns_on_truncation(context):
    InstructionValidator(context).validate_instructions(
        to_resolved_lines("ADD R1 R2 8\nADD R1 R2 -3\nADD R1 UNKNOWN R2", context)
    )
    assert context.warnings == [
        log_warning("SRC-011", 8, 2, 0, position=(1, "ADD R1 R2 8")),
        log_warning("SRC-011", -3, 2, 1, position=(2, "ADD R1 R2 -3")),
    ]
    assert context.errors == [
        log_error("SRC-001", "alias", "unknown", position=(3, "ADD R1 UNKNOWN R2"))
    ]


def test_instruction_validator_warns_on_pseudo_truncation():
    mix_architecture = make_architecture(
        instruction_set={"MIX": ["10", "x2 x4"], "HLT": ["11", "000000"]},
        pseudo_instruction_set={"P": "MIX {0} {0}"},
    )
    context = build_context(mix_architecture)
    InstructionValidator(context).validate_instructions(to_resolved_lines("P 20", context))
    assert context.warnings == [
        log_warning("SRC-011", 20, 2, 0, position=(1, "P 20")),
        log_warning("SRC-011", 20, 4, 4, position=(1, "P 20")),
    ]


def test_pseudo_expander(pseudo_context):
    expander = PseudoExpander(pseudo_context)
    lines = to_resolved_lines("INC R1\nHLT\nNEG R2\nREV R1", pseudo_context)
    assert list(expander.expand_pseudo_instructions(lines)) == [
        ExpandedLine("add", (1, 1, 1)),
        ExpandedLine("hlt", ()),
        ExpandedLine("add", (0, 0b10, 0)),
        ExpandedLine("add", (0, 0b10, 0)),
    ]
    assert expander.transform_slot(PlaceholderSlot("~", 0), 4, (0b0101,)) == 0b1010
    assert expander.transform_slot(PlaceholderSlot("", 0), 2, (7,)) == 0b11


def test_code_generator_and_context_tracking(context):
    generator = CodeGenerator(context)
    assert generator.generate_instruction(context.instruction_set["add"], (1, 2, 0)) == 0b00011000
    assert generator.generate_instruction(context.instruction_set["jmp"], (5,)) == 0b01000101
    assert generator.generate_instruction(context.instruction_set["hlt"], ()) == 0b11000000
    assert generator.generate_instruction(context.instruction_set["add"], (1, 2, 300)) == 0b00011000

    fields = (FixedBits(0b10, 2), VariableBits(3), FixedBits(0b1, 1))
    assert generator.generate_instruction(fields, (0b101,)) == 0b101011
    assert generator.generate_machine_code(iter([ExpandedLine("hlt", ())])) == [0b11000000]

    context.aliases["never"] = 1
    context.used_aliases.update({"r2", "r1"})
    context.pseudo_set["zz"] = ("add", ())
    context.pseudo_set["aa"] = ("add", ())
    context.used_pseudo_instructions.add("zz")
    assert context.get_used_aliases() == ["r1", "r2"]
    assert context.get_unused_aliases() == ["never"]
    assert context.get_unused_pseudo_instructions() == ["aa"]
    assert context.get_undefined_aliases() == []

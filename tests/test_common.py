import re
from string import Formatter

import pytest
from assembler.common.message import TEMPLATES, make_message
from assembler.common.models import (
    InvalidIndex,
    InvalidToken,
    LiteralSlot,
    PlaceholderSlot,
    TranslationSpec,
)
from assembler.common.translationparser import (
    InvalidTranslationError,
    TranslationParser,
    has_contiguous_indices,
    parse_placeholder,
    parse_slot_token,
)
from assembler.common.utils import (
    convert_to_integer,
    fits_in_width,
    is_integer_literal,
    is_not_reserved,
    is_valid_instruction,
    is_variable_field,
    log,
    log_error,
    log_warning,
    mask_to_width,
    normalize,
    parse_decimal,
)

CODE_PATTERN = re.compile(r"^(ARCH|TRN|SRC|API)-\d{3}$")

VALID_LITERALS = ["0", "+42", "-42", "0b1010", "0B1010", "0o17", "0d99", "0xff", "9" * 513]
INVALID_LITERALS = ["", "abc", "1+2", "0b", "0x", "0b12", "12.5", "1 2", "++1"]
CONVERSIONS = {
    "5": 5,
    "+5": 5,
    "-5": -5,
    "0b110": 6,
    "-0b110": -6,
    "0o17": 15,
    "-0o17": -15,
    "0d42": 42,
    "-0d42": -42,
    "0x2A": 42,
    "-0x2A": -42,
}


def test_message_templates_are_complete_and_usable():
    assert {code.split("-")[0] for code in TEMPLATES} == {"ARCH", "TRN", "SRC", "API"}
    for code, template in TEMPLATES.items():
        assert CODE_PATTERN.fullmatch(code), code
        fields = [field for _, field, _, _ in Formatter().parse(template) if field is not None]
        count = max(map(int, fields)) + 1 if fields else 0
        assert make_message(code, *(["value"] * count))


def test_make_message_formats_parameters_and_rejects_unknown_codes():
    assert make_message("SRC-001", "alias", "counter") == "Undefined alias 'counter'"
    assert make_message("SRC-011", 300, 8, 44) == "Value truncated to 8 bits: 300 -> 44"
    with pytest.raises(ValueError, match="Unknown message code"):
        make_message("XXX-000")


def test_log_helpers():
    assert log("ERROR", "boom") == "ERROR | boom"
    assert log("ERROR", "boom", position=(3, None)) == "ERROR | line 3 | boom"
    assert log("WARNING", "boom", position=(3, "LDI R1 5")) == (
        "WARNING | line 3 | boom | LDI R1 5"
    )
    assert log_error("SRC-001", "alias", "foo") == "ERROR | Undefined alias 'foo'"
    assert log_warning("SRC-010", "Alias", "x") == "WARNING | Alias 'x' is defined but never used"


def test_integer_literals_and_conversion():
    for literal in VALID_LITERALS:
        assert is_integer_literal(literal), literal
    for literal in INVALID_LITERALS:
        assert not is_integer_literal(literal), literal
    for literal, expected in CONVERSIONS.items():
        assert convert_to_integer(literal) == expected, literal

    assert parse_decimal("0007") == 7
    assert parse_decimal("1.5") is None


def test_name_and_width_helpers():
    assert normalize("AbC") == "abc"
    assert is_variable_field("X128")
    assert not is_variable_field("x")
    assert is_not_reserved("ADD")
    assert not is_not_reserved("define")
    assert is_valid_instruction("jmp")
    assert not is_valid_instruction("used")

    assert mask_to_width(255, 8) == 255
    assert mask_to_width(256, 8) == 0
    assert mask_to_width(-1, 8) == 255
    assert mask_to_width(0b1010, 3) == 0b010
    with pytest.raises(ValueError, match="Invalid bit width: 0"):
        mask_to_width(1, 0)

    assert fits_in_width(-128, 8)
    assert not fits_in_width(-129, 8)
    assert fits_in_width(255, 8)
    assert not fits_in_width(256, 8)
    assert not fits_in_width(-3, 2)
    with pytest.raises(ValueError, match="Invalid bit width: -1"):
        fits_in_width(0, -1)


def test_slot_and_translation_parsing():
    assert parse_placeholder("{0}") == ("", 0)
    assert parse_placeholder("-{12}") == ("-", 12)
    assert parse_placeholder("x{0}") is None

    assert parse_slot_token("0x2A") == LiteralSlot(42)
    assert parse_slot_token("@{127}") == PlaceholderSlot("@", 127)
    assert parse_slot_token("{128}") == InvalidIndex(128)
    assert parse_slot_token("42x") == InvalidToken("42x")
    assert has_contiguous_indices({0, 1, 2})
    assert not has_contiguous_indices({0, 2})

    spec = TranslationSpec(("-2", "7"), (2, 2), "pseudo")
    assert TranslationParser.parse(spec) == (
        (LiteralSlot(0b10), LiteralSlot(0b11)),
        [("TRN-004", (7, 2))],
    )


@pytest.mark.parametrize(
    ("spec", "code"),
    [
        (TranslationSpec(("1",), (2, 3), "pseudo"), "TRN-003"),
        (TranslationSpec(("abc",), (2,), "pseudo"), "TRN-002"),
        (TranslationSpec(("{1}", "{1}"), (2, 2), "pseudo"), "TRN-001"),
        (TranslationSpec(("{128}",), (2,), "pseudo"), "TRN-001"),
    ],
    ids=["format", "operand", "indices", "index"],
)
def test_translation_parser_rejects_invalid_translations(spec, code):
    with pytest.raises(InvalidTranslationError) as excinfo:
        TranslationParser.parse(spec)
    assert excinfo.value.code == code

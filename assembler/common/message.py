TEMPLATES: dict[str, str] = {
    # Architecture file errors
    "ARCH-001": "The field {0!r} is not a valid architecture field",
    "ARCH-002": "The {0} field is required",
    "ARCH-003": "The {0} field must be an object",
    "ARCH-004": "The {0} field must contain a valid {1}",
    "ARCH-005": "The {0} field must contain at least one {1}",
    "ARCH-006": "The {0} field must contain a valid name, got {1!r}",
    "ARCH-007": "The {0} field must not contain a duplicate name, got {1!r}",
    "ARCH-008": "The alias {0!r} must have an integer value",
    "ARCH-009": "The instruction {0!r} must contain a valid format",
    "ARCH-010": "The instruction {0!r} must start with a valid binary opcode",
    "ARCH-011": "The instruction {0!r} must not reuse the opcode {1!r}",
    "ARCH-012": "The instruction set must use opcodes of a consistent width",
    "ARCH-013": "The instruction {0!r} must contain a valid format string",
    "ARCH-014": "The instruction {0!r} must contain valid operands",
    "ARCH-015": "The instruction {0!r} must match the architecture instruction length",
    "ARCH-016": "The pseudo instruction set requires a valid instruction set",
    "ARCH-017": "The pseudo instruction set must not reuse the instruction name {0!r}",
    "ARCH-018": "The translation for {0!r} must be a non-empty string",
    "ARCH-019": "The translation for {0!r} must use a name in the instruction set",
    "ARCH-020": "The translation for {0!r} must reference a valid instruction format",
    "ARCH-021": "The translation for {0!r} must match the number of operands in {1!r}",
    "ARCH-022": "The translation for {0!r} must contain valid constants and placeholders",
    "ARCH-023": "The translation for {0!r} must reference valid operands in {1!r}",
    "ARCH-024": "The translation for {0!r} must use contiguous placeholder indices starting at 0",
    # Pseudo translation parsing errors
    "TRN-001": "Invalid placeholder index {0!r} in translation for {1!r}",
    "TRN-002": "Invalid translation operand {0!r}",
    "TRN-003": "The translation for {0!r} has an invalid format",
    "TRN-004": "Constant {0} does not fit in {1} bits",
    # Source code errors and warnings
    "SRC-001": "Undefined {0} {1!r}",
    "SRC-002": "Invalid {0} directive format",
    "SRC-003": "Invalid {0} name {1!r}",
    "SRC-004": "{0} {1!r} already exists",
    "SRC-005": "Invalid alias value {0!r}",
    "SRC-006": "Unsupported instruction {0!r}",
    "SRC-007": "Labels must be alone on their line",
    "SRC-008": "Invalid operand count for {0!r}",
    "SRC-009": "Circular alias detected for {0!r}",
    "SRC-010": "{0} {1!r} is defined but never used",
    "SRC-011": "Value truncated to {1} bits: {0} -> {2}",
    "SRC-012": "Source file extension {0!r} does not match the architecture file extension {1!r}",
    # Public API errors
    "API-001": "The {0} argument must be a {1}, got {2}",
}


def make_message(code: str, *parameters: object) -> str:
    try:
        template = TEMPLATES[code]
    except KeyError:
        raise ValueError(f"Unknown message code: {code!r}") from None
    return template.format(*parameters)

# Citrine

Citrine assembles a program into machine code from an architecture file. The
architecture defines the available instructions, aliases, and shortcuts.

## Installation

Python 3.13 or later.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
citrine --version
```

## Usage

```bash
citrine examples/test_program.grt3 -a architecture/garnetCoreV3.json
citrine - -a architecture/garnetCoreV3.json < examples/test_program.grt3
```

`assemble` is implicit; `arch` and `architecture` are explicit. The code is
printed to standard output by default, one instruction per line; `-` denotes
standard input.

| Option | Effect |
| --- | --- |
| `-a`, `--architecture` | Architecture file (required) |
| `-o`, `--output` | Output file, or `-` for standard output (default) |
| `-f`, `--format` | Format `bin` (default), `hex`, or `dec` |
| `-c`, `--check` | Assemble without writing the code or the listing |
| `-l`, `--listing` | Listing file, or `-` for standard output |
| `-p`, `--no-pad` | Disables zero padding |
| `-q`, `--quiet` | Hides warnings |
| `-s`, `--strict` | Fails the assembly if any warnings are present |
| `-d`, `--diagnostics` | Messages as `text` or `json` |
| `-D`, `--diagnostics-output` | Messages file, or `-` for standard error (default) |
| `-h`, `--help` | Shows the help |
| `-v`, `--version` | Shows the version |

## Outputs

Values are padded according to the instruction size; `--no-pad` disables this
padding. If the output path is a directory or ends with `/`, the base name of
the source is reused with `.mc`, `.lst`, `.log`, or `.json`; otherwise, the path
is used as is. For standard input, the base name is `-`. An empty program or a
failed assembly writes neither code nor listing.

With `-l`, the listing shows the address, the machine word, and the source line.

## Writing a program

The language is case-insensitive. Empty lines and comments (`//`) are ignored;
commas are accepted as separators.

The examples in this section target `architecture/garnetCoreV3.json`:

```asm
DEFINE N AS 5

USED .main

.main:
    LDI, R0, N
    HLT
```

**Instructions and operands.** The number of operands follows the instruction's
variable fields or the pseudo-instruction's placeholders. An operand can be an
integer (`42`, `-8`, `0b101010`, `0o52`, `0d42`, `0x2a`), an alias, or a label.
An out-of-range value is masked with a warning.

**Aliases.** `DEFINE` associates a name with a value, an alias, or a label, even
one defined later. An alias cannot be redefined and produces a warning if it is
unused. A circular chain is reported when used; an alias to a missing name is an
error. Names start with a letter or `_`, followed by letters, digits, or `_`;
`DEFINE`, `USED`, `PSEUDO`, `AS`, and `TO` are reserved.

**Labels and `USED`.** A label starts with `.`, ends with `:`, and must be alone
on its line. Its value is the index of the next instruction. A forward reference
is allowed; a missing label is an error and an unused label produces a warning.
`USED .main` marks a label as used without changing the generated code.

**Pseudo-instructions.** A pseudo-instruction is a local abbreviation whose
target must be a real instruction. The translation provides one argument per
variable field; each argument is a constant or a `{n}` placeholder. Indices start
at `0`, must be contiguous, and may be repeated. An out-of-range constant is
masked with a warning. An unused pseudo-instruction produces a warning, except
those provided by the architecture.

```asm
PSEUDO SUBTRACT TO ARI 2 {0} {0} {1}
PSEUDO COPY TO BIT 3 {0} {1} {1}

SUBTRACT R2 R1    // becomes ARI 2 R2 R2 R1
COPY R3 R0        // becomes BIT 3 R3 R0 R0
```

A placeholder accepts a prefix that transforms the operand before it is
inserted into the target field:

| Prefix | Operation |
| --- | --- |
| `-` | Arithmetic negation |
| `~` | Bitwise NOT |
| `<` | Rotate left |
| `>` | Rotate right |
| `@` | Bit reversal |

## Describing an architecture

The architecture file fully describes the instruction set; unknown fields are
rejected.

| Field | Required | Role |
| --- | --- | --- |
| `architecture_name` | yes | Name of the architecture |
| `instruction_length` | yes | Size of an instruction, from 1 to 128 bits |
| `instruction_set` | yes | Instructions and their encoding |
| `file_extension` | yes | Program extension, for example `.grt3` |
| `aliases` | no | Aliases available in all programs |
| `pseudo_instruction_set` | no | Pseudo-instructions provided by the architecture |

The extension starts with a dot and then contains only letters or digits.

```json
{
  "architecture_name": "Example Core",
  "instruction_length": 8,
  "instruction_set": {
    "ADD": ["00", "x2 x2 x2"],
    "LDI": ["01", "x2 x4"],
    "HLT": ["11", "000000"]
  },
  "aliases": {"R0": 0, "R1": 1, "R2": 2, "R3": 3},
  "file_extension": ".exa"
}
```

An instruction is a binary opcode followed by fields. In
`"ADD": ["00", "x2 x2 x2"]`, `00` is the opcode, `xN` is an `N`-bit operand, and
a sequence of `0`/`1` is a fixed field. The total, including the opcode, equals
`instruction_length`. Opcodes have the same width and are unique; instruction
and pseudo-instruction names contain only letters and are not reserved.
`ADD R1 R2 R3` encodes as `00011011`.

Architecture aliases are integers valid in all programs. Their names may contain
symbols (`==`, `!=`, `'A'`) but cannot be an integer, a reserved word, or start
with a dot; they do not produce a warning when unused. Architecture
pseudo-instructions follow the `PSEUDO` rules; an out-of-range constant is an
error in the architecture but a warning in a `PSEUDO` directive.

The architecture is validated before each assembly. It can also be checked on
its own (`arch` and `architecture` are equivalent):

```bash
citrine arch validate architecture/garnetCoreV3.json
citrine arch show architecture/garnetCoreV3.json
```

`validate` prints `<file>: ok`; `show` prints a JSON summary. These commands
accept `-d` and `-D`, not `-q` or `-s`.

## Messages and exit codes

Errors and warnings are printed to standard error. Format:
`ERROR | line 31 | Invalid operand count for 'ldi' | LDI R1`.

`-d json` groups them under `errors` and `warnings`; `-D` redirects them to a
file; `-q` hides warnings. `-s` makes them blocking (code `1`), but they remain
of `WARNING` severity.

A program extension different from the architecture's produces a warning, except
with `--strict` and except for standard input.

Exit codes: `0` success, `1` assembly or architecture error (or warning with
`--strict`), `2` usage error, `3` read or write error.

## License

MIT. See [LICENSE](LICENSE).

from typing import Final

KNOWN_COMMANDS: set[str] = {"assemble", "architecture", "arch"}
SPECIAL_OPTIONS: set[str] = {"-h", "--help", "-v", "--version"}

# Standard stream argument.
STDIN: Final[str] = "-"
STDOUT: Final[str] = "-"
STDERR: Final[str] = "-"

# Exit code
EXIT_OK: int = 0
EXIT_ERRORS: int = 1
EXIT_USAGE: int = 2
EXIT_IO: int = 3

FALLBACK_VERSION = "dev"

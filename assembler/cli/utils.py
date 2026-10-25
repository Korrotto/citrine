import sys
from argparse import Namespace
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from json import JSONDecodeError, dumps, load
from pathlib import Path
from typing import Never, TextIO, cast

from assembler.cli.constants import (
    EXIT_ERRORS,
    EXIT_IO,
    EXIT_OK,
    FALLBACK_VERSION,
    STDERR,
    STDIN,
    STDOUT,
)


def read_json(path: str) -> object:
    try:
        with open(path, encoding="utf-8-sig") as raw_content:
            return load(raw_content)
    except (OSError, UnicodeDecodeError) as error:
        die_io(f"cannot read {path}: {error}")
    except (JSONDecodeError, RecursionError) as error:
        die_io(f"invalid JSON in {path}: {error}")
    except ValueError as error:
        die_io(f"cannot read {path}: {error}")


def read_source(path: str) -> str:
    try:
        if path == STDIN:
            return sys.stdin.read()
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        die_io(f"cannot read {path}: {error}")


def die_io(message: str) -> Never:
    print(f"citrine: error: {message}", file=sys.stderr)
    raise SystemExit(EXIT_IO)


def read_architecture(path: str) -> dict[str, object]:
    data: object = read_json(path)

    if not isinstance(data, dict):
        print("citrine assemble: architecture JSON file must be an object", file=sys.stderr)
        raise SystemExit(EXIT_ERRORS)

    return cast(dict[str, object], data)


def write_file(path: str, data: str, file_name: str, suffix: str, stream: TextIO) -> None:
    if path in (STDOUT, STDERR):
        print(data, file=stream)
        return

    output: Path = Path(path)
    if output.is_dir() or path.endswith(("/", "\\")):
        output = output / Path(file_name).with_suffix(suffix)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(data + "\n", encoding="utf-8")
    except OSError as error:
        die_io(f"cannot write {path}: {error}")


def write_errors_and_warnings(args: Namespace, data: str, file_name: str) -> None:
    suffix: str = ".json" if args.diagnostics == "json" else ".log"
    write_file(str(args.diagnostics_output), data, file_name, suffix, sys.stderr)


def write_code(args: Namespace, data: str, file_name: str) -> None:
    suffix: str = ".mc"
    write_file(str(args.output), data, file_name, suffix, sys.stdout)


def write_list(args: Namespace, data: str, file_name: str) -> None:
    suffix: str = ".lst"
    write_file(str(args.listing), data, file_name, suffix, sys.stdout)


def report(errors: list[str], warnings: list[str], args: Namespace, file_name: str) -> int:
    visible_warnings: list[str] = [] if getattr(args, "quiet", False) else warnings

    if args.diagnostics == "json":
        diagnostics: str = dumps({"errors": errors, "warnings": visible_warnings}, indent=2)
    else:
        diagnostics = "\n".join(errors + visible_warnings)

    if errors or visible_warnings:
        write_errors_and_warnings(args, diagnostics, file_name)

    if errors or (getattr(args, "strict", False) and warnings):
        return EXIT_ERRORS

    return EXIT_OK


def base_encode(machine_code: list[int], length: int, no_padding: bool, base: str) -> list[str]:
    return [f"{code:{base}}" if no_padding else f"{code:0{length}{base}}" for code in machine_code]


def binary_encode(machine_code: list[int], length: int, no_padding: bool) -> list[str]:
    return base_encode(machine_code, length, no_padding, "b")


def hexa_encode(machine_code: list[int], length: int, no_padding: bool) -> list[str]:
    length = (length + 3) // 4
    return base_encode(machine_code, length, no_padding, "x")


def decimal_encode(machine_code: list[int], length: int, no_padding: bool) -> list[str]:
    length = len(str((1 << length) - 1))
    return base_encode(machine_code, length, no_padding, "d")


ENCODERS: dict[str, Callable[[list[int], int, bool], list[str]]] = {
    "bin": binary_encode,
    "hex": hexa_encode,
    "dec": decimal_encode,
}


def package_version() -> str:
    try:
        return version("citrine-assembler")
    except PackageNotFoundError:
        return FALLBACK_VERSION

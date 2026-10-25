from ..common.utils import normalize
from .models import TokenizedLine
from .utils import is_label_line, line_type


class Tokenizer:
    @staticmethod
    def tokenize_source_code(source_code: str) -> list[TokenizedLine]:
        source_code = source_code.removeprefix("\ufeff")
        return [
            line
            for number, raw in enumerate(source_code.splitlines(), 1)
            if (line := Tokenizer.tokenize_line(raw, number)) is not None
        ]

    @staticmethod
    def tokenize_line(raw_line: str, line_number: int) -> TokenizedLine | None:
        if not (text := raw_line.split("//", 1)[0].strip()):
            return None

        normalized_line: str = normalize(text)
        is_label: bool = is_label_line(normalized_line)
        body: str = normalized_line[:-1] if is_label else normalized_line

        if not (tokens := tuple(body.replace(",", " ").split())):
            return None

        return TokenizedLine(line_number, text, tokens, line_type(tokens[0], is_label))

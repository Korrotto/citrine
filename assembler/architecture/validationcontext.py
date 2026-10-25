from ..common.utils import log_error


class ValidationContext:
    def __init__(self, raw_data: dict[str, object]) -> None:
        self.raw_data: dict[str, object] = raw_data
        self.errors: list[str] = []

    def log_error(self, code: str, *args: object) -> None:
        self.errors.append(log_error(code, *args))

    def require(self, key: str, missing_code: str) -> bool:
        if key in self.raw_data:
            return True
        self.log_error(missing_code, key)
        return False

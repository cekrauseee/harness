class HarnessError(Exception):
    """A user-actionable contract failure."""

    def __init__(self, code: str, message: str, hint: str = "", exit_code: int = 2):
        super().__init__(message)
        self.code = code
        self.hint = hint
        self.exit_code = exit_code


def require(condition, code: str, message: str, hint: str = ""):
    if not condition:
        raise HarnessError(code, message, hint)

__all__ = ["BCQLSyntaxError"]


class BCQLSyntaxError(Exception):
    def __init__(self, error_message: str, *, bcql_query: str = "", error_position: int | None = None) -> None:
        self.query = bcql_query
        self.position = error_position
        self.message = error_message
        super().__init__(str(self))

    def __str__(self) -> str:
        # Potential issue: this assumes there are no newlines in the query
        # TODO: check that bcql cannot/should not contain newlines which might mess with this error formatting
        parts = [self.message]
        if self.query and self.position is not None:
            parts.append(f"  {self.query}")
            parts.append(f"  {' ' * self.position}^")
        return "\n".join(parts)

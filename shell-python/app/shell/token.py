import enum
from dataclasses import dataclass


TokenType = enum.Enum(
    "TokenType",
    [
        "DGREAT",
        "EOF",
        "GREAT",
        "IO_NUMBER",
        "OR",
        "WORD",
    ],
)


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str

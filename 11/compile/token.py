from enum import Enum
from typing import Any

from compile.syntax import *


class Token:
    def __init__(self, token: str, line: int, kind: TokenEnum) -> None:
        self.token = token
        self.line = line
        self.kind = kind

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, self.token)

class Symbol(Token):
    def __init__(self, token: str, line: int) -> None:
        super().__init__(token, line, TokenEnum.SYMBOL)

class Keyword(Token):
    def __init__(self, token: str, line: int) -> None:
        super().__init__(token, line, TokenEnum.KEYWORD)
        self.enum = KEYWORD_CONST_MAP[token]

class Identifier(Token):
    def __init__(self, token: str, line: int) -> None:
        super().__init__(token, line, TokenEnum.IDENTIFIER)

class StringConst(Token):
    def __init__(self, token: str, line: int) -> None:
        super().__init__(token, line, TokenEnum.STRING_CONST)

class IntConst(Token):
    def __init__(self, token: str, line: int) -> None:
        super().__init__(token, line, TokenEnum.INT_CONST)
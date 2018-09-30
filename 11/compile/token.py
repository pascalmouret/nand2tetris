from typing import Any


CLASS = 0
CONSTRUCTOR = 1
FUNCTION = 2
METHOD = 3
FIELD = 4
STATIC = 5
VAR = 6
INT = 7
CHAR = 8
BOOLEAN = 9
VOID = 10
TRUE = 11
FALSE = 12
NULL = 13
THIS = 14
LET = 15
DO = 16
IF = 17
ELSE = 18
WHILE = 19
RETURN = 20
SYMBOL = 21
IDENTIFIER = 22
INT_CONST = 23
STRING_CONST = 24


CONST_MAP = {
    'class': CLASS,
    'constructor': CONSTRUCTOR,
    'function': FUNCTION,
    'method': METHOD,
    'field': FIELD,
    'static': STATIC,
    'var': VAR,
    'int': INT,
    'char': CHAR,
    'boolean': BOOLEAN,
    'void': VOID,
    'true': TRUE,
    'false': FALSE,
    'null': NULL,
    'this': THIS,
    'let': LET,
    'do': DO,
    'if': IF,
    'else': ELSE,
    'while': WHILE,
    'return': RETURN,
    'SYMBOL': SYMBOL,
    'IDENTIFIER': IDENTIFIER,
    'INT_CONST': INT_CONST,
    'STRING_CONST': STRING_CONST
}


CONST_NAME_MAP = dict([(v, k) for k, v in CONST_MAP.items()])


class Token:
    def __init__(self, token: str, line: int, const: int) -> None:
        self.token = token
        self.const = const
        self.line = line

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, self.token)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Token):
            return self.token == other.token
        return other == self.token or other == self.const

    def __hash__(self):
        return self.const

    def to_xml(self) -> str:
        return '<{0}> {1} </{0}>'.format(
            self.__class__.__name__[0].lower() + self.__class__.__name__[1:],
            self.token
        )

class Symbol(Token):
    def __init__(self, token: str, line: int) -> None:
        super().__init__(token, line, SYMBOL)

class Identifier(Token):
    def __init__(self, token: str, line: int) -> None:
        super().__init__(token, line, IDENTIFIER)

class IntConst(Token):
    def __init__(self, token: str, line: int) -> None:
        super().__init__(token, line, INT_CONST)

class StringConst(Token):
    def __init__(self, token: str, line: int) -> None:
        super().__init__(token, line, STRING_CONST)

class Keyword(Token):
    def __init__(self, token: str, line: int) -> None:
        super().__init__(token, line, CONST_MAP[token])

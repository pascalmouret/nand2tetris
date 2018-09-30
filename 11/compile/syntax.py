from enum import Enum


class IdentEnum(Enum):
    STATIC = 0
    FIELD = 1
    ARG = 2
    VAR = 3
    SUB = 4
    CLASS = 5

class KeywordEnum(Enum):
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

class TokenEnum(Enum):
    KEYWORD = 0
    SYMBOL = 1
    IDENTIFIER = 2
    INT_CONST = 3
    STRING_CONST = 4


KEYWORD_CONST_MAP = {
    'class': KeywordEnum.CLASS,
    'constructor': KeywordEnum.CONSTRUCTOR,
    'function': KeywordEnum.FUNCTION,
    'method': KeywordEnum.METHOD,
    'field': KeywordEnum.FIELD,
    'static': KeywordEnum.STATIC,
    'var': KeywordEnum.VAR,
    'int': KeywordEnum.INT,
    'char': KeywordEnum.CHAR,
    'boolean': KeywordEnum.BOOLEAN,
    'void': KeywordEnum.VOID,
    'true': KeywordEnum.TRUE,
    'false': KeywordEnum.FALSE,
    'null': KeywordEnum.NULL,
    'this': KeywordEnum.THIS,
    'let': KeywordEnum.LET,
    'do': KeywordEnum.DO,
    'if': KeywordEnum.IF,
    'else': KeywordEnum.ELSE,
    'while': KeywordEnum.WHILE,
    'return': KeywordEnum.RETURN,
}
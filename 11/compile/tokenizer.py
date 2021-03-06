import itertools
from pathlib import Path
from typing import Iterator

from compile.token import *
from compile.syntax import KEYWORD_CONST_MAP


class Tokenizer:
    KEYWORDS = set(KEYWORD_CONST_MAP.keys())
    WHITESPACE = set(' \n\t')
    SYMBOLS = set('{}()[].,;+-*/&|<>=~')
    STOPERS = WHITESPACE | SYMBOLS

    def __init__(self, path: Path) -> None:
        self.file = path

    def __iter__(self) -> Iterator[Token]:
        self.file_handle = open(self.file)
        self.line_count = 1
        self.char_iter = itertools.chain.from_iterable(self.file_handle)
        self.current = None
        self.next = self.char_iter.__next__()
        return self

    def load_next(self) -> None:
        self.current = self.next;
        try:
            if self.current == '\n':
                self.line_count += 1
            self.next = self.char_iter.__next__()
        except StopIteration:
            self.file_handle.close()
            self.next = None

    def __next__(self) -> Token:
        if self.next is None:
            raise StopIteration
        
        current_token = []
        while True:
            self.load_next()
            if self.current == '"':
                return self.read_string_const()
            self.skip_comment()
            if self.current in self.SYMBOLS:
                return Symbol(self.current, self.line_count);
            if self.current not in self.WHITESPACE:
                current_token.append(self.current)
            if self.next in self.STOPERS or not self.next:
                break
        if not current_token:
            return self.__next__()
        return self.identify(''.join(current_token))

    def identify(self, token: str) -> Token:
        if token in self.KEYWORDS:
            return Keyword(token, self.line_count)
        if token[0].isdigit():
            return IntConst(token, self.line_count)
        return Identifier(token, self.line_count)

    def read_string_const(self) -> StringConst:
        string = []
        while True:
            self.load_next()
            if self.current == '"':
                return StringConst(''.join(string), self.line_count)
            else:    
                string.append(self.current)

    def skip_comment(self) -> None:
        if self.current == '/':
            if self.next == '/':
                while self.current != '\n':
                    self.load_next()
                return None
            if self.next == '*':
                last = self.current
                while not (last == '*' and self.current == '/'):
                    last = self.current
                    self.load_next()
                self.load_next()
        return None

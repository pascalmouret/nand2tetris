import itertools
from pathlib import Path
from typing import Iterator

from compile.token import *


class Tokenizer:
    KEYWORDS = set(CONST_MAP.keys())
    WHITESPACE = set(' \n\t')
    SYMBOLS = set('{}()[].,;+-*/&|<>=~')
    STOPERS = WHITESPACE | SYMBOLS

    def __init__(self, path: Path) -> None:
        self.file = path

    def __iter__(self) -> Iterator[Token]:
        self.file_handle = open(self.file)
        self.char_iter = itertools.chain.from_iterable(self.file_handle)
        self.current = None
        self.next = self.char_iter.__next__()
        return self

    def load_next(self) -> None:
        self.current = self.next;
        try:
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
                return Symbol(self.current);
            if self.current not in self.WHITESPACE:
                current_token.append(self.current)
            if self.next in self.STOPERS or not self.next:
                break
        if not current_token:
            return self.__next__()
        return self.identify(''.join(current_token))

    def identify(self, token: str) -> Token:
        if token in self.KEYWORDS:
            return Keyword(token)
        if token[0].isdigit():
            return IntConst(token)
        return Identifier(token)

    def read_string_const(self) -> StringConst:
        string = []
        while True:
            self.load_next()
            if self.current == '"':
                return StringConst(''.join(string))
            else:    
                string.append(self.current)

    def skip_comment(self) -> None:
        if self.current == '/':
            if self.next == '/':
                while self.current != '\n':
                    self.load_next()
                return None
            if self.next == '*':
                for c in self.char_iter:
                    last = self.current
                    self.current = self.next
                    self.next = c
                    if last == '*' and self.current == '/':
                        self.load_next()
                        return None
        return None

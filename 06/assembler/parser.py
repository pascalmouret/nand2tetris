import re
from typing import Iterator, Optional

from assembler.expressions import Empty, Label, ACommand, CCommand, Expression


class Parser():
    def __init__(self, path: str) -> None:
        self.f = open(path)

    def __iter__(self) -> Iterator[Expression]:
        self.f.seek(0)
        return self

    def __next__(self) -> Expression:
        for line in self.f:
            expr = self.parseExpression(line) 
            if isinstance(expr, Empty):
                return self.__next__()
            return expr
        raise StopIteration

    def parseExpression(self, expr: str) -> Expression:
        expr = re.sub(r'\s+', '', expr)
        expr = re.sub(r'//.*', '', expr)
        if expr == '':
            return Empty(expr)
        elif expr.startswith('('):
            return Label(expr)
        elif expr.startswith('@'):
            return ACommand(expr)
        else:
            return CCommand(expr)
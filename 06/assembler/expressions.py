import abc
from typing import Optional

from assembler.symbols import SymbolTable


JUMPS = {
    '': 0,
    'JGT': 1,
    'JEQ': 2,
    'JGE': 3,
    'JLT': 4,
    'JNE': 5,
    'JLE': 6,
    'JMP': 7
}


DEST = { 
    '': 0,
    'M': 1,
    'D': 2,
    'MD': 3,
    'A': 4,
    'AM': 5,
    'AD': 6,
    'AMD': 7
}


OPS = {
    '0': 0b0101010,
    '1': 0b0111111,
    '-1': 0b0111010,
    'D': 0b0001100,
    'A': 0b0110000,
    'M': 0b1110000,
    '!D': 0b0001101,
    '!A': 0b0110001,
    '!M': 0b1110001,
    '-D': 0b0001111,
    '-A': 0b0110011,
    '-M': 0b1110011,
    'D+1': 0b0011111,
    'A+1': 0b0110111,
    'M+1': 0b1110111,
    'D-1': 0b0001110,
    'A-1': 0b0110010,
    'M-1': 0b1110010,
    'D+A': 0b0000010,
    'D+M': 0b1000010,
    'D-A': 0b0010011,
    'D-M': 0b1010011,
    'A-D': 0b0000111,
    'M-D': 0b1000111,
    'D&A': 0b0000000,
    'D&M': 0b1000000,
    'D|A': 0b0010101,
    'D|M': 0b1010101
}


class Expression(metaclass=abc.ABCMeta):
    def __init__(self, expr: str) -> None:
        self.expr = expr
        
    @abc.abstractmethod
    def translate(self, symbols: SymbolTable) -> Optional[str]: ...

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.expr)


class Empty(Expression):
    def translate(self, symbols: SymbolTable) -> Optional[str]: 
        return None


class Label(Expression):
    def translate(self, symbols: SymbolTable) -> Optional[str]:
        return None

    def get_label(self) -> str:
        return self.expr[1:-1]


class ACommand(Expression):
    def translate(self, symbols: SymbolTable) -> Optional[str]:
        value = self.expr[1:]
        if value[0].isdigit():
            address = int(value)
        else:
            address = symbols.address_for_symbol(value)
        return '0{:015b}'.format(address)


class CCommand(Expression):
    def translate(self, symbols: SymbolTable) -> Optional[str]:
        comp = self.expr
        if '=' in comp:
            dest, comp = comp.split('=')
        else:
            dest = ''
        if ';' in comp:
            comp, jmp = comp.split(';')
        else:
            jmp = ''
        return '111{0:07b}{1:03b}{2:03b}'.format(OPS[comp], DEST[dest], JUMPS[jmp])

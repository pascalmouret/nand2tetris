import abc
from typing import Optional


class Command(metaclass=abc.ABCMeta):
    def __init__(self, command: str, file: str) -> None:
        self.command = command
        self.file = file

    @abc.abstractmethod
    def to_asm(self) -> str: ...

    def constant(self) -> str:
        return ''

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.command)


class Add(Command):
    def to_asm(self) -> str:
        return '''
            @SP
            AM=M-1
            D=M
            A=A-1
            M=M+D
        '''

class Sub(Command):
    def to_asm(self) -> str:
        return '''
            @SP
            AM=M-1
            D=M
            A=A-1
            M=M-D
        '''

class Neg(Command):
    def to_asm(self) -> str:
        return '''
            @SP
            A=M-1
            M=!M
            M=M+1
        '''

class Eq(Command):
    label_count = 0

    def next_label(self):
        Eq.label_count += 1
        return 'EQ_RET_{}'.format(Eq.label_count)

    def constant(self):
        return '''
            (EQ)
            @SP
            AM=M-1
            D=M
            A=A-1
            D=D-M
            M=-1
            @EQ_END
            D;JEQ
            @SP
            A=M-1
            M=0
            (EQ_END)
            @R15
            A=M
            0;JMP
        '''

    def to_asm(self) -> str:
        return '''
            @{0}
            D=A
            @R15
            M=D
            @EQ
            0;JMP
            ({0})
        '''.format(self.next_label())
    
class Gt(Command):
    label_count = 0
    
    def next_label(self):
        Gt.label_count += 1
        return 'GT_RET_{}'.format(Gt.label_count)

    def constant(self) -> str:
        return '''
            (GT)
            @SP
            AM=M-1
            D=M
            A=A-1
            D=M-D
            M=-1
            @GT_END
            D;JGT
            @SP
            A=M-1
            M=0
            (GT_END)
            @R15
            A=M
            0;JMP
        '''

    def to_asm(self) -> str:
        return '''
            @{0}
            D=A
            @R15
            M=D
            @GT
            0;JMP
            ({0})
        '''.format(self.next_label())
    
class Lt(Command):
    label_count = 0
    
    def next_label(self):
        Lt.label_count += 1
        return 'LT_RET_{}'.format(Lt.label_count)

    def constant(self) -> str:
        return '''
            (LT)
            @SP
            AM=M-1
            D=M
            A=A-1
            D=M-D
            M=-1
            @LT_END
            D;JLT
            @SP
            A=M-1
            M=0
            (LT_END)
            @R15
            A=M
            0;JMP
        '''

    def to_asm(self) -> str:
        return '''
            @{0}
            D=A
            @R15
            M=D
            @LT
            0;JMP
            ({0})
        '''.format(self.next_label())

class And(Command):
    def to_asm(self) -> str:
        return '''
            @SP
            AM=M-1
            D=M
            A=A-1
            M=D&M
        '''

class Or(Command):
    def to_asm(self) -> str:
        return '''
            @SP
            AM=M-1
            D=M
            A=A-1
            M=D|M
        '''

class Not(Command):
    def to_asm(self) -> str:
        return '''
            @SP
            A=M-1
            M=!M
        '''

class MemoryCommand(Command):
    REGS = {
        'local': 'LCL',
        'argument': 'ARG',
        'this': 'THIS',
        'that': 'THAT'
    }
    
    def load_address(self, segment: str, index: int) -> str:
        if segment == 'pointer':
            return '@{}'.format(3 + index)
        elif segment == 'temp':
            return '@{}'.format(5 + index)
        elif segment == 'static':
            return '@{}.{}'.format(self.file, index)
        else:
            return '''
                @{0}
                D=M
                @{1}
                A=D+A
            '''.format(self.REGS[segment], index)
            
class Push(MemoryCommand):
    def value_to_d(self, segment: str, index: int) -> str:
        if segment == 'constant':
            return '''
                @{}
                D=A
            '''.format(index)
        else:
            return '''
                {}
                D=M
            '''.format(self.load_address(segment, index))

    def to_asm(self) -> str:
        segment, index = self.command.split(' ')[1:]
        return '''
            {}
            @SP
            M=M+1
            A=M-1
            M=D
        '''.format(self.value_to_d(segment, int(index)))

class Pop(MemoryCommand):
    def to_asm(self) -> str:
        segment, index = self.command.split(' ')[1:]
        if segment == 'constant':
            return ''
        return '''
            {}
            D=A
            @R14
            M=D
            @SP
            AM=M-1
            D=M
            @R14
            A=M
            M=D
        '''.format(self.load_address(segment, int(index)))


COMMANDS = {
    'add': Add,
    'sub': Sub,
    'neg': Neg,
    'eq': Eq,
    'gt': Gt,
    'lt': Lt,
    'and': And,
    'or': Or,
    'not': Not,
    'push': Push,
    'pop': Pop
}


def parse_command(command: str, file: str) -> Command:
    return COMMANDS[command.split(' ')[0]](command, file)
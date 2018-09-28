import abc
from typing import Optional, TypeVar


class Context:
    def __init__(self, file: str, function: str) -> None:
        self.file = file
        self.function = function

    def static_symbol(self, index: int) -> str:
        return '{}.{}'.format(self.file, index)

    def label(self, name: str) -> str:
        return '{}.{}'.format(self.function, name) if self.function else name


class Command(metaclass=abc.ABCMeta):
    def __init__(self, command: str) -> None:
        self.command = command

    @abc.abstractmethod
    def to_asm(self, context: Context) -> str: ...

    def constant(self) -> str:
        return ''

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.command)


class Add(Command):
    def to_asm(self, context: Context) -> str:
        return '''
            @SP
            AM=M-1
            D=M
            A=A-1
            M=M+D
        '''

class Sub(Command):
    def to_asm(self, context: Context) -> str:
        return '''
            @SP
            AM=M-1
            D=M
            A=A-1
            M=M-D
        '''

class Neg(Command):
    def to_asm(self, context: Context) -> str:
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

    def to_asm(self, context: Context) -> str:
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

    def to_asm(self, context: Context) -> str:
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
            M=0
            @LT_END
            D;JLT
            @SP
            A=M-1
            M=-1
            (LT_END)
            @R15
            A=M
            0;JMP
        '''

    def to_asm(self, context: Context) -> str:
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
    def to_asm(self, context: Context) -> str:
        return '''
            @SP
            AM=M-1
            D=M
            A=A-1
            M=D&M
        '''

class Or(Command):
    def to_asm(self, context: Context) -> str:
        return '''
            @SP
            AM=M-1
            D=M
            A=A-1
            M=D|M
        '''

class Not(Command):
    def to_asm(self, context: Context) -> str:
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
    
    def load_address(self, segment: str, index: int, context: Context) -> str:
        if segment == 'pointer':
            return '@{}'.format(3 + index)
        elif segment == 'temp':
            return '@{}'.format(5 + index)
        elif segment == 'static':
            return '@{}'.format(context.static_symbol(index))
        else:
            return '''
                @{0}
                D=M
                @{1}
                A=D+A
            '''.format(self.REGS[segment], index)
            
class Push(MemoryCommand):
    def value_to_d(self, segment: str, index: int, context: Context) -> str:
        if segment == 'constant':
            return '''
                @{}
                D=A
            '''.format(index)
        else:
            return '''
                {}
                D=M
            '''.format(self.load_address(segment, index, context))

    def to_asm(self, context: Context) -> str:
        segment, index = self.command.split(' ')[1:]
        return '''
            {}
            @SP
            M=M+1
            A=M-1
            M=D
        '''.format(self.value_to_d(segment, int(index), context))

class Pop(MemoryCommand):
    def to_asm(self, context: Context) -> str:
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
        '''.format(self.load_address(segment, int(index), context))

class Goto(Command):
    def to_asm(self, context: Context) -> str:
        return '''
            @{}
            0;JMP
        '''.format(context.label(self.command.split()[1]))

class IfGoto(Command):
    def to_asm(self, context: Context) -> str:
        return '''
            @SP
            AM=M-1
            D=M
            @{}
            D;JNE
        '''.format(self.command.split(' ')[1])

class Label(Command):
    def to_asm(self, context: Context) -> str:
        return '''
            ({})
        '''.format(context.label(self.command.split()[1]))

class Function(Command):
    def push_empty(self) -> str:
        return '''
            @SP
            M=M+1
            A=M-1
            M=0
        '''

    def to_asm(self, context: Context) -> str:
        name, lcls = self.command.split(' ')[1:]
        context.function = name
        return '''
            ({})
            {}
        '''.format(
                name, 
                ''.join([self.push_empty() for i in range(0, int(lcls))])
            )

class Call(Command):
    label_count = 0
    
    def next_label(self) -> str:
        Call.label_count += 1
        return 'CALL_RET_{}'.format(Call.label_count)

    def push_reg(self, reg: str) -> str:
        return '''
            @{}
            D=M
            @SP
            M=M+1
            A=M-1
            M=D
        '''.format(reg)

    def to_asm(self, context: Context) -> str:
        name, args = self.command.split(' ')[1:]
        return '''
            // push return address
            @{2}
            D=A
            @SP
            M=M+1
            A=M-1
            M=D
            // push registers
            {3}
            {4}
            {5}
            {6}
            // set ARG
            @{1}
            D=A
            @SP
            D=M-D
            @ARG
            M=D
            // set LCL
            @SP
            D=M
            @LCL
            M=D
            // jump
            @{0}
            0;JMP
            ({2})
        '''.format(
                name, 
                int(args) + 5,
                self.next_label(), 
                self.push_reg('LCL'), 
                self.push_reg('ARG'), 
                self.push_reg('THIS'), 
                self.push_reg('THAT')
            )

class Return(Command):
    def pop_reg(self, name: str, offset: int) -> str:
        return '''
            @R15
            D=M
            @{}
            A=D-A
            D=M
            @{}
            M=D
        '''.format(offset, name)

    def to_asm(self, context: Context) -> str:
        context.function = ''
        return '''
            // store LCL (R15)
            @LCL
            D=M
            @R15
            M=D
            // store return (R14)
            @5
            D=A
            @R15
            A=M-D
            D=M
            @R14
            M=D
            // pop return value
            @SP
            AM=M-1
            D=M
            @ARG
            A=M
            M=D
            // restore stack to ARG+1
            @ARG
            D=M
            @SP
            M=D+1
            {}
            {}
            {}
            {}
            @R14
            A=M
            0;JMP
        '''.format(
                self.pop_reg('THAT', 1),
                self.pop_reg('THIS', 2),
                self.pop_reg('ARG', 3),
                self.pop_reg('LCL', 4),
            )



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
    'pop': Pop,
    'goto': Goto,
    'if-goto': IfGoto,
    'label': Label,
    'function': Function,
    'call': Call,
    'return': Return
}


def parse_command(command: str) -> Command:
    return COMMANDS[command.split(' ')[0]](command)
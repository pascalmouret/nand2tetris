from typing import Iterator, Type, List, Union, Set, Optional

from pathlib import Path
from textwrap import indent
from enum import Enum

from compile.symbol_table import SymbolTable
from compile.tokenizer import Tokenizer
from compile.writer import VMWriter
from compile.token import *
from compile.syntax import *


class CompilerError(Exception):
    def __init__(self, line: int, message: str) -> None:
        super().__init__('Line {}: {}'.format(line, message))


class Compiler:
    CLASS_VAR_DEC = {KeywordEnum.STATIC, KeywordEnum.FIELD}
    SUBROUTINE_DEC = {KeywordEnum.CONSTRUCTOR, KeywordEnum.FUNCTION, KeywordEnum.METHOD}
    VAR_TYPES = {KeywordEnum.INT, KeywordEnum.CHAR, KeywordEnum.BOOLEAN, TokenEnum.IDENTIFIER}
    FUNCTION_TYPES = {KeywordEnum.VOID} | VAR_TYPES
    STATEMENTS = {KeywordEnum.LET, KeywordEnum.IF, KeywordEnum.WHILE, KeywordEnum.DO, KeywordEnum.RETURN}
    TERM_OPEN = set('(')
    UNARY_OP = set('-~')
    BINARY_OP = set('+-*/&|<>=')
    ALL_OPS = BINARY_OP | UNARY_OP
    EXPR_CONST = {KeywordEnum.TRUE, KeywordEnum.FALSE, KeywordEnum.NULL, KeywordEnum.THIS, TokenEnum.INT_CONST, TokenEnum.STRING_CONST}
    TERM = {TokenEnum.IDENTIFIER} | UNARY_OP | TERM_OPEN | EXPR_CONST
    SUB_CALL = set('(.')

    def __init__(self, tokenizer: Tokenizer) -> None:
        self.tokenizer = tokenizer
    
    def write_to(self, outf: Path) -> None:
        self.class_name = None
        self.symbol_table = SymbolTable()
        self.label_count = 0

        self.tokens = iter(self.tokenizer)
        self.next() # pre-load first token

        self.writer = VMWriter(outf)
        self.outf = open(outf, 'w')
        self.compile_file()
        self.outf.close()

    def compile_file(self) -> None:
        self.compile_class()

    def next(self) -> None:
        try:
            self.current = next(self.tokens)
        except StopIteration:
            raise CompilerError(self.current.line, 'Unexpected EOF.')

    def current_is(self, options: Union[
        TokenEnum, KeywordEnum, str, 
        Set[Union[TokenEnum, KeywordEnum, str]]
    ]) -> bool:
        if not isinstance(options, set):
            options = {options}
        if self.current.kind in options:
            return True
        elif self.current.kind == TokenEnum.KEYWORD:
            return self.current.enum in options
        elif self.current.kind == TokenEnum.SYMBOL:
            return self.current.token in options

    def discard_if(self, options: Union[
        TokenEnum, KeywordEnum, str, 
        Set[Union[TokenEnum, KeywordEnum, str]]
    ]) -> Token:
        if self.current_is(options):
            token = self.current
            self.next()
            return token
        else:
            if not isinstance(options, set):
                options = {options}
            self.raise_unexpected([o.name if isinstance(o, Enum) else o for o in options])

    def raise_unexpected(self, expected: Set[str]) -> None:
        raise CompilerError(self.current.line, 'Expected {}, got {} instead.'.format(
            '|'.join(expected),
            self.current.token
        ))

    def find_in_scope(self, name: str) -> Optional[Symbol]:
        return self.symbol_table.find(name)

    def get_in_scope(self, name: str) -> Symbol:
        symbol = self.find_in_scope(name)
        if not symbol:
            raise CompilerError(self.current.line, '\'{}\' not in scope.'.format(name))
        return symbol

    def push_var(self, name: str) -> None:
        symbol = self.get_in_scope(name)
        if symbol.kind == IdentEnum.STATIC:
            self.writer.push_static(symbol.index)
        elif symbol.kind == IdentEnum.FIELD:
            self.writer.push_this(symbol.index)
        elif symbol.kind == IdentEnum.ARG:
            self.writer.push_arg(symbol.index)
        else:
            self.writer.push_local(symbol.index)

    def pop_var(self, name: str) -> None:
        symbol = self.get_in_scope(name)
        if symbol.kind == IdentEnum.FIELD:
            self.writer.pop_this(symbol.index)
        elif symbol.kind == IdentEnum.STATIC:
            self.writer.pop_static(symbol.index)
        elif symbol.kind == IdentEnum.ARG:
            self.writer.pop_arg(symbol.index)
        else:
            self.writer.pop_local(symbol.index)

    def get_label_id(self) -> int:
        self.label_count += 1
        return self.label_count

    def compile_class(self) -> None:
        self.discard_if(KeywordEnum.CLASS)
        self.class_name = self.discard_if(TokenEnum.IDENTIFIER).token
        self.discard_if('{')

        while not self.current_is(self.SUBROUTINE_DEC | {'}'}):
            self.compile_class_var_dec()
        while not self.current_is('}'):
            self.compile_subroutine_dec()
         
        # can't iterate, will raise stop iteration
        if not self.current_is('}'):
            raise CompilerError(self.current.line, 'Unexpected EOF.')

    def compile_type(self, function: bool = False) -> str:
        types = self.FUNCTION_TYPES if function else self.VAR_TYPES
        return self.discard_if(types).token
            
    def compile_class_var_dec(self) -> None:
        if self.current_is(KeywordEnum.FIELD):
            var_kind = IdentEnum.FIELD
        if self.current_is(KeywordEnum.STATIC):
            var_kind = IdentEnum.STATIC
        self.discard_if(self.CLASS_VAR_DEC)
        self.compile_var_list(var_kind)

    def compile_var_list(self, var_kind: IdentEnum) -> None:
        tpe = self.compile_type()

        name = self.discard_if(TokenEnum.IDENTIFIER).token
        self.symbol_table.register(name, tpe, var_kind)
        while not self.current_is(';'):
            self.next()
            name = self.discard_if(TokenEnum.IDENTIFIER).token
            self.symbol_table.register(name, tpe, var_kind)
            
        self.discard_if(';')

    def compile_subroutine_dec(self) -> None:
        self.symbol_table.reset_function_scope()

        sub_kind = self.discard_if(self.SUBROUTINE_DEC)
        ret_kind = self.compile_type(True)
        sub_name = self.discard_if(TokenEnum.IDENTIFIER).token

        if sub_kind.enum == KeywordEnum.METHOD:
            self.symbol_table.register('this', self.class_name, IdentEnum.ARG)

        self.compile_parameter_list()
        self.discard_if('{')

        while not self.current_is({'}'} | self.STATEMENTS):
            self.compile_var_dec()

        if sub_kind.enum == KeywordEnum.FUNCTION:
            self.compile_function_setup(sub_name)
        elif sub_kind.enum == KeywordEnum.METHOD:
            self.compile_method_setup(sub_name)
        elif sub_kind.enum == KeywordEnum.CONSTRUCTOR:
            self.compile_constructor_setup(sub_name)
        
        self.compile_statements()
        self.discard_if('}')

    def compile_function_setup(self, name: str) -> None:
        self.writer.w_function(
            '{}.{}'.format(self.class_name, name), 
            self.symbol_table.count_of(IdentEnum.VAR)
        )

    def compile_method_setup(self, name: str) -> None:
        self.compile_function_setup(name)
        self.push_var('this')
        self.writer.pop_pointer(0)

    def compile_constructor_setup(self, name: str) -> None:
        self.compile_function_setup(name)
        self.writer.push_const(self.symbol_table.count_of(IdentEnum.FIELD))
        self.writer.w_call('Memory.alloc', 1)
        self.writer.pop_pointer(0)

    def compile_parameter_list(self) -> None:
        self.discard_if('(')
        
        while not self.current_is(')'):
            if self.current_is(','):
                self.next()
            tpe = self.compile_type()
            name = self.discard_if(TokenEnum.IDENTIFIER).token
            self.symbol_table.register(name, tpe, IdentEnum.ARG)

        self.discard_if(')')
            
    def compile_var_dec(self) -> None:
        self.discard_if(KeywordEnum.VAR)
        self.compile_var_list(IdentEnum.VAR)
        
    def compile_statements(self) -> None:
        self.compile_statement()
        while self.current_is(self.STATEMENTS):
            self.compile_statement()

    def compile_statement(self) -> None:
        if self.current_is(KeywordEnum.LET):
            self.compile_let()
        elif self.current_is(KeywordEnum.IF):
            self.compile_if()
        elif self.current_is(KeywordEnum.WHILE):
            self.compile_while()
        elif self.current_is(KeywordEnum.DO):
            self.compile_do()
        elif self.current_is(KeywordEnum.RETURN):
            self.compile_return()
        else:
            raise CompilerError(
                self.current.line, 
                'Expected let|if|while|do|return, got {} instead.'.format(self.current)
            )
            
    def compile_let(self) -> None:
        self.discard_if(KeywordEnum.LET)
        name = self.discard_if(TokenEnum.IDENTIFIER).token
        is_array = False
        
        if self.current_is('['):
            is_array = True
            self.discard_if('[')
            self.compile_expression()
            self.discard_if(']')
            self.writer.pop_temp(0)
            
        self.discard_if('=')
        self.compile_expression()

        if is_array:
            self.push_var(name)
            self.writer.push_temp(0)
            self.writer.w_add()
            self.writer.pop_pointer(1)
            self.writer.pop_that(0)
        else:
            self.pop_var(name)
        
        self.discard_if(';')

    def compile_if(self) -> None:
        label_id = self.get_label_id()

        self.discard_if(KeywordEnum.IF)
        
        self.compile_expression()
        self.writer.w_not()
        self.writer.w_if('_ELSE_{}'.format(label_id))

        self.discard_if('{')
        self.compile_statements()
        self.discard_if('}')

        self.writer.w_goto('_ENDIF_{}'.format(label_id))
        self.writer.w_label('_ELSE_{}'.format(label_id))

        if self.current_is(KeywordEnum.ELSE):
            self.next()
            self.discard_if('{')
            self.compile_statements()
            self.discard_if('}')

        self.writer.w_label('_ENDIF_{}'.format(label_id))
            
    def compile_while(self) -> None:
        label_id = self.get_label_id()
    
        self.discard_if(KeywordEnum.WHILE)

        self.writer.w_label('_WHILE_{}'.format(label_id))
        self.compile_expression()
        self.writer.w_not()
        self.writer.w_if('_WHILE_END_{}'.format(label_id))
        
        self.discard_if('{')
        if not self.current_is('}'):
            self.compile_statements()
        self.discard_if('}')

        self.writer.w_goto('_WHILE_{}'.format(label_id))
        self.writer.w_label('_WHILE_END_{}'.format(label_id))

    def compile_do(self) -> None:
        self.discard_if(KeywordEnum.DO)
        self.compile_subroutine_call()
        self.writer.pop_temp(0)
        self.discard_if(';')

    def compile_return(self) -> None:
        self.discard_if(KeywordEnum.RETURN)
        if self.current_is(self.TERM):
            self.compile_expression()
        else:
            self.writer.push_const(0)
        self.discard_if(';')
        self.writer.w_return()

    def compile_subroutine_call(self, last: Optional[Token] = None) -> None:
        # because we need to look t+2 ahead when doing expression, we might
        # have to pass in the identifier manually
        owner_name = last.token if last else self.discard_if(TokenEnum.IDENTIFIER).token
        class_name = owner_name
        args = 0

        if self.current_is('.'):
            self.next()
            routine_name = self.discard_if(TokenEnum.IDENTIFIER).token
            ref = self.symbol_table.find(owner_name)
            if ref:
                class_name = ref.tpe
                self.push_var(owner_name)
                args += 1
        else:
            routine_name = owner_name
            class_name = self.class_name
            self.writer.push_pointer(0)
            args += 1

        call = '{}.{}'.format(class_name, routine_name)

        self.discard_if('(')
        args += self.compile_expression_list()
        self.discard_if(')')

        self.writer.w_call(call, args)

    def compile_expression_list(self) -> None:
        args = 0
        
        if self.current_is(self.TERM):
            self.compile_expression()
            args = 1
        while self.current_is(','):
            self.discard_if(',')
            self.compile_expression()
            args += 1

        return args

    def compile_expression(self) -> None:
        self.compile_term()
        while self.current_is(self.BINARY_OP):
            op = self.current
            self.next()
            self.compile_term()
            self.compile_op(op.token)

    def compile_term(self) -> None:
        if self.current_is('('):
            self.next()
            self.compile_expression()
            self.discard_if(')')
        elif self.current_is(self.UNARY_OP):
            op = self.current
            self.next()
            self.compile_term()
            self.compile_unary_op(op.token)
        elif self.current_is(TokenEnum.IDENTIFIER):
            last = self.current
            self.next()
            if self.current_is(self.SUB_CALL):
                self.compile_subroutine_call(last)
            elif self.current_is('['):
                self.push_var(last.token)
                self.discard_if('[')
                self.compile_expression()
                self.discard_if(']')
                self.writer.w_add()
                self.writer.pop_pointer(1)
                self.writer.push_that(0)
            else:
                self.push_var(last.token)
        elif self.current_is(self.EXPR_CONST):
            self.compile_const()
        else:
            raise CompilerError(
                self.current.line,
                'Expected expression term, got {}.'.format(self.current)
            )

    def compile_op(self, operation: str) -> None:
        if operation not in self.BINARY_OP:
            raise CompilerError(
                self.current.line, 
                '\'{}\' is not a valid binary operator.'.format(operation)
            )
        
        if operation == '+':
            self.writer.w_add()
        elif operation == '-':
            self.writer.w_sub()
        elif operation == '*':
            self.writer.w_call('Math.multiply', 2)
        elif operation == '/':
            self.writer.w_call('Math.divide', 2)
        elif operation == '&':
            self.writer.w_and()
        elif operation == '|':
            self.writer.w_or()
        elif operation == '<':
            self.writer.w_lt()
        elif operation == '>':
            self.writer.w_gt()
        else:
            self.writer.w_eq()

    def compile_unary_op(self, operation: str) -> None:
        if operation not in self.UNARY_OP:
            raise CompilerError(
                self.current.line, 
                '\'{}\' is not a valid unary operator.'.format(operation)
            )

        if operation == '-':
            self.writer.w_neg()
        else:
            self.writer.w_not()

    def compile_const(self) -> None:
        const = self.discard_if(self.EXPR_CONST)
        
        if const.kind == TokenEnum.INT_CONST:
            self.writer.push_const(const.token)
        elif const.kind == TokenEnum.STRING_CONST:
            self.writer.push_const(len(const.token))
            self.writer.w_call('String.new', 1)
            for c in const.token:
                self.writer.push_const(ord(c))
                self.writer.w_call('String.appendChar', 2)
        elif const.kind == TokenEnum.KEYWORD:
            if const.enum == KeywordEnum.TRUE:
                self.writer.push_const(1)
                self.writer.w_neg()
            elif const.enum in [KeywordEnum.FALSE, KeywordEnum.NULL]:
                self.writer.push_const(0)
            elif const.enum == KeywordEnum.THIS:
                self.writer.push_pointer(0)
        
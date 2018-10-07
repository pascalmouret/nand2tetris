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
        self.writer = VMWriter(outf)
        self.outf = open(outf, 'w')
        self.depth = 0
        self.tokens = iter(self.tokenizer)
        self.next() # pre-load first token
        self.compile_file()
        self.outf.close()

    def compile_file(self) -> None:
        self.compile_class()

    def next(self) -> None:
        try:
            self.current = next(self.tokens)
        except StopIteration:
            raise CompilerError(self.current.line, 'Unexpected EOF.')

    def enter_block(self, name: str) -> None:
        self.write('<{}>'.format(name))
        self.depth += 1

    def exit_block(self, name: str) -> None:
        self.depth -=1
        if self.depth < 0:
            raise CompilerError(self.current.line, 'Closed unopened block.')
        self.write('</{}>'.format(name))

    def write(self, line: Union[str, Token]) -> None:
        if isinstance(line, Token):
            line = line.to_xml()
            self.next()
        self.outf.write(indent(line, ''.join(['  ' for i in range(0, self.depth)])) + '\n')

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

    def write_if(self, options: Union[
        TokenEnum, KeywordEnum, str, 
        Set[Union[TokenEnum, KeywordEnum, str]]
    ]) -> Token:
        if self.current_is(options):
            token = self.current
            self.write(self.current)
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
        return self.write_if(types).token
            
    def compile_class_var_dec(self) -> None:
        self.enter_block('classVarDec')
        if self.current_is(KeywordEnum.FIELD):
            var_kind = IdentEnum.FIELD
        if self.current_is(KeywordEnum.STATIC):
            var_kind = IdentEnum.STATIC
        self.write_if(self.CLASS_VAR_DEC)
        self.compile_var_list(var_kind)
        self.exit_block('classVarDec')

    def compile_var_list(self, var_kind: IdentEnum) -> int:
        tpe = self.compile_type()

        name = self.discard_if(TokenEnum.IDENTIFIER).token
        self.symbol_table.register(name, tpe, var_kind)
        count = 1
        while not self.current_is(';'):
            self.next()
            name = self.discard_if(TokenEnum.IDENTIFIER).token
            self.symbol_table.register(name, tpe, var_kind)
            count += 1
            
        self.discard_if(';')
        return count

    def compile_subroutine_dec(self) -> None:
        self.symbol_table.reset_function_scope()

        sub_kind = self.discard_if(self.SUBROUTINE_DEC)
        ret_kind = self.compile_type(True)
        sub_name = self.discard_if(TokenEnum.IDENTIFIER).token
        self.compile_parameter_list()
        self.discard_if('{')

        local_count = 0
        while not self.current_is({'}'} | self.STATEMENTS):
            local_count += self.compile_var_dec()

        if sub_kind.enum == KeywordEnum.FUNCTION:
            self.writer.w_function(
                '{}.{}'.format(self.class_name, sub_name), 
                local_count
            )
        
        self.compile_statements()
        self.discard_if('}')

    def compile_parameter_list(self) -> None:
        self.discard_if('(')
        
        while not self.current_is(')'):
            if self.current_is(','):
                self.next()
            tpe = self.compile_type()
            name = self.discard_if(TokenEnum.IDENTIFIER).token
            self.symbol_table.register(name, tpe, IdentEnum.ARG)

        self.discard_if(')')
            
    def compile_var_dec(self) -> int:
        self.discard_if(KeywordEnum.VAR)
        return self.compile_var_list(IdentEnum.VAR)
        
    def compile_statements(self) -> None:
        self.enter_block('statements')
        
        self.compile_statement()
        while self.current_is(self.STATEMENTS):
            self.compile_statement()

        self.exit_block('statements')

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
        
        if self.current_is('['):
            self.write_if('[')
            self.compile_expression()
            self.write_if(']')
            
        self.discard_if('=')
        self.compile_expression()
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
        self.compile_statements()
        self.discard_if('}')

        self.writer.w_goto('_WHILE_{}'.format(label_id))
        self.writer.w_label('_WHILE_END_{}'.format(label_id))

    def compile_do(self) -> None:
        self.discard_if(KeywordEnum.DO)
        self.compile_subroutine_call()
        self.discard_if(';')

    def compile_return(self) -> None:
        self.discard_if(KeywordEnum.RETURN)
        if self.current_is(self.TERM):
            self.compile_expression()
        self.discard_if(';')
        self.writer.w_return()

    def compile_subroutine_call(self, last: Optional[Token] = None) -> None:
        # because we need to look t+2 ahead when doing expression, we might
        # have to pass in the identifier manually
        routine_name = None
        class_name = None
        
        if last:
            call = last.token
        else:
            call = self.discard_if(TokenEnum.IDENTIFIER).token
        if self.current_is('.'):
            self.next()
            routine_name = self.discard_if(TokenEnum.IDENTIFIER).token
            call = '{}.{}'.format(call, routine_name)

        self.discard_if('(')
        args = self.compile_expression_list()
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
                self.write(last.to_xml())
                self.write(self.get_in_scope(last.token).to_xml())
                self.write_if('[')
                self.compile_expression()
                self.write_if(']')
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
        elif const.kind == TokenEnum.KEYWORD:
            if const.enum == KeywordEnum.TRUE:
                self.writer.push_const(1)
                self.writer.w_neg()
            elif const.enum in [KeywordEnum.FALSE, KeywordEnum.NULL]:
                self.writer.push_const(0)
        
from typing import Iterator, Type, List, Union, Set, Optional
from pathlib import Path
from textwrap import indent
from enum import Enum

from compile.symbol_table import SymbolTable
from compile.tokenizer import Tokenizer
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
    OP = set('+-*/&|<>=--')
    EXPR_CONST = {KeywordEnum.TRUE, KeywordEnum.FALSE, KeywordEnum.NULL, KeywordEnum.THIS, TokenEnum.INT_CONST, TokenEnum.STRING_CONST}
    TERM = {TokenEnum.IDENTIFIER} | UNARY_OP | TERM_OPEN | EXPR_CONST
    SUB_CALL = set('(.')

    def __init__(self, tokenizer: Tokenizer) -> None:
        self.tokenizer = tokenizer
    
    def write_to(self, outf: Path) -> None:
        self.outf = open(outf, 'w')
        self.depth = 0
        self.tokens = iter(self.tokenizer)
        self.next() # pre-load first token
        self.compile_file()
        self.outf.close()

    def compile_file(self) -> None:
        self.compile_class()

    def next(self) -> Token:
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

    def compile_class(self) -> None:
        self.enter_block('class')

        self.write_if(KeywordEnum.CLASS)
        self.write_if(TokenEnum.IDENTIFIER)
        self.write_if('{')

        while not self.current_is(self.SUBROUTINE_DEC | {'}'}):
            self.compile_class_var_dec()
        while not self.current_is('}'):
            self.compile_subroutine_dec()
         
        # can't iterate, will raise stop iteration
        if self.current_is('}'):
            self.write(self.current.to_xml())
        self.exit_block('class')

    def compile_type(self, function: bool = False) -> str:
        types = self.FUNCTION_TYPES if function else self.VAR_TYPES
        return self.write_if(types)
            
    def compile_class_var_dec(self) -> None:
        self.enter_block('classVarDec')
        self.write_if(self.CLASS_VAR_DEC)
        self.compile_var_list()
        self.exit_block('classVarDec')

    def compile_var_list(self) -> Token:
        self.compile_type()

        self.write_if(TokenEnum.IDENTIFIER)
        while not self.current_is(';'):
            self.write_if(',')
            self.write_if(TokenEnum.IDENTIFIER)
        self.write_if(';')

    def compile_subroutine_dec(self) -> None:
        self.enter_block('subroutineDec')
        
        self.write_if(self.SUBROUTINE_DEC)
        self.compile_type(True)
        self.write_if(TokenEnum.IDENTIFIER)
        self.compile_parameter_list()
        self.compile_subroutine_body()

        self.exit_block('subroutineDec')

    def compile_parameter_list(self) -> None:
        self.write_if('(')
        self.enter_block('parameterList')

        while not self.current_is(')'):
            if self.current_is(','):
                self.write_if(',')
            self.compile_type()
            self.write_if(TokenEnum.IDENTIFIER).token,

        self.exit_block('parameterList')
        self.write_if(')')

    def compile_subroutine_body(self) -> None:
        self.enter_block('subroutineBody')
        self.write_if('{')
        
        while not self.current_is({'}'} | self.STATEMENTS):
            self.compile_var_dec()
        self.compile_statements()
        
        self.write_if('}')
        self.exit_block('subroutineBody')

    def compile_var_dec(self) -> None:
        self.enter_block('varDec')
        
        self.write_if(KeywordEnum.VAR)
        self.compile_var_list()
        
        self.exit_block('varDec')

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
        self.enter_block('letStatement')
        
        self.write_if(KeywordEnum.LET)
        self.write_if(TokenEnum.IDENTIFIER)
        if self.current_is('['):
            self.write_if('[')
            self.compile_expression()
            self.write_if(']')
        self.write_if('=')
        self.compile_expression()
        self.write_if(';')

        self.exit_block('letStatement')

    def compile_if(self) -> None:
        self.enter_block('ifStatement')

        self.write_if(KeywordEnum.IF)
        self.write_if('(')
        self.compile_expression()
        self.write_if(')')
        self.write_if('{')
        self.compile_statements()
        self.write_if('}')

        if self.current_is(KeywordEnum.ELSE):
            self.write_if(KeywordEnum.ELSE)
            self.write_if('{')
            self.compile_statements()
            self.write_if('}')

        self.exit_block('ifStatement')

    def compile_while(self) -> None:
        self.enter_block('whileStatement')
        
        self.write_if(KeywordEnum.WHILE)
        self.write_if('(')
        self.compile_expression()
        self.write_if(')')
        self.write_if('{')
        self.compile_statements()
        self.write_if('}')

        self.exit_block('whileStatement')

    def compile_do(self) -> None:
        self.enter_block('doStatement')

        self.write_if(KeywordEnum.DO)
        self.compile_subroutine_call()
        self.write_if(';')

        self.exit_block('doStatement')

    def compile_return(self) -> None:
        self.enter_block('returnStatement')

        self.write_if(KeywordEnum.RETURN)
        if self.current_is(self.TERM):
            self.compile_expression()
        self.write_if(';')

        self.exit_block('returnStatement')

    def compile_subroutine_call(self, top: Optional[Token] = None) -> None:
        # because we need to look t+2 ahead when doing expression, we might
        # have to pass in the identifier manually
        if top:
            self.write(top.to_xml())
        else:
            self.write_if(TokenEnum.IDENTIFIER)
        while self.current_is('.'):
            self.write_if('.')
            self.write_if(TokenEnum.IDENTIFIER)
        self.write_if('(')
        self.compile_expression_list()
        self.write_if(')')

    def compile_expression_list(self) -> None:
        self.enter_block('expressionList')

        if self.current_is(self.TERM | {'('}):
            self.compile_expression()
        while self.current_is(','):
            self.write_if(',')
            self.compile_expression()

        self.exit_block('expressionList')

    def compile_expression(self) -> None:
        self.enter_block('expression')

        self.compile_term()
        while self.current_is(self.OP):
            self.write_if(self.OP)
            self.compile_term()

        self.exit_block('expression')

    def compile_term(self) -> None:
        self.enter_block('term')
        
        if self.current_is('('):
            self.write_if('(')
            self.compile_expression()
            self.write_if(')')
        elif self.current_is(self.UNARY_OP):
            self.write_if(self.UNARY_OP)
            self.compile_term()
        elif self.current_is(TokenEnum.IDENTIFIER):
            top = self.current
            self.next()
            if self.current_is(self.SUB_CALL):
                self.compile_subroutine_call(top)
            elif self.current_is('['):
                self.write(top.to_xml())
                self.write_if('[')
                self.compile_expression()
                self.write_if(']')
            else:
                self.write(top.to_xml())
        elif self.current_is(self.EXPR_CONST):
            self.write_if(self.EXPR_CONST)
        else:
            raise CompilerError(
                self.current.line,
                'Expected expression term, got {}.'.format(self.current)
            )

        self.exit_block('term')
        
from typing import Iterator, Type, List, Union, Set, Optional
from pathlib import Path
from textwrap import indent

from compile.tokenizer import Tokenizer, Token
from compile.token import *


class CompilerError(Exception):
    pass


class Compiler:
    CLASS_VAR_DEC = set([STATIC, FIELD])
    SUBROUTINE_DEC = set([CONSTRUCTOR, FUNCTION, METHOD])
    VAR_TYPES = set([INT, CHAR, BOOLEAN, IDENTIFIER])
    FUNCTION_TYPES = set([VOID]) | VAR_TYPES
    STATEMENTS = set([LET, IF, WHILE, DO, RETURN])
    UNARY_OP = set('-~')
    TERM_OPEN = set('(')
    OP = set('+-*/&|<>=--')
    EXPR_CONST = set([TRUE, FALSE, NULL, THIS, INT_CONST, STRING_CONST])
    TERM = set([IDENTIFIER]) | UNARY_OP | TERM_OPEN | EXPR_CONST
    SUB_CALL = set(['(', '.'])

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
            raise CompilerError('Unexpected EOF.')

    def enter_block(self, name: str) -> None:
        self.write('<{}>'.format(name))
        self.depth += 1

    def exit_block(self, name: str) -> None:
        self.depth -=1
        if self.depth < 0:
            raise CompilerError('Closed unopened block.')
        self.write('</{}>'.format(name))

    def write(self, line: Union[str, Token]) -> None:
        if isinstance(line, Token):
            line = line.to_xml()
            self.next()
        self.outf.write(indent(line, ''.join(['  ' for i in range(0, self.depth)])) + '\n')

    def verify_is(self, things: Union[int, str, Set[Union[int, str]]]) -> None:
        def to_string(thing: Union[str, int]) -> str:
            if isinstance(thing, int):
                return CONST_NAME_MAP[const]
            else:
                return thing

        if not isinstance(things, set):
            things = [things]
            
        if self.current in things or self.current.token in things:
            self.write(self.current)
        else:
            raise CompilerError('Expected {}, got {} instead.'.format(
                '|'.join([to_string(thing) for thing in things]),
                self.current.token
            ))

    def compile_class(self) -> None:
        self.enter_block('class')

        self.verify_is(CLASS)
        self.verify_is(IDENTIFIER)
        self.verify_is('{')

        while self.current != '}' and self.current not in self.SUBROUTINE_DEC:
            self.compile_class_var_dec()
        while self.current != '}':
            self.compile_subroutine_dec()
         
        # can't iterate, will raise stop iteration
        if self.current == '}':
            self.write(self.current.to_xml())
        self.exit_block('class')

    def compile_type(self, function: bool = False) -> None:
        types = self.FUNCTION_TYPES if function else self.VAR_TYPES
        self.verify_is(types)
            
    def compile_class_var_dec(self) -> None:
        self.enter_block('classVarDec')
        self.verify_is(self.CLASS_VAR_DEC)
        self.compile_var_list()
        self.exit_block('classVarDec')

    def compile_var_list(self) -> Token:
        self.compile_type()

        while self.current != ';':
            if self.current == ',':
                self.verify_is(',')
            self.verify_is(IDENTIFIER)
        self.verify_is(';')

    def compile_subroutine_dec(self) -> None:
        self.enter_block('subroutineDec')
        
        self.verify_is(self.SUBROUTINE_DEC)
        self.compile_type(True)
        self.verify_is(IDENTIFIER)
        self.compile_parameter_list()
        self.compile_subroutine_body()

        self.exit_block('subroutineDec')

    def compile_parameter_list(self) -> None:
        self.verify_is('(')
        self.enter_block('parameterList')

        while self.current != ')':
            if self.current == ',':
                self.verify_is(',')
            self.compile_type()
            self.verify_is(IDENTIFIER)

        self.exit_block('parameterList')
        self.verify_is(')')

    def compile_subroutine_body(self) -> None:
        self.enter_block('subroutineBody')
        self.verify_is('{')
        
        while self.current != '}' and self.current not in self.STATEMENTS:
            self.compile_var_dec()
        self.compile_statements()
        
        self.verify_is('}')
        self.exit_block('subroutineBody')

    def compile_var_dec(self) -> None:
        self.enter_block('varDec')
        
        self.verify_is(VAR)
        self.compile_var_list()
        
        self.exit_block('varDec')

    def compile_statements(self) -> None:
        self.enter_block('statements')
        
        self.compile_statement()
        while self.current in self.STATEMENTS:
            self.compile_statement()

        self.exit_block('statements')

    def compile_statement(self) -> None:
        if self.current == LET:
            self.compile_let()
        elif self.current == IF:
            self.compile_if()
        elif self.current == WHILE:
            self.compile_while()
        elif self.current == DO:
            self.compile_do()
        elif self.current == RETURN:
            self.compile_return()
        else:
            raise CompilerError('Expected let|if|while|do|return, got {} instead.'.format(self.current))
            
    def compile_let(self) -> None:
        self.enter_block('letStatement')
        
        self.verify_is(LET)
        self.verify_is(IDENTIFIER)
        if self.current == '[':
            self.verify_is('[')
            self.compile_expression()
            self.verify_is(']')
        self.verify_is('=')
        self.compile_expression()
        self.verify_is(';')

        self.exit_block('letStatement')

    def compile_if(self) -> None:
        self.enter_block('ifStatement')

        self.verify_is(IF)
        self.verify_is('(')
        self.compile_expression()
        self.verify_is(')')
        self.verify_is('{')
        self.compile_statements()
        self.verify_is('}')

        if self.current == ELSE:
            self.verify_is(ELSE)
            self.verify_is('{')
            self.compile_statements()
            self.verify_is('}')

        self.exit_block('ifStatement')

    def compile_while(self) -> None:
        self.enter_block('whileStatement')
        
        self.verify_is(WHILE)
        self.verify_is('(')
        self.compile_expression()
        self.verify_is(')')
        self.verify_is('{')
        self.compile_statements()
        self.verify_is('}')

        self.exit_block('whileStatement')

    def compile_do(self) -> None:
        self.enter_block('doStatement')

        self.verify_is(DO)
        self.compile_subroutine_call()
        self.verify_is(';')

        self.exit_block('doStatement')

    def compile_return(self) -> None:
        self.enter_block('returnStatement')

        self.verify_is(RETURN)
        if self.current in self.TERM:
            self.compile_expression()
        self.verify_is(';')

        self.exit_block('returnStatement')

    def compile_subroutine_call(self, top: Optional[Token] = None) -> None:
        # because we need to look t+2 ahead when doing expression, we might
        # have to pass in the identifier manually
        if top:
            self.write(top.to_xml())
        else:
            self.verify_is(IDENTIFIER)
        while self.current == '.':
            self.verify_is('.')
            self.verify_is(IDENTIFIER)
        self.verify_is('(')
        self.compile_expression_list()
        self.verify_is(')')

    def compile_expression_list(self) -> None:
        self.enter_block('expressionList')

        if self.current in self.TERM or self.current == '(':
            self.compile_expression()
        while self.current == ',':
            self.verify_is(',')
            self.compile_expression()

        self.exit_block('expressionList')

    def compile_expression(self) -> None:
        self.enter_block('expression')

        self.compile_term()
        while self.current.token in self.OP:
            self.verify_is(self.OP)
            self.compile_term()

        self.exit_block('expression')

    def compile_term(self) -> None:
        self.enter_block('term')
        
        if self.current == '(':
            self.verify_is('(')
            self.compile_expression()
            self.verify_is(')')
        elif self.current.token in self.UNARY_OP:
            self.verify_is(self.UNARY_OP)
            self.compile_term()
        elif self.current == IDENTIFIER:
            top = self.current
            self.next()
            if self.current.token in self.SUB_CALL:
                self.compile_subroutine_call(top)
            elif self.current.token == '[':
                self.write(top.to_xml())
                self.verify_is('[')
                self.compile_expression()
                self.verify_is(']')
            else:
                self.write(top.to_xml())
        elif self.current in self.EXPR_CONST:
            self.verify_is(self.EXPR_CONST)
        else:
            raise CompilerError('Expected expression term, got {}.'.format(self.current))

        self.exit_block('term')
        
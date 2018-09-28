import re
from pathlib import Path

from translator.parser import Parser
from translator.commands import COMMANDS, Context, Call


class Writer:
    def __init__(self, parser: Parser) -> None:
        self.parser = parser

    def clean_asm(self, asm: str) -> str:
        return '\n'.join([s for s in asm.replace(' ', '').splitlines() if s])

    def init_asm(self) -> str:
        return '''
            @256
            D=A
            @SP
            M=D
        '''

    def init_section(self) -> str:
        constants = ''.join([c('').constant() for c in COMMANDS.values()])
        return '''
            {}
            {}
            {}
        '''.format(
                self.init_asm(), 
                Call('call Sys.init 0').to_asm(Context('', '')), 
                constants
            )

    def write_to(self, path: Path) -> None:
        f = open(path, 'w')
        context = Context('', '')
        f.write(self.clean_asm(self.init_section()) + '\n')
        for file, command in self.parser:
            context.file = file
            f.write(self.clean_asm(command.to_asm(context)) + '\n')
        f.close()

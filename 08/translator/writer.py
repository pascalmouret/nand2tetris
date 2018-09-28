import re
from pathlib import Path

from translator.parser import Parser
from translator.commands import COMMANDS


class Writer:
    def __init__(self, parser: Parser):
        self.parser = parser

    def clean_asm(self, asm: str) -> str:
        return re.sub(r'( )|(^\n)', '', asm)

    def init_section(self):
        constants = ''.join([self.clean_asm(c.constant('')) for c in COMMANDS.values()])
        const_len = constants.count('\n') - constants.count('(') + 2
        return '''
            @{}
            0;JMP
            {}'''.format(const_len, constants)

    def write_to(self, path: Path) -> None:
        f = open(path, 'w')
        f.write(self.init_section())
        for command in self.parser:
            f.write(self.clean_asm(command.to_asm()))
        f.close()

from assembler.parser import Parser
from assembler.symbols import SymbolTable
from assembler.expressions import Label


DEFAULT_SYMBOLS = {
    'SP': 0,
    'LCL': 1,
    'ARG': 2,
    'THIS': 3,
    'THAT': 4,
    'R0': 0,
    'R1': 1,
    'R2': 2,
    'R3': 3,
    'R4': 4,
    'R5': 5,
    'R6': 6,
    'R7': 7,
    'R8': 8,
    'R9': 9,
    'R10': 10,
    'R11': 11,
    'R12': 12,
    'R13': 13,
    'R14': 14,
    'R15': 15,
    'SCREEN': 16384,
    'KBD': 24576
}


def create_table(parser: Parser) -> SymbolTable:
    table = SymbolTable(DEFAULT_SYMBOLS)
    line = 0
    for expr in parser:
        if isinstance(expr, Label):
            table.add_label(expr.get_label(), line)
        else:
            line += 1
    return table

def assemble(inf: str, outf: str) -> None:
    parser = Parser(inf)
    symbols = create_table(parser)
    f = open(outf, 'w')
    for expr in parser:
        out = expr.translate(symbols)
        if out:
            f.write(out + '\n')


if __name__ == '__main__':
    import sys
    infile = sys.argv[1]
    outfile = infile[:-4] + '.hack'
    assemble(infile, outfile)
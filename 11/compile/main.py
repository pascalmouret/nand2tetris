from pathlib import Path

from compile.tokenizer import Tokenizer
from compile.compiler import Compiler, CompilerError


def compile(path: Path) -> None:
    files = []
    if path.is_dir():
        files = path.glob('*.jack')
        if not files:
            raise ValueError('No .jack files found in directory.')
    else:
        if path.parts[-1].endswith('.jack'):
            files = [path]
        else:
            raise ValueError('Not a .jack file.')
        
    for file in files:
        try:
            compile_file(file)
        except CompilerError as e:
            print('Error in {}:'.format(file))
            print('    {}'.format(e))
            print('\033[91mCompilation failed.')
            return
    print('\033[92mCompilation done.')

def compile_file(path: Path):
    out_path = path.parent / path.parts[-1].replace('.jack', '.vm')
    tokenizer = Tokenizer(path)
    compiler = Compiler(tokenizer).write_to(out_path)


if __name__ == '__main__':
    import sys
    compile(Path(sys.argv[1]))

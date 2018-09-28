from pathlib import Path

from translator.writer import Writer
from translator.parser import load


def translate(path: Path):
    writer = Writer(load(path))
    if path.is_dir():
        out_path = path / '{}.asm'.format(path.parts[-1])
    else:
        out_path = path.parent / '{}.asm'.format(path.parts[-1].replace('.vm', ''))
    writer.write_to(out_path)


if __name__ == '__main__':
    import sys
    translate(Path(sys.argv[1]))

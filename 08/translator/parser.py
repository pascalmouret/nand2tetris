import re
import abc
from pathlib import Path
from typing import Iterator, Tuple

from translator.commands import Command, parse_command


class Parser(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __iter__(self) -> Iterator[Tuple[str, Command]]: ...


class FileParser(Parser):
    def __init__(self, fin: Path) -> None:
        self.path = fin
        self.name = fin.parts[-1].split('.')[0]

    def __iter__(self) -> Iterator[Tuple[str, Command]]:
        self.f = open(self.path)
        self.f.seek(0)
        return self

    def __next__(self) -> Tuple[str, Command]:
        for line in self.f:
            trimmed = self.trim_line(line)
            if trimmed != '':
                return (self.name, parse_command(trimmed))
        self.f.close()
        raise StopIteration

    def trim_line(self, line: str) -> str:
        return re.sub(r'(^\s*)|(\s*$)', '', re.sub(r'(//.*)', '', line))


class DirectoryParser(Parser):
    def __init__(self, din: Path) -> None:
        self.dir = din

    def __iter__(self) -> Iterator[Tuple[str, Command]]:
        self.source_iter = iter(self.dir.glob('*.vm'))
        self.current = iter(FileParser(self.source_iter.__next__()));
        return self

    def __next__(self) -> Tuple[str, Command]:
        try:
            return self.current.__next__()
        except StopIteration:
            self.current = iter(FileParser(self.source_iter.__next__()));
            return self.__next__()
         

def load(path: Path) -> Parser:
    if path.is_dir():
        return DirectoryParser(path)
    elif path.parts[-1].endswith('.vm'):
        return FileParser(path)
    else:
        raise ValueError('{} is neither directory or vm file.'.format(path))
    
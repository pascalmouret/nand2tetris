from enum import Enum
from typing import Dict, Optional

from compile.syntax import IdentEnum


class Symbol:
    def __init__(self, kind: IdentEnum, tpe: str, index: int) -> None:
        self.kind = kind
        self.index = index
        self.tpe = tpe

    def to_xml(self, declared: bool = False) -> str:
        return '<identDesc kind="{}" type="{}" index="{}" declared="{}" />'.format(
            self.kind, self.tpe, self.index, declared
        )

class SymbolTable:
    _CLASS_LEVEL = {IdentEnum.STATIC, IdentEnum.FIELD}
    _FUNC_LEVEL = {IdentEnum.ARG, IdentEnum.VAR}

    def __init__(self) -> None:
        self._class_scope = {}
        self._counts = {
            IdentEnum.STATIC: 0,
            IdentEnum.FIELD: 0,
            IdentEnum.ARG: 0,
            IdentEnum.VAR: 0
        }
        self.reset_function_scope()

    def reset_function_scope(self):
        self._function_scope = {}
        self._counts[IdentEnum.ARG] = 0
        self._counts[IdentEnum.VAR] = 0

    def register(self, name: str, tpe: str, kind: IdentEnum) -> Symbol:
        if kind in self._CLASS_LEVEL:
            return self._register_in_scope(name, tpe, kind, self._class_scope)
        else:
            return self._register_in_scope(name, tpe, kind, self._function_scope)

    def find(self, name: str) -> Optional[Symbol]:
        if name in self._function_scope:
            return self._function_scope[name]
        elif name in self._class_scope:
            return self._class_scope[name]
        else:
            return None

    def _register_in_scope(
        self, 
        name: str,
        tpe: str,
        kind: IdentEnum, 
        scope: Dict[str, Symbol]
    ) -> Symbol:
        symbol = Symbol(kind, tpe, self._counts[kind])
        scope[name] = symbol
        self._counts[kind] += 1
        return symbol
            


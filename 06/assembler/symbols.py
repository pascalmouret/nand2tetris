from typing import Dict, Optional

class SymbolTable():
    def __init__(self, defaults: Dict[str, int]) -> None:
        self.next_variable = 16
        self.table = defaults

    def address_for_symbol(self, symbol: str) -> int:
        if symbol not in self.table:
            self.table[symbol] = self.next_variable
            self.next_variable += 1
        return self.table[symbol]

    def add_label(self, label: str, address: int) -> None:
        self.table[label] = address
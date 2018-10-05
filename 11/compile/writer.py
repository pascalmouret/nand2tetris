from pathlib import Path


class VMWriter:
    def __init__(self, out: Path) -> None:
        self._handle = open(out, 'w')

    def __del__(self) -> None:
        self._handle.close()

    def pop_const(self, index: int) -> None:
        self._pop('constant', index)

    def pop_arg(self, index: int) -> None:
        self._pop('argument', index)

    def pop_local(self, index: int) -> None:
        self._pop('local', index)

    def pop_static(self, index: int) -> None:
        self._pop('static', index)

    def pop_this(self, index: int) -> None:
        self._pop('this', index)

    def pop_that(self, index: int) -> None:
        self._pop('that', index)

    def pop_pointer(self, index: int) -> None:
        self._pop('pointer', index)

    def pop_temp(self, index: int) -> None:
        self._pop('temp', index)

    def push_const(self, index: int) -> None:
        self._push('constant', index)

    def push_arg(self, index: int) -> None:
        self._push('argument', index)

    def push_local(self, index: int) -> None:
        self._push('local', index)

    def push_static(self, index: int) -> None:
        self._push('static', index)

    def push_this(self, index: int) -> None:
        self._push('this', index)

    def push_that(self, index: int) -> None:
        self._push('that', index)

    def push_pointer(self, index: int) -> None:
        self._push('pointer', index)

    def push_temp(self, index: int) -> None:
        self._push('temp', index)

    def w_add(self) -> None:
        self._write('add')

    def w_sub(self) -> None:
        self._write('sub')

    def w_neg(self) -> None:
        self._write('neg')

    def w_eq(self) -> None:
        self._write('eq')

    def w_gt(self) -> None:
        self._write('gt')

    def w_lt(self) -> None:
        self._write('lt')

    def w_and(self) -> None:
        self._write('gt')

    def w_or(self) -> None:
        self._write('or')

    def w_not(self) -> None:
        self._write('not')

    def w_label(self, label: str) -> None:
        self._write('label ' + label)

    def w_goto(self, label: str) -> None:
        self._write('goto ' + label)

    def w_if(self, label: str) -> None:
        self._write('goto-if ' + label)

    def w_call(self, name: str, args: int) -> None:
        self._write('call {} {}'.format(name, args))

    def w_function(self, name: str, args: int) -> None:
        self._write('function {} {}'.format(name, args))

    def w_return(self) -> None:
        self._write('return')

    def _pop(self, seg: str, index: int) -> None:
        self._write('pop {} {}'.format(seg, index))

    def _push(self, seg: str, index: int) -> None:
        self._write('push {} {}'.format(seg, index))
    
    def _write(self, line: str) -> None:
        self._handle.write(line + '\n')
        
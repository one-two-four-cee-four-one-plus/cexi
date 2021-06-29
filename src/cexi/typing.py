from types import SimpleNamespace
from enum import Enum

t = SimpleNamespace(
    # basic
    bool='_Bool',
    char='char',
    byte='char',
    wchar='wchar_t',
    short='short',
    int='int',
    size='size_t',
    ssize='ssize_t',
    float='float',
    double='double',
    void='void',
    # long
    long='long',
    longlong='long long',
    ldouble='long double',
    # unsigned
    ubyte='unsigned char',
    ushort='unsigned short',
    uint='unsigned int',
    ulong='unsigned long',
    ulonglong='unsigned long long',
    # py
    py='PyObject*',
    none='Py_None'
)

PY_FUNC, CEE_FUNC, CEE_EXPR = 0, 1, 2


class ArgsFlag(Enum):
    pass


class Mapping:
    def __init__(self, prefix=None, suffix=None):
        self.prefix = prefix
        self.suffix = suffix

    def __getitem__(self, name):
        if not self.suffix:
            return f'{self.prefix} {name}'
        elif not self.prefix:
            return f'{name} {self.suffix}'
        else:
            return f'{self.prefix} {name} {self.suffix}'


P = Mapping(suffix='*')
PP = Mapping(suffix='**')
C = Mapping(prefix='const')
CP = Mapping(suffix='*const')
P2C = Mapping(prefix='const', suffix='*')

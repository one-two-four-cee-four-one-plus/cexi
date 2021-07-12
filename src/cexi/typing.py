from enum import Enum
from inspect import Signature


empty = Signature.empty


class Literal:
    def __init__(self, name):
        self.name = name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Literal):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        else:
            raise TypeError(f'cannot compare Literal to {type(other)}')


class TypeTable:
    table = tuple((  # table of (python, cexi, cee, format) name combinations

        # basic
        (bool,                    'bool',       '_Bool',                'p'),
        (chr,                     'char',       'char',                 'c'),
        (str,                     'str',        'char *',               's'),
        (Literal('byte'),         'byte',       'char',                 None),
        (Literal('short'),        'short',      'short',                'h'),
        (int,                     'int',        'int',                  'i'),
        (Literal('size_t'),       'size',       'size_t',               None),
        (Literal('ssize_t'),      'ssize',      'ssize_t',              None),
        (Literal('py_size'),      'psize',      'Py_ssize_t',           'n'),
        (float,                   'float',      'float',                'f'),
        (Literal('double'),       'double',     'double',               'd'),
        (complex,                 'complex',    'Py_complex',           'D'),
        (Literal('void'),         'void',       'void',                 None),

        # long
        (Literal('long'),         'long',       'long',                 'l'),
        (Literal('long long'),    'longlong',   'long long',            'L'),
        (Literal('long double'),  'ldouble',    'long double',          None),

        # unsigned
        (Literal('u8'),           'ubyte',      'unsigned char',        'b',),
        (Literal('u16'),          'ushort',     'unsigned short',       'H'),
        (Literal('u32'),          'uint',       'unsigned int',         'I'),
        (Literal('u64'),          'ulong',      'unsigned long',        'k'),
        (Literal('u128'),         'ulonglong',  'unsigned long long',   'K'),

        # py
        (bytes,                   'bytes',      'PyBytesObject *',      'S'),
        (bin,                     'bin',        'Py_buffer',            'y*'),
        (bytearray,               'bytearray',  'PyByteArrayObject *',  'Y'),
        (object,                  'py',         'PyObject*',            'O'),
        (empty,                   'py',         'PyObject*',            'O'),
        (None,                    'none',       'Py_None',              None)
    ))

    py_to_cee = {row[0]: row[2] for row in table}
    py_to_format = {row[0]: row[3] for row in table if row[3]}


class ArgsFlag(Enum):
    pass


class Mapping:
    def __init__(self, prefix=None, suffix=None):
        self.prefix = prefix
        self.suffix = suffix

    def map(self, name):
        if not self.suffix:
            return f"{self.prefix} {name}"
        elif not self.prefix:
            return f"{name} {self.suffix}"
        else:
            return f"{self.prefix} {name} {self.suffix}"


P = Mapping(suffix="*")
PP = Mapping(suffix="**")
C = Mapping(prefix="const")
CP = Mapping(suffix="*const")
P2C = Mapping(prefix="const", suffix="*")

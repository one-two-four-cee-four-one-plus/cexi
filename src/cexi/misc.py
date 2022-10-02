from itertools import product
from operator import itemgetter
from string import ascii_lowercase
from collections import OrderedDict
from uuid import uuid4

from .typing import TypeTable
from . import templates


def _generate_names(count, exclude):
    prefixes = ['', *list(ascii_lowercase)]
    for prefix, name in product(prefixes, ascii_lowercase):
        value = f'{prefix}{name}'
        if value in exclude:
            continue
        yield value


def generate_names(count, exclude):
    names = _generate_names(count, exclude)
    return [next(names) for _ in range(count)]


def gensym(prefix='cexi', suffix=''):
    if prefix:
        prefix = f'{prefix}_'
    if suffix:
        suffix = f'_{suffix}'
    infix = str(uuid4()).replace("-", "")
    return f'{prefix}{infix}{suffix}'


def ensure_tuple(f):
    def closure(*args, **kwargs):
        ret = f(*args, **kwargs)
        return ret if isinstance(ret, tuple) else (ret,)
    return closure


ESCAPE_SEQ_MAP = {
    '\n': '\\n',
}


def escape(content):
    if isinstance(content, str):
        content = ''.join(ESCAPE_SEQ_MAP.get(c, c) for c in content)
    return content


def mapping(d):
    @staticmethod
    def func(v):
        ret = itemgetter(*v)(d) if v else tuple()
        if isinstance(ret, str):
            return (ret,)
        return ret
    return func


def zip_decl(types, names, delim=', '):
    return delim.join(f'{t} {n}' for t, n in zip(types, names))


def uses(decos):
    decos = reversed(decos)

    def outer(f):
        def inner(*args, **kwargs):
            return f(*args, **kwargs)
        return inner

    for deco in decos:
        outer = deco.use(outer)

    return outer


class Unpack:
    map = mapping(TypeTable.py_to_cee)
    format = mapping(TypeTable.py_to_format)

    def __init__(self, **kwargs):
        self.mapping = OrderedDict(kwargs.items())

    def translate(self, name):
        types = self.map(self.mapping.values())
        names = self.mapping.keys()
        decl = zip_decl(types, names, delim='; ')
        format = ''.join(self.format(self.mapping.values()))
        names = ', '.join(f'&{n}' for n in names)
        return templates.UNPACK.substitute(
            decl=f'{decl};',
            name=name,
            names=names,
            format=format
        )


to = Unpack

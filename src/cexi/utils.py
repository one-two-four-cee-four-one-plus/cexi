from itertools import product
from operator import itemgetter
from string import ascii_lowercase


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


def ensure_tuple(f):
    def closure(*args, **kwargs):
        ret = f(*args, **kwargs)
        return ret if isinstance(ret, tuple) else (ret,)
    return closure


def mapping(d):
    @staticmethod
    def func(v):
        ret = itemgetter(*v)(d)
        if isinstance(ret, str):
            return (ret,)
        return ret
    return func


def zip_decl(types, names):
    return ', '.join(f'{t} {n}' for t, n in zip(types, names))


def uses(decos):
    decos = reversed(decos)

    def outer(f):
        def inner(*args, **kwargs):
            return f(*args, **kwargs)
        return inner

    for deco in decos:
        outer = deco.use(outer)

    return outer

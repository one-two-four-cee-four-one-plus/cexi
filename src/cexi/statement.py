from functools import cached_property
from inspect import signature, Signature
from collections import OrderedDict

from . import proxy
from . import templates
from .misc import generate_names, mapping, zip_decl, Unpack, escape
from .typing import TypeTable, P


empty = Signature.empty


class CodeTemplate:
    template = None

    def get_context():
        raise NotImplementedError()

    def translate(self):
        return self.template.substitute(self.get_context())


class CodeBlock(CodeTemplate):
    def __init__(self, obj, module):
        self.obj = obj
        self.module = module

    def translate(self):
        if self.template:
            return self.template.substitute(**self.get_context()).strip()
        return self.obj.strip()

    @cached_property
    def body(self):
        return self.obj.__doc__.strip()


class CeeCallable(CodeBlock):
    template = templates.CEE_FUNCTION
    map = mapping(TypeTable.py_to_cee)

    def __init__(self, obj, module):
        super().__init__(obj, module)
        self.signature = signature(self.obj)
        self.returns = self.signature.return_annotation
        if isinstance(self.returns, str):
            self.returns = (self.returns,)
        else:
            try:
                self.returns = tuple(self.returns)
            except TypeError:
                self.returns = (self.returns,)

        self.params = OrderedDict(
            (k, v.annotation) for k, v in self.signature.parameters.items()
        )
        self.name = self.obj.__name__

    def get_context(self):
        names = self.params.keys()
        types = self.map(self.params.values())
        return dict(
            return_type=self.map(self.returns)[0],
            name=self.name,
            parameters=', '.join(f'{t} {n}' for t, n in zip(types, names)),
            body=self.body
        )


class Unpack(CodeTemplate):
    template = templates.UNPACK

    map = mapping(TypeTable.py_to_cee)
    format = mapping(TypeTable.py_to_format)

    def __init__(self, name, **kwargs):
        self.name = name
        self.mapping = OrderedDict(kwargs.items())

    def get_context(self):
        types = self.map(self.mapping.values())
        names = self.mapping.keys()
        decl = zip_decl(types, names, delim='; ')
        format = ''.join(self.format(self.mapping.values()))
        names = ', '.join(f'&{n}' for n in names)
        return dict(
            decl=f'{decl};',
            name=self.name,
            names=names,
            format=format
        )


class Pack(CodeTemplate):
    template = templates.PACK

    format = mapping(TypeTable.py_to_format)

    def __init__(self, name, **kwargs):
        self.name = name
        self.mapping = OrderedDict(kwargs.items())

    def get_context(self):
        names = self.mapping.keys()
        format = ''.join(self.format(self.mapping.values()))
        names = ', '.join(str(n) for n in names)
        return dict(
            name=self.name,
            names=names,
            format=format
        )


class PyCallable(CeeCallable):
    def __init__(self, *args, doc=None, flags=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__doc = doc
        self.__flags = flags

    @cached_property
    def template(self):
        if len(self.returns) == 1:
            return templates.EXT_FUNCTION1
        else:
            return templates.EXT_FUNCTION_MULTI

    @cached_property
    def doc(self):
        return "NULL" if self.__doc is None else f'"{self.__doc}"'

    @cached_property
    def flags(self):
        return "METH_VARARGS"

    @cached_property
    def table_entry(self):
        return f'{{"{self.name}", {self.name}, {self.flags}, {self.doc}}}'

    def proxy(self):
        return proxy.Proxy(self.module, self)

    def get_context(self):
        if len(self.returns) == 1:
            return self.get_context1()
        else:
            return self.get_context_multi()

    def get_context1(self):
        map = mapping(TypeTable.py_to_cee)
        unpack = Unpack('args', **self.params)
        pack = Pack('ret', **{f'__folded_{self.name}_result': self.returns[0]})
        return dict(
            return_type=self.map(self.returns)[0],
            name=self.name,
            unpack=unpack.translate(),
            pack=pack.translate(),
            body=self.body,
            ret='ret'
        )

    def get_context_multi(self):
        unpack = Unpack('args', **self.params)
        pack = Pack('args', **self.params)
        unpack_ctx = unpack.get_context()
        pack_ctx = pack.get_context()
        names = self.params.keys()
        types = self.map(self.params.values())
        ret = dict(
            name=self.name,
            unpack=unpack.translate(),
            body=self.body,
            format=unpack_ctx['format'],
            names=pack_ctx['names'],
            decl=', '.join(' '.join(pair) for pair in zip(types, names))
        )
        return ret

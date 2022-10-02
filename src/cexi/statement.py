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


class Capture(PyCallable):
    template = templates.CAPTURE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.orig = self.name
        self.name = self.capture = f"__capture_{self.orig}" f"_from_{self.module.name}"
        self.captured = f"__captured_{self.orig}_from_{self.module.name}"

    def get_context(self):
        return dict(
            decl=f"static PyObject* __captured_{self.orig}_from_{self.module.name} = NULL;",
            name=self.name,
            capture=self.captured,
        )


class Share(CeeCallable):
    prefix = ""
    format = mapping(TypeTable.py_to_format)

    def __init__(self, obj, module, capture):
        super().__init__(obj, module)
        self.capture = capture

    @cached_property
    def template(self):
        if self.params:
            return templates.SHARE
        else:
            return templates.SHARE_NO_ARGS

    def get_context(self):
        in_types, out_types = self.map(self.params.values()), self.map(self.returns)
        in_names, out_names = self.params.keys(), generate_names(
            len(self.returns), self.params.keys()
        )
        out_types = tuple(P.map(t) for t in out_types)
        in_format = "".join(self.format(self.params.values()))
        out_format = "".join(self.format(self.returns))
        return dict(
            name=self.name,
            in_decl=zip_decl(in_types, in_names),
            out_decl=zip_decl(out_types, out_names),
            capture=self.capture.captured,
            in_format=in_format,
            in_params=", ".join(in_names),
            out_format=out_format,
            out_params=", ".join(out_names),
        )

    def proxy(self):
        return proxy.ReverseProxy(self.module, self.obj, self.capture)

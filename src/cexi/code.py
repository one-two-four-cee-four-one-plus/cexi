from functools import cached_property
from inspect import signature, Signature
from collections import OrderedDict

from . import binding
from . import templates
from .utils import generate_names, mapping, zip_decl, Unpack
from .typing import TypeTable, P


empty = Signature.empty


class CodeTemplate:
    template = None

    def get_context():
        raise NotImplementedError()

    def translate(self):
        raise NotImplementedError()


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
    prefix = ""
    template = templates.FUNCTION
    default_return = int
    map = mapping(TypeTable.py_to_cee)

    def __init__(self, obj, module):
        super().__init__(obj, module)
        self.signature = signature(self.obj)
        self.returns = self.signature.return_annotation
        if isinstance(self.returns, str):
            self.returns = [self.returns]
        else:
            try:
                self.returns = tuple(self.returns)
            except TypeError:
                self.returns = (self.returns,)

        if len(self.returns) == 1 and self.returns[0] is empty:
            self.returns = [self.default_return]

        self.params = OrderedDict(
            (k, v.annotation) for k, v in self.signature.parameters.items()
        )
        self.name = self.obj.__name__

    def get_context(self):
        assert len(self.returns) == 1
        types = self.map(self.params.values())
        names = self.params.keys()
        return dict(
            prefix=self.prefix,
            return_type=self.map(self.returns)[0],
            name=self.name,
            parameters=zip_decl(types, names),
            body=self.body,
        )


class PyCallable(CeeCallable):
    prefix = "static"
    default_return = object

    def __init__(self, *args, doc=None, flags=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__doc = doc
        self.__flags = flags

    @cached_property
    def doc(self):
        return "NULL" if self.__doc is None else f'"{self.__doc}"'

    @cached_property
    def flags(self):
        return "METH_VARARGS"

    @cached_property
    def table_entry(self):
        return f'{{"{self.name}", {self.name}, {self.flags}, {self.doc}}}'

    def binding(self):
        return binding.Binding(self.module, self)


class UnpackedPyCallable(PyCallable):
    def get_context(self):
        assert len(self.returns) == 1
        types = []
        prefix = ''
        for name, type in self.params.items():
            if isinstance(type, Unpack):
                prefix += type.translate(name)
                types.append(object)
            else:
                types.append(type)
        types = self.map(types)
        names = self.params.keys()
        return dict(
            prefix=self.prefix,
            return_type=self.map(self.returns)[0],
            name=self.name,
            parameters=zip_decl(types, names),
            body=(prefix + '\n    ' + self.body).strip(),
        )


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


class Reverse(CeeCallable):
    prefix = ""
    template = templates.REVERSE
    format = mapping(TypeTable.py_to_format)

    def __init__(self, obj, module, capture):
        super().__init__(obj, module)
        self.capture = capture

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

    def binding(self):
        return binding.ReverseBinding(self.module, self.obj, self.capture)

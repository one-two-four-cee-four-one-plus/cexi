from textwrap import indent, dedent
from inspect import signature, _empty
from functools import wraps, cached_property
from pathlib import Path
from importlib import import_module

from . import templates
from .typing import PY_FUNC, CEE_FUNC, CEE_EXPR
from .exceptions import CodeDiverged
from .constants import TAB


class Binding:
    def __init__(self, module, obj):
        self.module = module
        self.obj = obj

    def __getattribute__(self, attr):
        if attr == 'cee_name':
            return object.__getattribute__(self, 'obj').name
        return Binding.get_attr(self, attr)

    def __call__(self, *args, **kwargs):
        return Binding.get_attr(self, '__call__')(*args, **kwargs)

    @staticmethod
    def get_attr(binding, attr):
        try:
            module_name = object.__getattribute__(binding, 'module').name
            module = import_module(module_name)
            member_name = object.__getattribute__(binding, 'obj').name
            obj = getattr(module, member_name)
            return object.__getattribute__(obj, attr)
        except AttributeError:
            msg = f'for "{member_name}" function from "{module_name}"'
            raise CodeDiverged(msg) from None


class ExtObject:
    def __init__(self, obj, module, type=None, doc=None, flags=None):
        self.obj = obj
        self.module = module
        self.type = type
        self.__doc = doc
        self.__flags = flags

    @cached_property
    def signature(self):
        return signature(self.obj)

    @cached_property
    def parameters(self):
        parameters = [
            f'{parameter.annotation} {name}'
            for name, parameter in self.signature.parameters.items()
        ]
        return ', '.join(parameters)

    @cached_property
    def return_type(self):
        if (rt := self.signature.return_annotation) is _empty:
            return 'void'
        return rt

    @cached_property
    def name(self):
        return self.obj.__name__

    @cached_property
    def body(self):
        return self.obj.__doc__.strip()

    @cached_property
    def table_entry(self):
        return f'{{"{self.name}", {self.name}, {self.flags}, {self.doc}}}'

    @cached_property
    def prefix(self):
        return 'static' if self.type == PY_FUNC else ''

    @cached_property
    def doc(self):
        return 'NULL' if self.__doc is None else f'"{self.__doc}"'

    @cached_property
    def flags(self):
        return 'METH_VARARGS'

    def evaluate_callable(self):
        return templates.FUNCTION.substitute(
            prefix=self.prefix,
            return_type=self.return_type,
            name=self.name,
            parameters=self.parameters,
            body=self.body
        ).lstrip()

    def evaluate(self):
        if self.type in (PY_FUNC, CEE_FUNC):
            return self.evaluate_callable()
        return self.obj


class Ext:
    def __init__(self, name, flags=None):
        self.name = name
        self.code = []

    #################
    # names section #
    #################

    @cached_property
    def __capitalized(self):
        return self.name.capitalize()

    @cached_property
    def __error_name(self):
        return f'{self.__capitalized}Error'

    @cached_property
    def __method_table_name(self):
        return f'{self.__capitalized}Methods'

    @cached_property
    def __module_name(self):
        return f'{self.name}module'

    ###############
    # API section #
    ###############

    def __call__(self, obj, *args, ):
        self.code.append(ExtObject(obj, self))

    def py(self, obj=None, doc=None, flags=None):
        def closure(obj):
            obj = ExtObject(obj, self, type=PY_FUNC, doc=doc, flags=flags)
            self.code.append(obj)
            return Binding(self, obj)
        if callable(obj):
            return closure(obj)
        return closure

    def cee(self, obj):
        obj = ExtObject(obj, self, type=CEE_FUNC)
        self.code.append(obj)

    def prepare(self, obj):
        ...

    ###########################
    # code generation section #
    ###########################

    @cached_property
    def __mandatory_header(self):
        return templates.MANDATORY_HEADER

    @cached_property
    def __module_code(self):
        return '\n\n\n'.join(code.evaluate().strip() for code in self.code)

    @cached_property
    def __method_table(self):
        methods = ',\n'.join(
            obj.table_entry for obj in self.code
            if obj.type == PY_FUNC
        )
        methods = indent(methods, TAB).lstrip()
        return templates.METHOD_TABLE.substitute(
            name=self.__method_table_name,
            methods=methods
        )

    @cached_property
    def __module_definition(self):
        return templates.MODULE_DEFINITION.substitute(
            module=self.__module_name,
            name=self.name,
            method_table=self.__method_table_name
        )

    @cached_property
    def __module_init(self):
        return templates.MODULE_INIT.substitute(
            name=self.name,
            module=self.__module_name
        )

    @cached_property
    def __code(self):
        return templates.MODULE_CODE.substitute(
            header=self.__mandatory_header,
            code=self.__module_code,
            method_table=self.__method_table,
            module_definition=self.__module_definition,
            module_init=self.__module_init
        )

    #######################
    # integration section #
    #######################

    def __source_path(self, to_dir=None):
        path = Path(to_dir)
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        path /= f'{self.name}module'
        return path.with_suffix('.c')

    def as_extension(self, src_dir):
        from distutils.core import Extension
        path = self.__source_path(to_dir=src_dir)
        with open(path, 'wt') as fd:
            fd.write(self.__code)
        return Extension(self.name, sources=[str(path)])

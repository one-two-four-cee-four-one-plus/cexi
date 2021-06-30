from functools import cached_property
from textwrap import indent
from importlib import import_module
from pathlib import Path

from . import templates
from . import code
from .constants import TAB


class Ext:
    def __init__(self, name, flags=None):
        self.name = name
        self.code = []
        self.__capitalized = self.name.capitalize()
        self.__error_name = f"{self.__capitalized}Error"
        self.__method_table_name = f"{self.__capitalized}Methods"
        self.__module_name = f"{self.name}module"

    ###############
    # API section #
    ###############

    @cached_property
    def error(self):
        module = import_module(self.name)
        return module.error

    def block(self, obj):
        self.code.append(code.CodeBlock(obj, self))

    def py(self, obj=None, doc=None, flags=None):
        def closure(obj):
            obj = code.PyCallable(obj, self, doc=doc, flags=flags)
            self.code.append(obj)
            return obj.binding()

        if callable(obj):
            return closure(obj)
        return closure

    def cee(self, obj):
        obj = code.CeeCallable(obj, self)
        self.code.append(obj)

    def pyc(self, obj):
        capture = code.Capture(obj, self)
        reverse = code.Reverse(obj, self, capture)
        self.code.append(capture)
        self.code.append(reverse)
        return reverse.binding()

    ###########################
    # code generation section #
    ###########################

    @cached_property
    def __mandatory_header(self):
        return templates.MANDATORY_HEADER

    @cached_property
    def __error_definition(self):
        return templates.ERROR.substitute(error=self.__error_name)

    @cached_property
    def __module_code(self):
        return "\n\n\n".join(code.translate() for code in self.code)

    @cached_property
    def __method_table(self):
        methods = ",\n".join(
            obj.table_entry for obj in self.code
            if isinstance(obj, code.PyCallable)
        )
        methods = indent(methods, TAB).lstrip()
        return templates.METHOD_TABLE.substitute(
            name=self.__method_table_name, methods=methods
        )

    @cached_property
    def __module_definition(self):
        return templates.MODULE_DEFINITION.substitute(
            module=self.__module_name,
            name=self.name,
            method_table=self.__method_table_name,
        )

    @cached_property
    def __module_init(self):
        return templates.MODULE_INIT.substitute(
            name=self.name, module=self.__module_name, error=self.__error_name
        )

    @cached_property
    def __code(self):
        return templates.MODULE_CODE.substitute(
            header=self.__mandatory_header,
            error=self.__error_definition,
            code=self.__module_code,
            method_table=self.__method_table,
            module_definition=self.__module_definition,
            module_init=self.__module_init,
        )

    #######################
    # integration section #
    #######################

    @cached_property
    def __revision(self):
        return hash(self.__code)

    def __source_path(self, to_dir=None):
        path = Path(to_dir)
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        path /= f"{self.name}module"
        return path.with_suffix(".c")

    def as_extension(self, src_dir):
        from distutils.core import Extension

        path = self.__source_path(to_dir=src_dir)
        with open(path, "wt") as fd:
            fd.write(self.__code)
        return Extension(self.name, sources=[str(path)])

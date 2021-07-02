from functools import cached_property
from textwrap import indent
from importlib import import_module
from pathlib import Path


from tempfile import TemporaryDirectory
from sys import platform
from os import name
from distutils.ccompiler import get_default_compiler
from importlib.machinery import ExtensionFileLoader
from sysconfig import get_config_var


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
        self.__module = None
        self.__customize_cc = None

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

    def custom_compile(self, cc_func):
        self.__customize_cc = cc_func
        return cc_func

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

    def oneshot(self):
        if self.__module:
            return self

        with TemporaryDirectory() as tempo:
            path = Path(tempo) / self.name
            with path.with_suffix(".c").open(mode="wt") as fd:

                fd.write(self.__code)
                fd.flush()

                assert get_default_compiler(name, platform) == "unix"
                from distutils.unixccompiler import UnixCCompiler

                extra_preargs = ["-fPIC"]
                extra_postargs = []

                cc = UnixCCompiler()
                cc.add_include_dir(get_config_var("INCLUDEPY"))

                if self.__customize_cc:
                    self.__customize_cc(cc, extra_preargs, extra_postargs)

                os = cc.compile(
                    [fd.name],
                    extra_preargs=extra_preargs,
                    extra_postargs=extra_postargs,
                    output_dir=tempo,
                )
                cc.link_shared_lib(os, self.name, output_dir=tempo)
                libfile = cc.library_filename(
                    self.name, lib_type="shared", output_dir=tempo
                )
                loader = ExtensionFileLoader(self.name, libfile)
                self.__module = loader.load_module()
                return self

    def __enter__(self):
        self.oneshot()

    def __exit__(self, *args):
        return False

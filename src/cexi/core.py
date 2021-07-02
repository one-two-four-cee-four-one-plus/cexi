from functools import cached_property
from textwrap import indent
from importlib import import_module
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager
from distutils.core import setup, Extension as _Extension
from inspect import signature

from tempfile import TemporaryDirectory
from sys import platform
from os import name
from distutils.ccompiler import get_default_compiler
from importlib.machinery import ExtensionFileLoader
from sysconfig import get_config_var

from . import templates
from . import wrap
from .constants import TAB
from .utils import Unpack


class Extension:
    def __init__(self, name=None, *, flags=None):
        self.name_set = bool(name)
        if self.name_set:
            self.name = name
        else:
            self.name = f'cexi_{str(uuid4()).replace("-", "")}'
        self.code = []
        self.reverses = []
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
    def exception(self):
        module = import_module(self.name)
        return module.error

    def block(self, code_block):
        self.code.append(wrap.CodeBlock(code_block, self))

    def py(self, fun):
        params = signature(fun).parameters.values()
        if any(isinstance(p.annotation, Unpack) for p in params):
            cexi_fun = wrap.UnpackedPyCallable(fun, self)
        else:
            cexi_fun = wrap.PyCallable(fun, self)
        self.code.append(cexi_fun)
        return cexi_fun.proxy()

    def cee(self, fun):
        cexi_fun = wrap.CeeCallable(fun, self)
        self.code.append(cexi_fun)

    def pyc(self, fun):
        capture = wrap.Capture(fun, self)
        reverse = wrap.Reverse(fun, self, capture)
        self.code.append(capture)
        self.code.append(reverse)
        proxy = reverse.proxy()
        self.reverses.append(proxy)
        return proxy

    def compile_with(self, cc_func):
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
        return "\n\n\n".join(wrap.translate() for wrap in self.code)

    @cached_property
    def __method_table(self):
        methods = ",\n".join(
            obj.table_entry for obj in self.code
            if isinstance(obj, wrap.PyCallable)
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

    def ensure(self):
        if self.__module:
            return self

        with TemporaryDirectory() as tempo:
            path = (Path(tempo) / self.name).with_suffix(".c")
            with path.open(mode="wt") as fd:

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
                for reverse in self.reverses:
                    reverse.use()

    @property
    @contextmanager
    def ensured(self):
        yield self.ensure()

    def setup(self):
        assert self.name_set
        with TemporaryDirectory() as tempo:
            path = (Path(tempo) / self.name).with_suffix(".c")
            with path.open(mode="wt") as fd:

                fd.write(self.__code)
                fd.flush()

                return setup(
                    name=f'cexi_{self.name}_pkg',
                    ext_modules=[_Extension(self.name, sources=[fd.name])]
                )

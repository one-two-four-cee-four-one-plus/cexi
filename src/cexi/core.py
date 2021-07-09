from functools import cached_property
from textwrap import indent
from importlib import import_module
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager
from distutils.core import setup, Extension as _Extension
from tempfile import TemporaryDirectory
from sys import platform
from os import name
from distutils.ccompiler import get_default_compiler
from importlib.machinery import ExtensionFileLoader
from sysconfig import get_config_var
from multiprocessing import Queue, Process, Event
from pathlib import Path
from queue import Empty

from . import templates
from . import wrap
from .constants import TAB
from .exceptions import TooLate, BackgroundCompileError
from .proxy import DynamicProxy


class Extension:
    def __init__(self, name=None, *, make=None, flags=None, version=None):
        self.name = f'cexi_{str(uuid4()).replace("-", "")}'
        self.code = []
        self.reverses = []
        self.__capitalized = self.name.capitalize()
        self.__error_name = f"{self.__capitalized}Error"
        self.__method_table_name = f"{self.__capitalized}Methods"
        self.__module_name = f"{self.name}module"
        self._module = None
        self.__customize_cc = make

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

    def make(self, cc_func):
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
    def _code(self):
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
    def cc(self):
        assert get_default_compiler(name, platform) == "unix"
        from distutils.unixccompiler import UnixCCompiler
        return UnixCCompiler()

    def compile(self, fd, tempo):
        fd.write(self._code)
        fd.flush()

        self.cc.add_include_dir(get_config_var("INCLUDEPY"))

        extra_preargs = ["-fPIC"]
        extra_postargs = []

        if self.__customize_cc:
            self.__customize_cc(self.cc, extra_preargs, extra_postargs)

        os = self.cc.compile(
            [fd.name],
            extra_preargs=extra_preargs,
            extra_postargs=extra_postargs,
            output_dir=tempo,
        )
        self.cc.link_shared_lib(os, self.name, output_dir=tempo)

    def load(self, tempo):
        libfile = self.cc.library_filename(
            self.name, lib_type="shared", output_dir=tempo
        )
        loader = ExtensionFileLoader(self.name, libfile)
        self._module = loader.load_module()
        for reverse in self.reverses:
            reverse.use()

    def ensure(self):
        if self._module:
            return self

        with TemporaryDirectory() as tempo:
            path = (Path(tempo) / self.name).with_suffix(".c")
            with path.open(mode="wt") as fd:
                self.compile(fd, tempo)
                self.load(tempo)

    @property
    @contextmanager
    def ensured(self):
        yield self.ensure()


class SetupExtension(Extension):
    def __init__(self, name, version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.version = version

    def setup(self):
        with TemporaryDirectory() as tempo:
            path = (Path(tempo) / self.name).with_suffix(".c")
            with path.open(mode="wt") as fd:

                fd.write(self._code)
                fd.flush()

                return setup(
                    name=f'cexi_{self.name}_pkg',
                    version=self.version,
                    ext_modules=[_Extension(self.name, sources=[fd.name])]
                )


class DynamicExtension(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__event = None
        self.__queue = None
        self.__worker = False
        self.__default_set = False
        self.__cee_impl_set = False

    def define(self, fun):
        if self.__default_set:
            raise TooLate()
        proxy = DynamicProxy(self, fun)
        self.__default_set = True
        return proxy

    def _py(self, fun, name):
        if self.__cee_impl_set:
            raise TooLate()
        fun.__name__ = name
        proxy = super().py(fun)
        self.__cee_impl_set = True
        self.__spawn()
        return proxy

    def __background(self):
        with TemporaryDirectory() as tempo:
            path = (Path(tempo) / self.name).with_suffix(".c")
            with path.open(mode="wt") as fd:
                self.compile(fd, tempo)
                self.__queue.put_nowait(tempo)
                self.__event.wait()

    def __spawn(self):
        if self.__worker:
            return
        self.__worker = Process(target=self.__background, daemon=True)
        self.__queue = Queue(1)
        self.__event = Event()
        self.__worker.start()

    def _check(self):
        if self._module:
            return True

        if not self.__worker:
            return False
        elif self.__worker and self.__worker.exitcode not in (0, None):
            raise BackgroundCompileError() from None

        try:
            tempo = self.__queue.get_nowait()
            self.load(tempo)
            self.__event.set()
            return True
        except Empty:
            return False

        return False


class IncrementalExtension(Extension):
    pass

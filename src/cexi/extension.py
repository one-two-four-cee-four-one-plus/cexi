from uuid import uuid4
from pathlib import Path
from textwrap import indent
from functools import cached_property, partial
from tempfile import NamedTemporaryFile, TemporaryDirectory
from hashlib import blake2b

from .constants import TAB, ALLOWED_CHARACTERS
from .exceptions import IncorrectExtensionName
from . import templates
from . import statement
from .binary import Compiler, Loader


class Extension:
    def __init__(self, name: str, dir=None, options=None):
        if set(name) - ALLOWED_CHARACTERS:
            raise IncorrectExtensionName(name)

        self.name = name
        if dir:
            self.dir = Path(dir).absolute()
            self.dir.mkdir(parents=True, exist_ok=True)
        else:
            self.dir = TemporaryDirectory()
        self.options = options
        self.code = []
        self.shared = []

        self.__capitalized = self.name.capitalize()
        self.__error_name = f"{self.__capitalized}Error"
        self.__method_table_name = f"{self.__capitalized}Methods"
        self.__module_name = f"{self.name}module"

        self.module = None

    #######
    # API #
    #######

    @cached_property
    def exception(self):
        module = import_module(self.name)
        return module.error

    def block(self, code_block):
        self.code.append(statement.CodeBlock(code_block, self))

    def cee(self, fun):
        cexi_fun = statement.CeeCallable(fun, self)
        self.code.append(cexi_fun)
        return cexi_fun

    def py(self, fun):
        cexi_fun = statement.PyCallable(fun, self)
        self.code.append(cexi_fun)
        return cexi_fun.proxy()

    def share(self, fun):
        fun, orig = partial(fun, None), fun
        fun.__name__ = orig.__name__
        capture = statement.Capture(fun, self)
        reverse = statement.Share(fun, self, capture)
        self.code.append(capture)
        self.code.append(reverse)
        proxy = reverse.proxy()
        self.shared.append(proxy)
        return fun

    ###########
    # codegen #
    ###########

    def get_revision(self, source=None):
        h = blake2b(digest_size=7)
        h.update((source or self._code_without_revision).encode())
        return abs(int(h.hexdigest(), 16))

    @cached_property
    def __mandatory_header(self):
        return templates.MANDATORY_HEADER

    @cached_property
    def __error_definition(self):
        return templates.ERROR.substitute(error=self.__error_name)

    @cached_property
    def __module_code(self):
        return "\n\n\n".join(statement.translate() for statement in self.code)

    @cached_property
    def __method_table(self):
        methods = (",\n".join(
            obj.table_entry for obj in self.code
            if isinstance(obj, statement.PyCallable)
        ) + ",\n    ") if self.code else ""
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

    def __module_init(self):
        return templates.MODULE_INIT.substitute(
            name=self.name, module=self.__module_name, error=self.__error_name
        )

    def __module_init_with_revision(self, source):
        return templates.MODULE_INIT_WITH_REVISION.substitute(
            name=self.name, module=self.__module_name, error=self.__error_name,
            revision=self.get_revision(source)
        )

    @cached_property
    def _code_without_revision(self):
        return templates.MODULE_CODE.substitute(
            header=self.__mandatory_header,
            error=self.__error_definition,
            code=self.__module_code,
            method_table=self.__method_table,
            module_definition=self.__module_definition,
            module_init=self.__module_init(),
        )

    @cached_property
    def _code(self):
        return templates.MODULE_CODE.substitute(
            header=self.__mandatory_header,
            error=self.__error_definition,
            code=self.__module_code,
            method_table=self.__method_table,
            module_definition=self.__module_definition,
            module_init=self.__module_init_with_revision(source=self._code_without_revision),
        )

    #########################
    # compilation & loading #
    #########################

    def compile(self):
        dir = Path(self.dir.name) if isinstance(self.dir, TemporaryDirectory) else self.dir
        with NamedTemporaryFile(dir=dir, mode='wt', suffix='.c') as source:
            Compiler().compile_cexi_extension(self, source, dir)

    def load_shared(self):
        for fun in self.shared:
            fun._cexi_capture_callback()

    def load(self):
        dir = Path(self.dir.name) if isinstance(self.dir, TemporaryDirectory) else self.dir
        self.module = Loader().load_cexi_extension(self, dir)
        if isinstance(self.dir, TemporaryDirectory):
            self.dir.cleanup()
        self.load_shared()

    def is_recompilation_required(self):
        return self.module.cexi_revision != self.get_revision() if self.module else self.is_compilation_required()

    def prepare(self):
        if self.module:
            return

        try:
            self.load()
        except ImportError:
            self.compile()
            self.load()
        else:
            if self.is_recompilation_required():
                self.compile()
                self.load()

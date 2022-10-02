from pathlib import Path
from os import environ, path, chdir
from sysconfig import get_config_var
from distutils.unixccompiler import UnixCCompiler
from tempfile import TemporaryFile
from importlib.machinery import ExtensionFileLoader
from contextlib import contextmanager


class Compiler(UnixCCompiler):
    def compile_cexi_extension(self, extension, source_file, directory):
        source_file.write(extension._code)
        source_file.flush()

        self.add_include_dir(get_config_var("INCLUDEPY"))

        extra_preargs = ["-fPIC"]
        extra_postargs = []

        if options := extension.options:
            if flags := options.get('flags'):
                extra_preargs.extend(flags)

        origin = Path().absolute()
        try:
            chdir(directory)
            files = self.compile(
                [Path(source_file.name).name],
                extra_preargs=extra_preargs,
                extra_postargs=extra_postargs,
            )
            self.link_shared_lib(files, path.join(directory, extension.name))
        finally:
            chdir(origin)


class Loader:
    def load_cexi_extension(self, extension, directory):
        cc = Compiler()
        libfile = cc.library_filename(
            extension.name, lib_type="shared"
        )
        loader = ExtensionFileLoader(extension.name, path.join(directory, libfile))
        module = loader.load_module()
        return module

import argparse
from tempfile import TemporaryDirectory
from importlib import import_module

parser = argparse.ArgumentParser(description='Cee EXtensions Interpolation')
parser.add_argument('path', type=str, nargs=1, help='Path to module in format <path>:<module>')
args = parser.parse_args()

path, name = args.path[0].split(':')
cexi_extension = getattr(import_module(path), name)
try:
    dir = cexi_extension.dir
    module = cexi_extension
except AttributeError:
    dir = cexi_extension.cexi_module.dir
    module = cexi_extension.cexi_module

if isinstance(dir, TemporaryDirectory):
    raise Exception("Module isn't persistent")
else:
    module.compile()

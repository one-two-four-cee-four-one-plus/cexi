from importlib import import_module

from .exceptions import CodeDiverged
from .utils import ensure_tuple


class Binding:
    def __init__(self, module, obj):
        self.module = module
        self.obj = obj

    def __getattribute__(self, attr):
        return Binding.get_attr(self, attr)

    def __call__(self, *args, **kwargs):
        return Binding.get_attr(self, "__call__")(*args, **kwargs)

    @staticmethod
    def get_attr(binding, attr):
        try:
            module_name = object.__getattribute__(binding, "module").name
            module = import_module(module_name)
            msg = f"error importing {module_name}"
            member_name = object.__getattribute__(binding, "obj").name
            obj = getattr(module, member_name)
            return object.__getattribute__(obj, attr)
        except AttributeError:
            msg = f'for "{member_name}" function from "{module_name}"'
            raise CodeDiverged(msg) from None
        except ImportError:
            pass


class ReverseBinding:
    def __init__(self, module, obj, capture):
        self.__module = module
        self.__obj = obj
        self.__capture = capture
        self.__captured = False

    def __call__(self, *args, **kwargs):
        obj = object.__getattribute__(self, "_ReverseBinding__obj")
        return obj(*args, **kwargs)

    def __getattribute__(self, attr):
        if attr == 'use' and not object.__getattribute__(self, "_ReverseBinding__captured"):
            def closure():
                obj = object.__getattribute__(self, "_ReverseBinding__obj")
                capture = object.__getattribute__(self, "_ReverseBinding__capture")
                module = import_module(capture.module.name)
                getattr(module, capture.capture)(ensure_tuple(obj))
                setattr(self, "_ReverseBinding__captured", True)
            return closure
        return object.__getattribute__(self, attr)

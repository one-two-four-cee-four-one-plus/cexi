from importlib import import_module

from .exceptions import CodeDiverged, NotInitialized
from .misc import ensure_tuple


class Proxy:
    def __init__(self, module, object):
        self.__module = module
        self.__object = object
        self.o = object

    def __getattribute__(self, attr):
        try:
            module_name = object.__getattribute__(self, "_Proxy__module").name
            module = import_module(module_name)
        except ImportError:
            raise NotInitialized(module_name) from None
        try:
            member_name = object.__getattribute__(self, "_Proxy__object").name
            obj = getattr(module, member_name)
            return object.__getattribute__(obj, attr)
        except AttributeError:
            raise CodeDiverged(module_name, member_name, attr) from None

    def __call__(self, *args, **kwargs):
        return self.__getattribute__("__call__")(*args, **kwargs)


class ReverseProxy:
    def __init__(self, module, object, capture):
        self.__module = module
        self.__object = object
        self.__capture = capture
        self.__captured = False

    def __call__(self, *args, **kwargs):
        obj = object.__getattribute__(self, "_ReverseProxy__object")
        return obj(*args, **kwargs)

    def __getattribute__(self, attr):
        if attr == "use":

            def closure():
                if object.__getattribute__(self, "_ReverseProxy__captured"):
                    return
                obj = object.__getattribute__(self, "_ReverseProxy__object")
                capture = object.__getattribute__(self, "_ReverseProxy__capture")
                module = import_module(capture.module.name)
                getattr(module, capture.capture)(ensure_tuple(obj))
                self.__captured = True

            return closure
        return object.__getattribute__(self, attr)


class DynamicProxy:
    def __init__(self, module, object):
        self.__module = module
        self.__object = object
        self.__replacement = None

    def __getattribute__(self, attr):
        if attr == "cee":
            py = object.__getattribute__(self, "_DynamicProxy__module")._py
            fun = object.__getattribute__(self, "_DynamicProxy__object")

            def closure(func):
                return py(func, fun.__name__)

            return closure

        replacement = object.__getattribute__(self, "_DynamicProxy__replacement")
        if replacement:
            return getattr(replacement, attr)

        module = object.__getattribute__(self, "_DynamicProxy__module")
        fun = object.__getattribute__(self, "_DynamicProxy__object")

        if module._check():
            module = import_module(module.name)
            self.__replacement = getattr(module, fun.__name__)
            return self.__getattribute__(attr)

        return getattr(fun, attr)

    def __call__(self, *args, **kwargs):
        return self.__getattribute__("__call__")(*args, **kwargs)

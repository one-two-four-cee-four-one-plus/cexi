from importlib import import_module

from .exceptions import CodeDiverged, NotInitialized
from .misc import ensure_tuple


class Proxy:
    def __init__(self, module, object):
        self.__module = module
        self.__object = object
        self.o = object

    def __getattribute__(self, attr):
        module = object.__getattribute__(self, "_Proxy__module").module
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

    def __call__(self, *args, **kwargs):
        obj = object.__getattribute__(self, "_ReverseProxy__object")
        return obj(*args, **kwargs)

    def __getattribute__(self, attr):
        if attr == "_cexi_capture_callback":

            def closure():
                obj = object.__getattribute__(self, "_ReverseProxy__object")
                capture = object.__getattribute__(self, "_ReverseProxy__capture")
                module = capture.module.module
                getattr(module, capture.capture)(ensure_tuple(obj))
            return closure

        return object.__getattribute__(self, attr)

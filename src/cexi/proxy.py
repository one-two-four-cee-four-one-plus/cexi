from importlib import import_module

from .exceptions import CodeDiverged, NotInitialized
from .utils import ensure_tuple


class Proxy:
    def __init__(self, module, object):
        self.__module = module
        self.__object = object

    def __getattribute__(self, attr):
        return Proxy.get_attr(self, attr)

    def __call__(self, *args, **kwargs):
        return Proxy.get_attr(self, "__call__")(*args, **kwargs)

    @staticmethod
    def get_attr(proxy, attr):
        try:
            module_name = object.__getattribute__(proxy, "_Proxy__module").name
            module = import_module(module_name)
        except ImportError:
            msg = f"module {module} not compiled/loaded"
            raise NotInitialized(msg)
        try:
            member_name = object.__getattribute__(proxy, "_Proxy__object").name
            obj = getattr(module, member_name)
            return object.__getattribute__(obj, attr)
        except AttributeError:
            msg = (
                f'for "{member_name}" from "{module_name}", failed to retrieve "{attr}"'
            )
            raise CodeDiverged(msg) from None


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
                setattr(self, "_ReverseProxy__captured", True)

            return closure
        return object.__getattribute__(self, attr)

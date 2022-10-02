from pathlib import Path

from .extension import Extension


class Signature:
    def py(self, obj):
        obj._cexi_sig = 'py'
        return obj

    def cee(self, obj):
        obj._cexi_sig = 'cee'
        return obj

    def share(self, obj):
        obj._cexi_sig = 'share'
        return obj

    def process(self, ext, attrs):
        for k, obj in attrs.copy().items():

            if sig := getattr(obj, '_cexi_sig', None):
                delattr(obj, '_cexi_sig')
                if sig == 'py':
                    attrs[k] = ext.py(obj)
                elif sig == 'cee':
                    ext.cee(obj)
                    attrs.pop(k)
                elif sig == 'share':
                    ext.share(obj)


s = Signature()


class CexiMeta(type):
    def __new__(mcls, name, bases, attrs, near=None):
        if attrs.get('__module__') != 'cexi.core':
            if near:
                directory = Path(near).parent / f'{name.lower()}_cexi_module'
            else:
                directory = attrs.pop('directory', None)
            options = attrs['options'].__dict__ if 'options' in attrs else None
            module = Extension(name, dir=directory, options=options)
            if doc := attrs.pop('__doc__', None):
                module.block(doc)
            s.process(module, attrs)
            attrs['cexi_module'] = module
        return super().__new__(mcls, name, bases, attrs)


class Module(metaclass=CexiMeta):
    directory = None

    def __init__(self):
        self.cexi_module.prepare()

# Cee EXtensions Interpolation


### Rationale
cexi aims to facilitate developing of [C extension](https://docs.python.org/3/extending/extending.html) for [CPython](https://github.com/python/cpython). In particular interfacing between python and C. In general building C extensions is a tedious process, especially when it comes to interfacing between two languages. cexi aims to make it easier by providing a simple interface to write C extensions in a pythonic way. It's not a replacement for [Cython](https://cython.org/), [CFFI](https://cffi.readthedocs.io/en/latest/), [SWIG](http://www.swig.org/), [Boost.Python](https://www.boost.org/doc/libs/1_75_0/libs/python/doc/html/index.html) or [PyBind11](https://pybind11.readthedocs.io/en/stable/), but rather a tool to make writing C extensions easier. It's main features are:
- pythonic interface to write C extensions
- automatic re/compilation of C extensions
- automatic loading of C extensions


### Code example
```python
from cexi import Module, s

class Foo(Module):

    class options:
        flags = ['-O3']

    """
    #include "stdio.h"
    """

    @s.cee
    def foo(x: int) -> int:
        """
        return x + 1;
        """

    @s.share
    def bar(self, x: int) -> int:
        return x ** 2

    @s.py
    def baz(x: int, y: int) -> (int, int):
        """
        printf("baz\\n");
        int ret = x + y;
        bar(ret, &ret);
        return(foo(x + y), ret);
        """

    def wrapped_baz(self, x, y):
        print(f'calling {self.baz}')
        return self.baz(x, y)

Foo().foo(1)  # => 2
ret = Foo().wrapped_baz(3, 4) # => prints
                              # calling <cexi.proxy.Proxy object at 0x7f4bae56cf10>
                              # baz

print(ret)  # => prints (8, 49)


class Foo(Module, near=__file__):
    pass


class Foo(Module):
    directory = Path('/some/path')
```

### Breakdown

Each extension begins with a class definition that inherits from `cexi.Module`. User can define flags
that will be passed to compiler via `options` class attribute.
```python
class Foo(Module):

    class options:
        flags = ['-O3']
```

Module docstring is directly inserted at the beginning of cee extension. It's useful to include headers
that will be used in extension's code.
```python
class Foo(Module):
    """
    #include "stdio.h"
    """
```

Then user can define functions that will be compiled as extension's functions. There are three types of functions:
- `@s.cee` - plain cee function, it's useful to organize plain cee routines. `.cee` functions aren't available for use in python, they're simply excluded from final class namespace
- `@s.share` -  .share is a plain python function that is added to module to be used in cee code it's signature is transformed as such:
    `func([input parameters]) -> <output parameters>`
    =>
    `int func([input parameters], [pointers to output parameters])`
e.g. bar here becomes `int bar(int x, int *a)`, it returns non-zero value on failure & modify pointer to the return value
- `@s.py` - .py is a cee extension function. it's available from python & can use both .cee & .share functions at will
Untagged functions are left untouched, i.e. they're just instance's methods.
cexi.Module children act as singletones - on instantiation they're get loaded/compiled by default they are built inside temporaty directories, but users are able to make modules persistent. There are two ways to do it:
- `near` parameter - if it's set to `__file__` module will be built in directory at `__file__/../<module name>_cexi_module`
- `directory` class attribute - if it's set module will be built in specified directory

Persistent extensions compiled on-demand. If extension is persistent cexi first loads it's module.
Then it compares revisions, which are hashed module's contents. Thus if class definition is changed
since last compilation it will be re-compiled and re-loaded.

You can also compile persistent extensions with command
```bash
python -mcexi <module path>:<class name>
```

### Installation
```bash
pip install cexi
```

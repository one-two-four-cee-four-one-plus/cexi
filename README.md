# Cee EXtensions Interpolation

cexi aims to facilitate developing of [C extension](https://docs.python.org/3/extending/extending.html) for [CPython](https://github.com/python/cpython)
main goal is to allow one to mix python an C code within single file

currently lib is WIP, unstable, undocumented & not nearly polished and
not extensively, yet you can enjoy some fancy examples below


### SPAM!

```python
# mimicking https://docs.python.org/3/extending/extending.html#a-simple-example

from cexi import Extension, to

spam = Extension('spam')


@spam.unpacked
def spam_system(self, args: to(command=str)):
    '''
    int sts = system(command);
    return PyLong_FromLong(sts);
    '''


system = spam_system
spam.oneshot()  # compilation happens here

assert system('true') == 0
assert system('false') != 1

assert issubclass(spam.error, Exception)
```


will generate following C code

```C
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject* SpamError;

static PyObject*
spam_system(PyObject* self, PyObject* args)
{
    char * command;
    if (!PyArg_ParseTuple(args, "s", &command)) {
        return NULL;
    };
    int sts = system(command);
    return PyLong_FromLong(sts);
}


static PyMethodDef SpamMethods[] = {
    {"spam_system", spam_system, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef spammodule = {
    PyModuleDef_HEAD_INIT,
    "spam",
    NULL,
    -1,
    SpamMethods
};

PyMODINIT_FUNC
PyInit_spam(void)
{
    PyObject* spam;
    spam = PyModule_Create(&spammodule);
    SpamError = PyErr_NewException("spam.error", NULL, NULL);
    Py_XINCREF(SpamError);
    if (PyModule_AddObject(spam, "error", SpamError) < 0) {
        Py_XDECREF(SpamError);
        Py_CLEAR(SpamError);
        Py_DECREF(spam);
        return NULL;
    };

    PyObject* cexi_code_revision = Py_BuildValue("s", CEXI_CODE_REVISION);
    Py_XINCREF(cexi_code_revision);
    if (PyModule_AddObject(spam, "cexi_code_revision", cexi_code_revision) < 0) {
        Py_XDECREF(cexi_code_revision);
        Py_CLEAR(cexi_code_revision);
        Py_DECREF(spam);
        return NULL;
    };
    return spam;
};
```


### pure C functions in extensions functions

```python
from cexi import Extension

mix = Extension()  # name will be generated automatically


@mix.cee
def add(a: int, b: int):  # pure C function, return type defaults to int
    'return a + b;'


@mix.py
def add2(self, args):  # default C ext function, default types (object, object) -> object
    '''
    int right = 0, ret = 0;
    PyObject* ret_obj = NULL;

    if (!PyArg_ParseTuple(args, "i", &right))
        return NULL;

    ret = add(2, right);

    ret_obj = Py_BuildValue("i", ret);
    Py_INCREF(ret_obj);
    return ret_obj;
    '''


with mix:  # compile & load extension if needed
    assert 4 == add2(2)
```


### using python functions in c extension functions

```python
from cexi import Extension, to, uses

mix = Extension()


@mix.pyc
def add(a: int, b: int) -> int:
    return a + b


@mix.pyc
def add_and_mul(a: int, b: int) -> (int, int):
    return (a + b, a * b)


@mix.unpacked
def test(self, args: to(left=int, right=int)):
    '''
    int r1 = 0, r2 = 0, r3 = 0; // results
    add(left, right, &r1);
    add_and_mul(left, right, &r2, &r3);
    PyObject* result = Py_BuildValue("iii", r1, r2, r3);
    Py_XINCREF(result);
    return result;
    '''


with mix:
    assert (5, 5, 6) == test(2, 3) == (add(2, 3), *add_and_mul(2, 3))
```
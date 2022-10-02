from string import Template


def template(text):
    return Template(text.strip())


MANDATORY_HEADER = """
#define PY_SSIZE_T_CLEAN
#include <Python.h>
""".strip()


ERROR = template("static PyObject* ${error};")

UNPACK = template(
    """
    ${decl}
    PyArg_ParseTuple(${name}, "${format}", ${names});
"""
)

PACK = template(
    """
    ${name} = Py_BuildValue("${format}", ${names});
"""
)

CEE_FUNCTION = template(
    """
${return_type}
${name}(${parameters})
{
    ${body}
}
"""
)

EXT_FUNCTION1 = template(
    """
${return_type}
__folded_${name}(PyObject *module, PyObject *args)
{
    ${unpack}
    ${body}
}

static PyObject *
${name}(PyObject *module, PyObject *args)
{
    ${return_type} __folded_${name}_result = __folded_${name}(module, args);
    PyObject * ${ret};
    ${pack}
    Py_INCREF(${ret});
    return ${ret};
}
""")


EXT_FUNCTION_MULTI = template(
    """
#define return(...) return ${name}_result(__VA_ARGS__)

static PyObject *
${name}_result(${decl}) {
    return Py_BuildValue("${format}", $names);
}

static PyObject *
${name}(PyObject *module, PyObject *args)
{
    ${unpack}
    ${body}
}
#undef return
""")


METHOD_TABLE = template(
    """
static PyMethodDef ${name}[] = {
    ${methods}{NULL, NULL, 0, NULL}
};
"""
)


MODULE_DEFINITION = template(
    """
static struct PyModuleDef $module = {
    PyModuleDef_HEAD_INIT,
    "${name}",
    NULL,
    -1,
    ${method_table}
};
"""
)

MODULE_INIT = template(
    """
PyMODINIT_FUNC
PyInit_${name}(void)
{
    PyObject* ${name};
    $name = PyModule_Create(&${module});

    $error = PyErr_NewException("${name}.error", NULL, NULL);
    Py_XINCREF(${error});
    if (PyModule_AddObject(${name}, "error", ${error}) < 0) {
        Py_XDECREF(${error});
        Py_CLEAR(${error});
        Py_DECREF(${name});
        return NULL;
    };

    return ${name};
};
"""
)

MODULE_INIT_WITH_REVISION = template(
    """
PyMODINIT_FUNC
PyInit_${name}(void)
{
    PyObject* ${name};
    $name = PyModule_Create(&${module});

    $error = PyErr_NewException("${name}.error", NULL, NULL);
    Py_XINCREF(${error});
    if (PyModule_AddObject(${name}, "error", ${error}) < 0) {
        Py_XDECREF(${error});
        Py_CLEAR(${error});
        Py_DECREF(${name});
        return NULL;
    };

    PyObject * revision = PyLong_FromLong(${revision});
    Py_XINCREF(revision);
    if (PyModule_AddObject(${name}, "cexi_revision", revision) < 0) {
        Py_XDECREF(revision);
        Py_CLEAR(revision);
        Py_DECREF(${name});
        return NULL;
    };

    return ${name};
};
"""
)

CAPTURE = template(
    """
${decl}
static PyObject*
${name}(PyObject *__whatever, PyObject *args)
{
    if (${capture}) {
        Py_INCREF(Py_None);
        return Py_None;
    };
    PyObject* temp;
    if (!PyArg_ParseTuple(args, "O:set_callback", &temp)) {
        PyErr_SetString(PyExc_ImportError, "cannot capture python function");
        return NULL;
    }
    if (!PyCallable_Check(temp)) {
        PyErr_SetString(PyExc_TypeError, "parameter must be callable");
        return NULL;
    };
    Py_XINCREF(temp);
    ${capture} = temp;
    Py_INCREF(Py_None);
    return Py_None;
};
"""
)

SHARE = template(
    """
int
${name}(${in_decl}, ${out_decl}) {
    if (!${capture})
        return 1;
    PyObject *result = NULL;
    if (!(result = PyObject_CallFunction(${capture}, "${in_format}", ${in_params})))
        return 2;
    if (!PyArg_ParseTuple(result, "${out_format}", ${out_params}))
        return 3;
    return 0;
}
"""
)

SHARE_NO_ARGS = template(
    """
int
${name}(${out_decl}) {
    if (!${capture})
        return 1;
    PyObject *result = NULL;
    if (!(result = PyObject_CallFunction(${capture}, NULL)))
        return 2;
    if (!PyArg_ParseTuple(result, "${out_format}", ${out_params}))
        return 3;
    return 0;
}
"""
)

MODULE_CODE = template(
    """
$header

$error

$code


$method_table

$module_definition

$module_init
"""
)

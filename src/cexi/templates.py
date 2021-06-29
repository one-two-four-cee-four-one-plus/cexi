from string import Template

MANDATORY_HEADER =\
'''
#define PY_SSIZE_T_CLEAN
#include <Python.h>
'''.strip()

METHOD_TABLE =\
Template('''
static PyMethodDef $name[] = {
    $methods,
    {NULL, NULL, 0, NULL}
};
'''.strip())

FUNCTION =\
Template('''
$prefix $return_type $name($parameters)
{
    $body
}
'''.strip())

MODULE_DEFINITION =\
Template('''
static struct PyModuleDef $module = {
    PyModuleDef_HEAD_INIT,
    "$name",
    NULL,
    -1,
    $method_table
};
'''.strip())

MODULE_INIT =\
Template('''
PyMODINIT_FUNC
PyInit_$name(void)
{
    PyObject *m;
    m = PyModule_Create(&$module);
    return m;
};
'''.strip())


MODULE_CODE =\
Template('''
$header


$code


$method_table

$module_definition

$module_init
'''.strip())

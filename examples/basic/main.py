from cexi import Ext, t, P2C


spam = Ext('spam')
spam('#include "stdio.h"')


@spam.cee
def regular_func(command: P2C[t.char]):
    '''
    printf("calling \\"%s\\" command from Cee\\n", command);
    '''

@spam.py
def ok(module: t.py, args: t.py) -> t.py:
    '''
    printf("command returned success\\n");
    return PyLong_FromLong(0);
    '''

@spam.py
def fail(module: t.py, args: t.py) -> t.py:
    '''
    printf("command returned error\\n");
    return PyLong_FromLong(1);
    '''

@spam.py
def spam_system(module: t.py, args: t.py) -> t.py:
    '''
    const char *command;

    if (!PyArg_ParseTuple(args, "s", &command))
        return NULL;

    regular_func(command);

    if (!system(command))
        return ok(module, args);
    return fail(module, args);
    '''


system = spam_system

if __name__ == '__main__':
    assert system('true') == 0
    assert system('false') != 0

from cexi import Extension, to


def test_spam():
    spam = Extension('spam')

    @spam.py
    def spam_system(self, args: to(command=str)):
        """
        int sts = system(command);
        return PyLong_FromLong(sts);
        """

    @spam.make
    def check_python_lib(cc, extra_preargs, extra_postargs):
        assert '-fPIC' in extra_preargs
        assert extra_postargs == []

    system = spam_system
    spam.ensure()

    assert system('true') == 0
    assert system('false') != 1

    assert hasattr(spam, 'exception')
    assert issubclass(spam.exception, Exception)

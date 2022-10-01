from cexi import Extension, to


def test_spam():
    spam = Extension('spam')

    @spam.py
    def spam_system(self, args: to(command=str)):
        """
        int sts = system(command);
        return PyLong_FromLong(sts);
        """

    system = spam_system
    spam.ensure()

    assert system('true') == 0
    assert system('false') != 1

    assert hasattr(spam, 'exception')
    assert issubclass(spam.exception, Exception)


def test_block():
    ext = Extension()

    ext.block(
        '#define A 42'
    )

    @ext.py
    def a(self, args):
        "return PyLong_FromLong(A);"

    with ext.ensured:
        assert a() == 42

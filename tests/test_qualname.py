"""
Tests for the qualname module.
"""
import functools
import inspect

from qualname import qualname


# These examples are based on the examples from
# https://www.python.org/dev/peps/pep-3155/

class C(object):
    @staticmethod
    def f():
        pass

    class D(object):
        @staticmethod
        def g():
            pass

        @staticmethod
        def h():
            def i():
                def j():
                    pass

                return j

            return i()


def f():
    def g():
        pass

    return g


class ClassWithProblematicDocstring:
    """
    This is an example of how inspect.getsourcelines, which uses a naive
    regex approach, can go very wrong. If you use it on the inner
    class InnerClass, you'll get an error, because the regex finds the
    string 'class InnerClass' in the line above before the class definition.
    Hence the library was updated to make test_problematic_docstring pass.
    """

    class InnerClass:
        pass


class D:
    """
    This class has the same unqualified name as C.D, making it harder to
    distinguish between them (inspect.getsourcelines returns the same result
    for both classes).
    """
    pass


def class_maker1():
    """
    Because C is defined inside a function, _assign_qualnames cannot reach it
    and so another approach is needed.
    """

    class C:
        def f(self):
            pass

    return C


def _test_cache(test_func):
    """
    This ensures that the cache works by running the test twice, where the second
    run should raise an error if qualname tries to use inspect.getsourcefile
    which comes after the cache checks.
    """

    def error():
        raise Exception()

    @functools.wraps(test_func)
    def wrapper():
        test_func()
        original = inspect.getsourcefile
        inspect.getsourcefile = error
        try:
            test_func()
        finally:
            inspect.getsourcefile = original

    return wrapper


@_test_cache
def test_nested_classes():
    assert qualname(C) == 'C'
    assert qualname(C.D) == 'C.D'


@_test_cache
def test_methods_in_nested_classes():
    assert qualname(C.f) == 'C.f'
    assert qualname(C.D.g) == 'C.D.g'


@_test_cache
def test_nested_functions():
    assert qualname(f) == 'f'
    assert qualname(f()) == 'f.<locals>.g'
    assert qualname(C.D.h()) == 'C.D.h.<locals>.i.<locals>.j'


@_test_cache
def test_directly_constructed_type():
    new_type = type('NewCls', (object,), {})
    assert qualname(new_type) == 'NewCls'


@_test_cache
def test_builtins():
    assert qualname(int) == 'int'
    assert qualname(len) == 'len'


@_test_cache
def test_problematic_docstring():
    assert qualname(ClassWithProblematicDocstring.InnerClass) == 'ClassWithProblematicDocstring.InnerClass'


@_test_cache
def test_classes_with_same_name():
    assert qualname(C.D) == 'C.D'
    assert qualname(D) == 'D'


def test_local_classes_with_same_name():
    assert qualname(class_maker1()) == 'class_maker1.<locals>.C'

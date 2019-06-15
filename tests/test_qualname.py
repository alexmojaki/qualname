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
    Because the class C below is defined inside a function, it cannot be reached from
    the top level and so another approach is needed to distinguish it from
    the C at the top of the file. However, since it is the *only* C not reachable
    from the top level, the qualname can still be determined unambiguously,
    even without any methods.
    """

    class C:
        pass

    return C


def class_maker2():
    """
    For the nested classes D here, the library can't guarantee the qualnames.
    But it can guess based on the methods of the classes, whose qualnames are known.
    """

    class X:
        class D:
            """
            This class has the most methods and is the base class of the others.
            This is to ensure that inherited methods do not interfere in the
            computation.
            """

            def f1(self):
                pass

            def f2(self):
                pass

            def f3(self):
                pass

    class Y:
        class D(X.D):
            def g(self):
                pass

    class Z:
        class D(X.D):
            def h(self):
                pass

            def i(self):
                pass

    # If you did this kind of method assignment enough times the library would
    # make the wrong guess, but since most of the methods on Z.D are originally
    # defined on it, it gets the qualname of the class right.
    Z.D.g = Y.D.g

    return X, Y, Z


def class_maker3():
    """
    These classes have no methods and so the library has no way of reliably
    guessing the qualname. However it must still make some guess rather than
    an error.
    """

    class A1:
        class B:
            pass

    class A2:
        class B:
            pass

    return A1, A2


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


# The cache doesn't work for local classes
def test_local_classes_with_same_name():
    assert qualname(class_maker1()) == 'class_maker1.<locals>.C'
    X, Y, Z = class_maker2()
    assert qualname(X) == 'class_maker2.<locals>.X'
    assert qualname(Y) == 'class_maker2.<locals>.Y'
    assert qualname(Z) == 'class_maker2.<locals>.Z'
    assert qualname(X.D) == 'class_maker2.<locals>.X.D'
    assert qualname(Y.D) == 'class_maker2.<locals>.Y.D'
    assert qualname(Z.D) == 'class_maker2.<locals>.Z.D'
    assert qualname(X.D.f1) == 'class_maker2.<locals>.X.D.f1'
    assert qualname(X.D.f2) == 'class_maker2.<locals>.X.D.f2'
    assert qualname(Y.D.g) == 'class_maker2.<locals>.Y.D.g'
    assert qualname(Z.D.h) == 'class_maker2.<locals>.Z.D.h'
    assert qualname(Z.D.i) == 'class_maker2.<locals>.Z.D.i'
    A1, A2 = class_maker3()
    options = ['class_maker3.<locals>.A1.B',
               'class_maker3.<locals>.A2.B']
    assert qualname(A1.B) in options
    assert qualname(A2.B) in options

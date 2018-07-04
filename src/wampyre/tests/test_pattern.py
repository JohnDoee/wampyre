import pytest

from ..opcodes import OP
from ..pattern import Pattern, UnknownPatternException


def test_lengths():
    p = Pattern('uri')
    assert p() == False
    assert p('a', 'b') == False


def test_uri():
    p = Pattern('uri')
    assert p('com.myapp.myprocedure1') == True
    assert p('.myapp.myprocedure1') == False
    assert p('com.myapp.myproced ure1') == False
    assert p('wamp.myapp.myprocedure1') == False

    p = Pattern('uri!')
    assert p('wamp.myapp.myprocedure1') == True


def test_id():
    p = Pattern('id')
    assert p(0) == False
    assert p(500) == True
    assert p('no') == False


def test_opcode():
    p = Pattern('opcode')
    assert p(OP.ERROR) == True
    assert p(2 ** 53) == False
    assert p('no') == False


def test_dict():
    p = Pattern('dict')
    assert p({}) == True
    assert p({'a': 'dict'}) == True
    assert p(['a']) == False
    assert p('no') == False


def test_list():
    p = Pattern('list')
    assert p([]) == True
    assert p(['a', 'b']) == True
    assert p({}) == False
    assert p('no') == False


def test_optional():
    p = Pattern('id?')
    assert p(0) == False
    assert p(500) == True
    assert p('no') == False
    assert p() == True


def test_multiple():
    p = Pattern('uri', 'id', 'uri?', 'id?')
    assert p('a.b.c', 10) == True
    assert p('a.b.c', 10, 20) == False
    assert p('a.b.c', 10, 'c.d') == True
    assert p('a.b.c', 10, 'c.d', 10) == True


def test_unknown_matcher():
    p = Pattern('fake_pattern')
    with pytest.raises(UnknownPatternException):
        p('test')

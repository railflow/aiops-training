import pytest

from greeter import make_greeting


def test_named():
    assert make_greeting("Ada") == "Hello, Ada!"


def test_strips_whitespace():
    assert make_greeting("  Ada ") == "Hello, Ada!"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_blank_becomes_world(value):
    assert make_greeting(value) == "Hello, world!"

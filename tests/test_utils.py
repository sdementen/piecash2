import pytest


def test_camelize():
    from piecash2.utils import camelize

    assert camelize("hello_world") == "HelloWorld"
    assert camelize("hello_world", uppercase_first_letter=False) == "helloWorld"
    assert camelize("hello-world") == "HelloWorld"
    assert camelize("hello-world", uppercase_first_letter=False) == "helloWorld"


def test_underscore():
    from piecash2.utils import underscore

    assert underscore("HelloWorld") == "hello_world"
    assert underscore("helloWorld") == "hello_world"
    assert underscore("hello-world") == "hello_world"
    assert underscore("helloWorld") == "hello_world"


def test_pluralize():
    from piecash2.utils import pluralize

    assert pluralize("word") == "words"
    assert pluralize("commodity") == "commodities"
    assert pluralize("Commodity") == "Commodities"

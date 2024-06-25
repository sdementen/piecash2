import sys
from pathlib import Path

import pytest

from piecash2 import open_book
from piecash2.schema.schema_generation import add_book_module_in_path, get_schema_name, path_schemas, remove_book_module_in_path

path_data = Path(__file__).parent.parent / "data"


def test_get_schema_name():
    book = path_data / "test book.gnucash"
    assert get_schema_name(book).is_relative_to(path_schemas)
    assert get_schema_name(book).stem == "book_schema_sqlite_2060400"


def test_direct_import():
    book = path_data / "test book.gnucash"
    assert get_schema_name(book).stem == "book_schema_sqlite_2060400"

    with pytest.raises(ImportError):
        import book_schema_sqlite_2060400

    add_book_module_in_path(book)

    # import the module
    import book_schema_sqlite_2060400

    remove_book_module_in_path(book)

    with pytest.raises(ImportError):
        import book_schema_sqlite_2060400


def test_open_book():
    book = path_data / "test book.gnucash"

    Session = open_book(book)
    piecash = Session.module
    assert piecash.__name__ == get_schema_name(book).stem


def test_simple_query():
    book = path_data / "test book.gnucash"

    Session = open_book(book)
    piecash = Session.module

    with Session() as s:
        assert len(s.query(piecash.Slot).all()) == 20

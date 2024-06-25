import os
import sys
from pathlib import Path

import pytest

from piecash2 import open_book
from piecash2.schema import schema_generation

path_data = Path(__file__).parent.parent / "data"


def test_get_schema_name():
    book = path_data / "test book.gnucash"
    assert schema_generation.get_schema_name(book).is_relative_to(schema_generation.path_schemas)
    assert schema_generation.get_schema_name(book).stem == "book_schema_sqlite_2060400"


def test_direct_import():
    book = path_data / "test book.gnucash"
    assert schema_generation.get_schema_name(book).stem == "book_schema_sqlite_2060400"
    path_module = schema_generation.get_schema_name(book)
    schema_generation.generate_schema(book, schema_file=path_module)

    with pytest.raises(ImportError):
        import book_schema_sqlite_2060400

    schema_generation.add_book_module_in_path(book)

    # import the module
    import book_schema_sqlite_2060400

    schema_generation.remove_book_module_in_path(book)

    with pytest.raises(ImportError):
        import book_schema_sqlite_2060400

    # remove module
    path_module.unlink()


def test_open_book():
    book = path_data / "test book.gnucash"

    Session = open_book(book)
    piecash = Session.module
    assert piecash.__name__ == schema_generation.get_schema_name(book).stem


def test_simple_query():
    book = path_data / "test book.gnucash"

    Session = open_book(book)
    piecash = Session.module

    with Session() as s:
        assert len(s.query(piecash.Slot).all()) == 20

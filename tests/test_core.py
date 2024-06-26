import pytest

from piecash2 import open_book
from piecash2.schema.generation import schema_generation
from tests.test_schemas import path_data


def test_simple_query():
    book = path_data / "test book.gnucash"

    Session = open_book(book)
    piecash = Session.module
    print(piecash.__file__)

    with Session() as s:
        for name, attr in piecash.__dict__.items():
            # print(name, type(attr))
            if isinstance(attr, type) and issubclass(attr, piecash.Base) and attr is not piecash.Base:
                for obj in s.query(attr).all():
                    print(obj)
                assert len(list(s.query(attr).all())) >= 0


@pytest.mark.parametrize(
    "book",
    [
        path_data / "test book.gnucash",
        str(path_data / "test book.gnucash"),
    ],
)
def test_open_book(book):
    Session = open_book(book)
    piecash = Session.module
    assert piecash.__name__ == schema_generation.get_schema_name(book).stem

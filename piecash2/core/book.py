import sqlite3
from pathlib import Path

import sqlalchemy
import sqlalchemy.orm

from piecash2.schema.generation.schema_generation import import_gnucash


def open_book(book, regenerate_schema=False):
    if isinstance(book, str):
        book = Path(book)

    book_posix = book.as_posix()

    # make a backup of the DB in memory
    db_memory_name = f":memgeco_{abs(hash(book_posix))}:"
    with sqlite3.connect(book_posix) as source:
        sqliteconn = f"file:{db_memory_name}?mode=memory&cache=shared"
        dest = sqlite3.connect(sqliteconn, uri=True)
        source.backup(dest)

    engine = sqlalchemy.create_engine(f"sqlite:///{db_memory_name}", echo=False, creator=lambda: sqlite3.connect(sqliteconn, uri=True))

    Session = sqlalchemy.orm.sessionmaker(bind=engine, autoflush=True, autocommit=False)

    # must execute some query otherwise future call to the Session raise error
    with Session() as s:
        s.execute(sqlalchemy.text(""))

    Session.module = import_gnucash(book, regenerate_schema=regenerate_schema)

    return Session

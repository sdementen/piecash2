"""Generate and import the SA schema from a gnucash sqlite file."""
import importlib.util
import sqlite3
import sys
from pathlib import Path

import sqlalchemy
import sqlalchemy.orm

# folder with code to insert into the schema generated by sqlacodegen
code_templates = Path(__file__).parent

# folder in HOME to store the generated schemas
path_schemas = Path.home() / ".piecash2" / "schemas"
path_schemas.mkdir(exist_ok=True, parents=True)


def import_module_from_path(path: Path):
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def import_gnucash(book, regenerate_schema=False):
    modulename = get_schema_name(book)

    if not modulename.exists() or regenerate_schema:
        generate_schema(book, schema_file=modulename)

    return import_module_from_path(modulename)


def generate_schema(db, schema_file: Path):
    """Generate the schema from the sqlite database using sqlacodegen and copy the common files to the db folder."""

    sys.argv = [
        "sqlacodegen_v2",
        "--outfile",
        str(schema_file),
        f"sqlite:///{db.as_posix()}",
        "--option",
        "use_inflect",
    ]
    import sqlacodegen_v2.cli

    sqlacodegen_v2.cli.main()

    # insert before/after the generated schema the common schema
    schema_file_text = (
        (code_templates / "sa_schema_pre.py").read_text() + schema_file.read_text() + (code_templates / "sa_schema_post.py").read_text()
    )

    schema_file.write_text(schema_file_text)
    return schema_file_text


def get_version(db: Path):
    """Return the table version of a given book file."""
    with sqlite3.connect(db) as conn:
        c = conn.cursor()
        c.execute("SELECT table_version FROM versions WHERE table_name=='Gnucash'")
        (gnucash_version,) = c.fetchone()
    return gnucash_version


def get_schema_name(book: Path):
    """Return the schema file name for a given book file."""
    v = get_version(book)
    return path_schemas / f"book_schema_sqlite_{v}.py"


def open_book(book, regenerate_schema=False):
    if isinstance(book, str):
        book = Path(book)

    book_posix = book.as_posix()

    # connect to the local sqlite extract of GECO
    sqlite_connection_string = f"sqlite:///{book_posix}"

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


def add_book_module_in_path(book):
    module_folder = str(get_schema_name(book).parent)
    if module_folder not in sys.path:
        sys.path.append(module_folder)


def remove_book_module_in_path(book):
    module_path = get_schema_name(book)
    module_folder = str(module_path.parent)
    module_name = module_path.stem

    sys.modules.pop(module_name)

    if module_folder in sys.path:
        sys.path.remove(module_folder)

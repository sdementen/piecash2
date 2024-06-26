import importlib
from pathlib import Path

import pytest

from piecash2.schema.generation import schema_generation

path_data = Path(__file__).parent.parent / "data"


def test_get_schema_name():
    book = path_data / "test book.gnucash"
    assert schema_generation.get_schema_name(book).is_relative_to(schema_generation.path_schemas)
    assert schema_generation.get_schema_name(book).stem == "book_schema_sqlite_2060400"


@pytest.fixture
def change_schema_path(request):
    import piecash2.schema.generation.schema_generation as schema_generation

    ops = schema_generation.path_schemas

    tmp_path = Path(request.getfixturevalue("tmpdir")) / "schemas"
    tmp_path.mkdir(exist_ok=True, parents=True)
    schema_generation.path_schemas = tmp_path

    yield

    schema_generation.path_schemas = ops


@pytest.mark.parametrize("book", list(path_data.glob("*.gnucash")))
def test_import_dynamic(book):
    schema_generation.import_gnucash(book)


@pytest.mark.parametrize("book", list(path_data.glob("*.gnucash")))
def test_import_explicit(book):
    module_name = schema_generation.get_schema_name(book).stem
    importlib.import_module(f"piecash2.schema.generated.{module_name}")


@pytest.mark.parametrize("book", [path_data / "test book.gnucash"])
def test_import_regenerate(book):
    schema_generation.import_gnucash(book, regenerate_schema=True)


@pytest.mark.parametrize("book", [path_data / "test book.gnucash"])
def test_add_book_module_in_path(book, change_schema_path):
    importlib.invalidate_caches()

    if True:
        path_module = schema_generation.get_schema_name(book)
        module_name = path_module.stem
        assert module_name.startswith("book_schema_sqlite_")

        # clean up existing file and unload module
        if path_module.exists():
            path_module.unlink()
        schema_generation.unload_module(module_name)

        # generate the schema
        schema_generation.generate_schema(book, schema_file=path_module)

        # if True:
        with pytest.raises(ImportError):
            importlib.import_module(module_name)

        schema_generation.add_book_module_in_path(book)

        # import the module
        importlib.import_module(module_name)
        schema_generation.unload_module(module_name)

        schema_generation.remove_book_module_in_path(book)

        with pytest.raises(ImportError):
            importlib.import_module(module_name)

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent


# each test runs on cwd to its temp dir
@pytest.fixture(autouse=True)
def go_to_tmpdir(request):
    # Get the fixture dynamically by its name.
    tmpdir = request.getfixturevalue("tmpdir")
    # ensure local test created packages can be imported
    sys.path.insert(0, str(tmpdir))
    # Chdir only for the duration of the test.
    with tmpdir.as_cwd():
        yield


@pytest.fixture(autouse=True)
def change_schema_path(request):
    import piecash2.schema.generation.schema_generation as schema_generation

    # schema_generation.path_schemas = Path(request.getfixturevalue("tmpdir")) / "schemas"
    # schema_generation.path_schemas.mkdir(exist_ok=True, parents=True)

    import piecash2.schema.generated as generated

    schema_generation.path_schemas = Path(generated.__file__).parent

    for book in (HERE.parent / "data").glob("*.gnucash"):
        schema_generation.generate_schema(book, schema_generation.get_schema_name(book))

    yield
